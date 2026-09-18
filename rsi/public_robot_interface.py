"""Read-only candidate. Host supplies latest_path; actor supplies matching identity.

Only reads the issued observation and its SHA-bound public robot-hand geometry.
No backend, action dispatch, model, network, object/contact state or extra files.
Stdlib only apart from the existing public_hand_geometry reader.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from rsi.public_hand_geometry import read_hand_geometry

SIDES = ("left", "right")
WRISTS = tuple(f"{side}_wrist_yaw_link" for side in SIDES)
FOUR = WRISTS + tuple(f"{side}_ankle_roll_link" for side in SIDES)
IDENTITY = {"observation_path", "reset_id", "observation_id"}


def encode(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def vector(value, size):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"Expected {size} finite numbers")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError("Non-finite/non-numeric vector")
    return list(value)


def quaternion(value):
    q = vector(value, 4)
    norm = math.sqrt(sum(x*x for x in q))
    if abs(norm - 1.0) > 1e-4:
        raise ValueError("Quaternion must be unit wxyz")
    return [x/norm for x in q]


def qmul(a, b):
    w, x, y, z = a
    v, i, j, k = b
    return [w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j,
            w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v]


def inverse(q):
    return [q[0], -q[1], -q[2], -q[3]]


def rotate(q, p):
    return qmul(qmul(q, [0, *p]), inverse(q))[1:]


def add(a, b):
    return [x+y for x, y in zip(a, b)]


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def pose(value):
    return {"position_world_m": vector(value["position_world_m"], 3),
            "quaternion_wxyz": quaternion(value["quaternion_wxyz"])}


def _load(latest_path, arguments, extra=()):
    if not isinstance(arguments, dict) or set(arguments) != IDENTITY | set(extra):
        raise ValueError("Arguments must contain exact identity and tool fields")
    path = Path(latest_path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Latest public observation must be an absolute non-symlink path")
    if arguments["observation_path"] != str(path):
        raise ValueError("Stale observation path; host latest_path is authoritative")
    if path.name != "observation.json" or path.parent.parent.name != "observations":
        raise ValueError("Unexpected public observation layout")
    if path.stat().st_size > 2_000_000:
        raise ValueError("Public observation exceeds size bound")
    raw = path.read_bytes()
    observation = json.loads(raw)
    if observation.get("episode_id") != str(path.parents[2]):
        raise ValueError("Observation episode binding mismatch")
    for key in ("reset_id", "observation_id"):
        if not isinstance(arguments[key], str) or not arguments[key]:
            raise ValueError(f"Nonempty {key} required")
        if observation.get(key) != arguments[key]:
            raise ValueError(f"Stale {key}; no cross-reset reuse")
    source = {"observation_path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
              "reset_id": observation["reset_id"], "observation_id": observation["observation_id"],
              "sim_s": observation.get("sim_s")}
    return observation, source


def _frame(observation, name):
    if name == "world":
        return {"position_world_m": [0., 0., 0.], "quaternion_wxyz": [1., 0., 0., 0.]}
    if name in FOUR:
        return pose(observation["four_point_world"][name])
    # No caller-selected frame or object name is looked up outside this allowlist.
    names = {f"{s}_hand_{f}_{n}_link" for s in SIDES for f, ns in
             (("thumb", (0, 1, 2)), ("index", (0, 1)), ("middle", (0, 1))) for n in ns}
    if name not in names:
        raise ValueError("Frame must be world or an issued named robot hand/ankle link")
    return pose(observation["finger_geometry"]["hand_collision_model"]["body_poses_world"][name])


def transform_pose(latest_path, arguments):
    """Express a caller-declared pose in another achieved public robot frame.

    source_frame/destination_frame are frame names; position_m and quaternion_wxyz
    describe the input pose in source_frame. Returns a pose, never an action target.
    """
    observation, source = _load(latest_path, arguments,
        ("source_frame", "destination_frame", "position_m", "quaternion_wxyz"))
    origin = _frame(observation, arguments["source_frame"])
    destination = _frame(observation, arguments["destination_frame"])
    q = quaternion(arguments["quaternion_wxyz"])
    p = vector(arguments["position_m"], 3)
    world_p = add(origin["position_world_m"], rotate(origin["quaternion_wxyz"], p))
    world_q = qmul(origin["quaternion_wxyz"], q)
    dest_inverse = inverse(destination["quaternion_wxyz"])
    return {"schema": "public-transform-pose-v1", "no_physical_action": True,
            "source": source, "frame": arguments["destination_frame"],
            "position_m": rotate(dest_inverse, sub(world_p, destination["position_world_m"])),
            "quaternion_wxyz": quaternion(qmul(dest_inverse, world_q))}


def _box_in_frame(low, high, body_pose, frame_pose):
    """Conservative AABB of a body-local box in an achieved destination frame."""
    center = [(a+b)/2 for a, b in zip(low, high)]
    extent = [(b-a)/2 for a, b in zip(low, high)]
    if any(e < 0 for e in extent):
        raise ValueError("Invalid body-local bounds")
    frame_inverse = inverse(frame_pose["quaternion_wxyz"])
    relative_q = qmul(frame_inverse, body_pose["quaternion_wxyz"])
    center = rotate(frame_inverse, sub(add(body_pose["position_world_m"],
        rotate(body_pose["quaternion_wxyz"], center)), frame_pose["position_world_m"]))
    columns = [rotate(relative_q, [float(i == j) for i in range(3)]) for j in range(3)]
    projected = [sum(abs(columns[j][i])*extent[j] for j in range(3)) for i in range(3)]
    return [sub(center, projected), add(center, projected)]


def _merge(boxes):
    if not boxes:
        raise ValueError("Empty geometry group")
    return [[min(b[0][i] for b in boxes) for i in range(3)],
            [max(b[1][i] for b in boxes) for i in range(3)]]


def _outward(box):
    # Round away from surfaces: this display rounding must never shrink a bound.
    return [[math.floor(x*1e5)/1e5 for x in box[0]],
            [math.ceil(x*1e5)/1e5 for x in box[1]]]


def _geometry(latest_path, observation):
    reference = observation.get("finger_geometry", {}).get("hand_collision_model", {})
    if not reference.get("path"):
        return {"status": "not_provided"}
    index = read_hand_geometry(latest_path, {"path": reference["path"]})
    if not index or "read_rejected" in index:
        raise ValueError("Issued hand geometry rejected: " + str((index or {}).get("read_rejected")))
    # Only the existing robot-only, hash-checked bounds index is consumed here.
    poses = reference["body_poses_world"]
    hands = {}
    for side, wrist in zip(SIDES, WRISTS):
        selected = [name for name in index["bodies"] if name.startswith(side + "_")]
        expected = {wrist} | {f"{side}_hand_{f}_{n}_link" for f, ns in
            (("thumb", (0, 1, 2)), ("index", (0, 1)), ("middle", (0, 1))) for n in ns}
        if set(selected) != expected or not expected <= set(poses):
            raise ValueError("Full-hand coverage unavailable; do not label partial bounds whole-hand")
        wrist_frame = _frame(observation, wrist)
        if max(abs(x-y) for x, y in zip(pose(poses[wrist])["position_world_m"],
                wrist_frame["position_world_m"])) > 1e-6:
            raise ValueError("Inconsistent public wrist position sources")
        if abs(abs(sum(x*y for x, y in zip(pose(poses[wrist])["quaternion_wxyz"],
                wrist_frame["quaternion_wxyz"]))) - 1.) > 1e-6:
            raise ValueError("Inconsistent public wrist orientation sources")
        by_frame = {}
        for frame_name, frame_pose in (("world", _frame(observation, "world")), ("wrist", wrist_frame)):
            boxes = {name: [_box_in_frame(vector(part["bounds_min_body_m"], 3),
                         vector(part["bounds_max_body_m"], 3), pose(poses[name]), frame_pose)
                         for part in index["bodies"][name]] for name in selected}
            groups = {"whole_hand": selected, "palm": [wrist],
                      "proximal": [n for n in selected if n != wrist and not
                          any(n.endswith(s) for s in ("thumb_2_link", "index_1_link", "middle_1_link"))],
                      "distal": [n for n in selected if
                          any(n.endswith(s) for s in ("thumb_2_link", "index_1_link", "middle_1_link"))]}
            by_frame[f"bounds_{frame_name}_m"] = {group: _outward(_merge(
                [box for name in names for box in boxes[name]])) for group, names in groups.items()}
        # Already-issued distal bounds are tighter in wrist frame; do not replace
        # them with transformed local boxes or invent a contact/TCP interpretation.
        by_frame["distal_native_bounds_wrist_m"] = {finger: _outward([
            vector(observation["finger_geometry"][side][finger]["bounds_min_wrist_m"], 3),
            vector(observation["finger_geometry"][side][finger]["bounds_max_wrist_m"], 3)])
            for finger in ("thumb", "index", "middle")}
        hands[side] = by_frame
    return {"status": "ok", "path": index["path"], "sha256": index["source_sha256"],
            "bounds_format": "[min_xyz,max_xyz]; m; outward-rounded 0.00001m",
            "method": "conservative AABB union of transformed body-local collision bounds; 8 bodies/hand",
            "hands": hands,
            "limits": "Bounds enclose collision geometry, not tight contact surfaces, aperture, force, TCP or retention. Read raw geometry/RGB when needed."}


def _round(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite public scalar")
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round(v) for v in value]
    return value


def robot_brief(latest_path, arguments):
    """Small robot-only derived receipt. Raw observation/images remain unchanged."""
    observation, source = _load(latest_path, arguments)
    command = observation.get("command_status") or {}
    anchor = command.get("observation_anchor", {})
    approved = command.get("approved_target", {})
    requested = command.get("requested_target", {})
    wrists = {}
    for side, name in zip(SIDES, WRISTS):
        measured = _frame(observation, name)
        row = {"measured_pose_world": measured,
               "active_position": name in command.get("active_position_links", []),
               "active_orientation": name in command.get("active_orientation_links", [])}
        if name in observation.get("four_point_reference_world", {}):
            row["current_reference_pose_world"] = pose(observation["four_point_reference_world"][name])
        if name in anchor:
            base = pose(anchor[name])["position_world_m"]
            row["measured_delta_from_command_anchor_world_m"] = sub(measured["position_world_m"], base)
            for label, mapping in (("approved", approved), ("requested", requested)):
                if name in mapping:
                    row[f"{label}_delta_from_command_anchor_world_m"] = sub(pose(mapping[name])["position_world_m"], base)
        row["tracking_error"] = {
            "position_m": command.get("actual_position_error_m_by_link", {}).get(name),
            "rotation_rad": command.get("actual_rotation_error_rad_by_link", {}).get(name)}
        row["gripper"] = {"commanded_closure": observation.get("gripper_commanded_closure", {}).get(side),
                          "goal_closure": observation.get("gripper_goal_closure", {}).get(side)}
        names, actual, target = (observation.get(k, []) for k in
            ("joint_names", "joint_position_rad", "commanded_joint_target_rad"))
        if len(names) != len(set(names)):
            raise ValueError("Duplicate public joint names")
        if names and len(names) == len(actual) == len(target):
            named = {n: t-a for n, a, t in zip(names, vector(actual, len(names)), vector(target, len(names)))
                     if n.startswith(side + "_") and any(s in n for s in ("shoulder", "elbow", "wrist"))}
            if named:
                largest = max(named, key=lambda n: abs(named[n]))
                row["arm_command_minus_measured_max"] = {"joint_name": largest,
                    "signed_rad": named[largest], "not_displacement_or_ik_residual": True}
        wrists[side] = row
    ik = command.get("ik_feedback", {})
    ik_rows = {side: {key: row[key] for key in ("converged", "position_error_m", "rotation_error_rad") if key in row}
               for side, row in ik.items() if side in SIDES and isinstance(row, dict)}
    root = observation.get("robot_root", {})
    result = {"schema": "public-robot-brief-v1", "no_physical_action": True, "source": source,
        "command": {key: command[key] for key in
            ("command_id", "command_kind", "status", "reference_finished", "start_sim_s", "duration_s") if key in command},
        "wrists": wrists, "ik": {"status": "provided" if ik_rows else "not_provided", "by_side": ik_rows},
        "robot_root": {key: root[key] for key in ("height_world_m", "tilt_deg") if key in root},
        "hand_geometry": _geometry(latest_path, observation),
        "limits": "Derived robot summary only. Command/reference, measured motion, IK solver residual and tracking error are distinct. No grasp/contact/success inference. Raw observation, selected experience and required RGB remain available unchanged."}
    return _round(result)


def dispatch(name, latest_path, arguments):
    """One read-only host entry. Repeated identity yields identical output, no ACKs.

    latest_path MUST come from harness.latest_path, never a caller-selected tool
    argument. Revalidate each call; no memoized observation across reset or ACK.
    """
    try:
        if name not in ("robot_brief", "transform_pose"):
            raise ValueError("Unknown public robot tool")
        return {"robot_brief": robot_brief, "transform_pose": transform_pose}[name](latest_path, arguments)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        return {"status": "rejected", "error": str(error), "no_physical_action": True}


def tool_specs():
    """Optional dynamic read tools; no output directory or execution permission."""
    string = {"type": "string"}
    identity = {key: string for key in sorted(IDENTITY)}
    vector3 = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}
    vector4 = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}
    transforms = {**identity, "source_frame": string, "destination_frame": string,
                  "position_m": vector3, "quaternion_wxyz": vector4}
    descriptions = {
        "robot_brief": "Read latest achieved wrists, command-vs-measured movement, IK and conservative whole-hand bounds. No physical action. Raw sources and RGB remain authoritative.",
        "transform_pose": "Express a declared pose between world and achieved public robot link frames. Quaternion wxyz, metres. No target detection, action or grasp inference."}
    return [{"type": "function", "name": name, "description": descriptions[name],
             "inputSchema": {"type": "object", "additionalProperties": False,
                             "properties": fields, "required": list(fields)}}
            for name, fields in (("robot_brief", identity), ("transform_pose", transforms))]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Offline public-observation demo; not actor path authorization")
    parser.add_argument("tool", choices=("robot_brief", "transform_pose"))
    parser.add_argument("--latest", required=True, help="Trusted host-owned latest observation path")
    parser.add_argument("--arguments", required=True, help="JSON tool arguments, including exact identity")
    args = parser.parse_args()
    print(encode(dispatch(args.tool, args.latest, json.loads(args.arguments))))
