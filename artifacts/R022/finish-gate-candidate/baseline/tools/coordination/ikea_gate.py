#!/usr/bin/env python3
"""Offline, fail-closed IKEA eligibility check. Never starts a model or simulator.

Trust boundary: the existing supervisor supplies host provenance receipts, after
checking the actual launch/reset. Actor claims and discovered filenames are NOT
an enrollment source. We independently re-audit the bound recording thereafter.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/R020"
CAMPAIGN = ROOT / "artifacts/R019/door-campaign"
THREAD = "01a0a867-d7aa-71f2-8547-e264d6d09ede"
CONTRACT = "simple-asset003-push-open-contact30deg-dwell1s-standing-v1"
VARIANT = "SIMPLE asset 003 push-open; original task is close-door"
REQUIRED = ("result.json", "video/robot_trace.jsonl", "video/episode.mp4",
            "video/render_manifest.json", "video/scene_setup.json", "SKILL.md")


class Rejected(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Rejected(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


@contextmanager
def locked(path):
    with Path(path).open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def inside(root, relative):
    need(isinstance(relative, str), "invalid evidence path")
    p = (root / relative).resolve()
    need(root.resolve() in p.parents and not Path(relative).is_absolute(),
         "evidence path escapes its root")
    return p


def finite(value):
    need(type(value) in (int, float) and math.isfinite(value), "nonfinite/nonnumeric state")
    return float(value)


def audit_trace(path, initial, duration):
    """Stream ONE enrolled recording; no trace dump or model input."""
    start = previous = initial_angle = since = None
    pushed = qualified = False
    n = 0
    command_ids = set()
    with path.open() as f:
        for line in f:
            row = json.loads(line)
            t = finite(row["sim_s"])
            state = row["host_render_state"]
            joints = state["qpos_by_joint"]
            angle = finite(joints["articulate_joint_1"][0])
            root = [finite(v) for v in joints["floating_base_joint"]]
            need(len(root) == 7, "invalid floating base state")
            w, x, y, z = root[3:]
            need(abs(w*w+x*x+y*y+z*z-1) < 1e-4, "invalid base quaternion")
            tilt = math.degrees(math.acos(max(-1, min(1, 1-2*(x*x+y*y)))))
            need(root[2] >= .55 and tilt <= 25, "standing/stability failed")
            if start is None:
                start = t
                initial_angle = angle
                need(joints == initial["qpos_by_joint"], "reset/first frame mismatch")
                need(abs(angle + math.pi/18) < 1e-5, "not the formal closed-door reset")
                need(row["native_outcome"] == "in_progress", "already successful at reset")
            else:
                need(abs(t-previous-.02) < 1e-5, "missing/repeated/nonphysical ticks")
            contact = state["hand_door_contact"]
            need(type(contact) is bool, "missing real host contact audit")
            pushed |= contact
            if pushed and angle-initial_angle >= math.pi/6:
                since = t if since is None else since
                qualified |= t-since >= 1.0-1e-7
            else:
                since = None
            need(row["native_outcome"] in ("in_progress", "success"), "host failure in trace")
            if row["native_outcome"] == "success":
                need(qualified, "success claim precedes physical criteria")
            status = row["status"]
            need(status.get("status") not in ("stopped", "failure"), "recording stopped")
            if status.get("command_id"):
                command_ids.add(status["command_id"])
            previous = t
            n += 1
    need(n > 51 and pushed and qualified, "contact/opening/one-second dwell not proven")
    need(row["native_outcome"] == "success", "recording lacks terminal host success")
    need(abs(previous-start-finite(duration)) < 1e-5, "incomplete physical episode recording")
    need(command_ids, "no recorded action execution")
    return {"ticks": n, "sim_s": previous-start, "commands": len(command_ids),
            "host_contact": pushed, "physical_criteria_passed": qualified}


def video_probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames,duration,r_frame_rate",
                        "-of", "json", str(path)], capture_output=True, text=True,
                       check=True, timeout=30)
    return json.loads(p.stdout)["streams"][0]


def audit_episode(episode, receipt, *, campaign=CAMPAIGN, probe=video_probe):
    episode = Path(episode).resolve()
    need(episode.parent == campaign.resolve() and re.fullmatch(r"episode-\d{4,}", episode.name),
         "not an enrolled formal door campaign episode")
    need(not receipt.get("synthetic_fixture_only") or campaign.resolve() != CAMPAIGN.resolve(),
         "synthetic fixture cannot enter production")
    need(receipt["schema"] == 1 and receipt["data_kind"] == "real_physics",
         "synthetic/replay receipt rejected")
    need(receipt["host_reviewer_thread"] == THREAD, "not the authorized host reviewer")
    need(receipt["contract"] == CONTRACT and receipt["mode"] == "formal_direct_simulation",
         "wrong task, replay, or diagnostic")
    need(receipt["episode"] == str(episode), "receipt belongs to another episode")
    reset = receipt["reset"]
    need(reset["method"] == "fresh_environment_reset" and reset["reset_id"], "missing independent reset")
    need(type(reset["seed"]) is int and reset["seed"] == int(episode.name.split("-")[-1]),
         "reset seed does not match formal runner")
    launch = reset["launch"]
    need(launch["boot_id"] and type(launch["pid"]) is int and launch["pid"] > 0
         and type(launch["start_ticks"]) is int and launch["start_ticks"] > 0,
         "missing host process identity")
    need(receipt["provenance_review"] == {
        "independent_reset": True, "full_episode": True, "no_replay": True,
        "no_diagnostic_initial_state": True, "single_action_writer": True,
        "original_physics": True}, "incomplete host provenance review")
    # Hashes bind host enrollment to exact evidence bytes, not an actor verdict.
    files = receipt["evidence_sha256"]
    result = read(episode / "result.json")
    need(result["success"] is True and result["native_outcome"] == "success",
         "result is not host success")
    need(result["episode_id"] == episode.name and result["error"] is None
         and result["skill_updated"] is True and result["stop_reason"] == "native_success",
         "incomplete/error episode")
    need(result["model"] == "gpt-6-astra" and result["effort"] == "xhigh", "wrong model/effort")
    need(type(result["actions"]) is int and result["actions"] > 0, "no physical actions")
    count = result["codex_turns"]
    need(type(count) is int and 0 < count <= 1000, "invalid completed turn count")
    needed = (*REQUIRED, *(f"turn_{i:03d}.json" for i in range(1, count+1)))
    # Preserve host launch/reset review evidence outside actor-accessible output.
    need(isinstance(receipt["host_evidence"], list) and receipt["host_evidence"],
         "missing launch/reset audit evidence")
    for item in receipt["host_evidence"]:
        p = inside(ROOT, item["path"])
        need((ROOT/"artifacts").resolve() in p.parents, "host evidence must be an artifact, never credentials")
        need(p.is_file() and digest(p) == item["sha256"], "host provenance evidence changed/missing")
    for name in needed:
        p = inside(episode, name)
        need(p.is_file() and p.stat().st_size > 0 and files.get(name) == digest(p),
             "missing/changed evidence: " + name)
    for i in range(1, count+1):
        need(read(episode/f"turn_{i:03d}.json")["status"] == "completed", "reasoning not complete")
    need(result["starting_skill_sha256"] == files["SKILL.md"], "skill version mismatch")
    manifest = read(episode/"video/render_manifest.json")
    need(manifest["actor_access"] is False and manifest["physics"] == "MuJoCo",
         "wrong backend or actor-visible host evidence")
    need(manifest["runtime_source_sha256"] == receipt["runtime_source_sha256"]
         and bool(manifest["runtime_source_sha256"]), "unbound runtime version")
    scene = read(episode/"video/scene_setup.json")
    need(scene["variant"] == VARIANT and scene["pd_profile"] == "checkpoint"
         and scene["actor_access"] is False and finite(scene["opening_dot_after"]) > 0,
         "wrong task setup/controller")
    stats = audit_trace(episode/"video/robot_trace.jsonl", manifest["initial_render_state"], result["sim_s"])
    need(stats["commands"] == result["actions"], "action/recording count mismatch")
    video = probe(episode/"video/episode.mp4")
    expected = (stats["ticks"] + 1)//2
    need(int(video["nb_frames"]) == expected and video["r_frame_rate"] == "25/1"
         and abs(finite(float(video["duration"]))-expected/25) < .041,
         "video does not cover the full recording")
    # Recheck after parsing/probing to reject a concurrent partial rewrite.
    for name in needed:
        need(digest(inside(episode, name)) == files[name], "evidence changed during audit")
    return {"episode": str(episode), "reset_id": reset["reset_id"],
            "launch_id": [launch[k] for k in ("boot_id", "pid", "start_ticks")],
            "trace_sha256": files["video/robot_trace.jsonl"],
            "video_sha256": files["video/episode.mp4"], **stats}


def evaluate(registry, api, *, base=OUT, campaign=CAMPAIGN, probe=video_probe, budget_policy=None):
    need(registry["schema"] == 1 and registry["data_kind"] == "real_physics", "invalid host registry")
    accepted, rejected = [], []
    seen = {k: set() for k in ("episode", "reset_id", "launch_id", "trace_sha256", "video_sha256")}
    for entry in registry["episodes"]:
        try:
            p = inside(base, entry["receipt"])
            need(digest(p) == entry["sha256"], "host receipt hash mismatch")
            receipt = read(p)
            row = audit_episode(receipt["episode"], receipt, campaign=campaign, probe=probe)
            need(digest(p) == entry["sha256"], "receipt changed during audit")
            for key in seen:
                need(json.dumps(row[key]) not in seen[key], "duplicate " + key)
            for key in seen:
                seen[key].add(json.dumps(row[key]))
            accepted.append(row)
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError,
                OverflowError, subprocess.SubprocessError) as exc:
            rejected.append({"entry": entry, "reason": str(exc)})
    # The user has ALREADY authorized the shared budget. Never ask twice or
    # take a per-process cap from api-configuration.json.
    from shared_budget import POLICY, policy_terms, pricing_status
    budget_policy = read(POLICY) if budget_policy is None else budget_policy
    terms = policy_terms(budget_policy)
    configured, pricing_blocker = pricing_status(budget_policy, api)
    gate = len(accepted) >= 3
    return {"schema": 1, "checked_at": utc(), "contract": CONTRACT,
            "audited_independent_successes": len(accepted), "required": 3,
            "physical_gate_passed": gate, "api_metadata_confirmed": configured,
            "budget_authorized": True, "budget_policy": str(POLICY),
            "shared_cap_fen": terms["cap_fen"], "report_interval_fen": terms["report_interval_fen"],
            "api_source_pricing_blocker": pricing_blocker,
            "state": "eligible_registered_only" if gate and configured else
                     "waiting_api_configuration" if gate else "waiting_simple_successes",
            "launch_performed": False, "model_calls": 0,
            "accepted": accepted, "rejected": rejected,
            "blockers": ([] if gate else ["need_three_host_audited_independent_complete_successes"])
                        + ([] if configured else ["api_source_pricing_or_bound_enforcement_unverified"])}


def check():
    with locked(OUT/"gate.lock"):
        try:
            state = evaluate(read(OUT/"host-audits.json"), read(OUT/"api-configuration.json"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
            state = {"schema": 1, "checked_at": utc(), "state": "invalid_configuration",
                     "physical_gate_passed": False, "audited_independent_successes": 0,
                     "required": 3, "launch_performed": False, "model_calls": 0,
                     "blockers": [str(exc)]}
        from shared_budget import BudgetLedger
        try:
            budget_status = BudgetLedger().status()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            budget_status = {"state": "blocked", "reason": str(exc), "runtime_api_validated": False}
        if budget_status.get("state") == "blocked" or budget_status.get("halted"):
            state.setdefault("blockers", []).append("shared_budget_accounting_blocked")
            if state["state"] == "eligible_registered_only":
                state["state"] = "waiting_budget_accounting"
        state["paid_request_dispatched"] = False
        state["api_runtime_validated"] = False
        atomic_json(OUT/"ikea-gate-state.json", state)
        with locked(OUT/"status.lock"):
            path = OUT/"coordination-status.json"
            status = read(path) if path.exists() else {"schema": 1}
            status["ikea_gate"] = state
            status["shared_budget"] = budget_status
            atomic_json(path, status)
        return state


def enroll(relative):
    """Only the trusted supervisor should call this after a real host review."""
    path = inside(OUT, relative)
    need(OUT/"host-receipts" in path.parents, "receipt must be in R020/host-receipts")
    with locked(OUT/"gate.lock"):
        registry = read(OUT/"host-audits.json")
        entry = {"receipt": str(path.relative_to(OUT)), "sha256": digest(path)}
        if entry in registry["episodes"]:
            return
        before = evaluate(registry, read(OUT/"api-configuration.json"))
        registry["episodes"].append(entry)
        after = evaluate(registry, read(OUT/"api-configuration.json"))
        need(after["audited_independent_successes"] == before["audited_independent_successes"]+1,
             "enrollment rejected: " + json.dumps(after["rejected"], ensure_ascii=False))
        atomic_json(OUT/"host-audits.json", registry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "wait", "enroll"), default="check", nargs="?")
    parser.add_argument("--receipt", help="enroll only: host-receipts/<name>.json relative to R020")
    args = parser.parse_args()
    # Fixed production roots: the CLI cannot point at synthetic test fixtures.
    if args.mode == "enroll":
        need(args.receipt, "--receipt required")
        enroll(args.receipt)
    if args.mode in ("check", "enroll"):
        print(json.dumps(check(), ensure_ascii=False, indent=2))
        return
    with (OUT/"waiter.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        last = None
        while True:
            state = check()
            # This is a local file observer, never a second supervisor/model.
            from delivery_status import refresh
            delivery = refresh()
            state["supervisor_acknowledged"] = delivery.get("acknowledged", False)
            signature = json.dumps({k:v for k,v in state.items() if k != "checked_at"}, sort_keys=True)
            if signature != last:
                print(json.dumps(state, ensure_ascii=False), flush=True)
                last = signature
            # Read-only checking; no launch even when eligible. Restart is safe.
            time.sleep(60)


if __name__ == "__main__":
    main()
