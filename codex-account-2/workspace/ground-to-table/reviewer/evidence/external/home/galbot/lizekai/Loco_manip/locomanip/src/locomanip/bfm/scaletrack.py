"""Standalone ScaleTrack inference for real-robot deployment.

Builds observations manually (no env manager dependency) and runs the
exported ONNX model to produce joint position targets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import mujoco
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Body names tracked by ScaleTrack (same order as training)
BODY_NAMES = (
    "pelvis",
    "left_hip_roll_link",
    "left_knee_link",
    "left_ankle_roll_link",
    "right_hip_roll_link",
    "right_knee_link",
    "right_ankle_roll_link",
    "torso_link",
    "left_shoulder_roll_link",
    "left_elbow_link",
    "left_wrist_yaw_link",
    "right_shoulder_roll_link",
    "right_elbow_link",
    "right_wrist_yaw_link",
)

MODE_CANDIDATES = {
    "Pelvis-1": ["pelvis"],
    "UMI-2": ["left_wrist_yaw_link", "right_wrist_yaw_link"],
    "VR-3": ["pelvis", "left_wrist_yaw_link", "right_wrist_yaw_link"],
    "UMI-4": [
        "left_wrist_yaw_link", "right_wrist_yaw_link",
        "left_ankle_roll_link", "right_ankle_roll_link",
    ],
    "VR-5": [
        "pelvis", "left_wrist_yaw_link", "right_wrist_yaw_link",
        "left_ankle_roll_link", "right_ankle_roll_link",
    ],
    "Head-Hands-3": [
        "torso_link", "left_wrist_yaw_link", "right_wrist_yaw_link",
    ],
    "Head-Hands-Feet-5": [
        "torso_link", "left_wrist_yaw_link", "right_wrist_yaw_link",
        "left_ankle_roll_link", "right_ankle_roll_link",
    ],
    # Whole-body: track all 14 bodies (BFM control_mode 7, "full").  The
    # 14-body target block is always fed regardless of mode; this makes BFM
    # trust every point (incl. hips/knees/feet), so leg pose — e.g. the
    # bin-stomp lift — is constrained instead of sacrificed for balance.
    "Full-14": list(BODY_NAMES),
}

PLAY_FUTURE_IDX = (0, 1, 2, 3, 4, 25)

# Default joint positions (knees-bent keyframe from g1_scaletrack_constants)
DEFAULT_JOINT_POS = {
    "left_hip_pitch_joint": -0.312,
    "left_hip_roll_joint": 0.0,
    "left_hip_yaw_joint": 0.0,
    "left_knee_joint": 0.669,
    "left_ankle_pitch_joint": -0.363,
    "left_ankle_roll_joint": 0.0,
    "right_hip_pitch_joint": -0.312,
    "right_hip_roll_joint": 0.0,
    "right_hip_yaw_joint": 0.0,
    "right_knee_joint": 0.669,
    "right_ankle_pitch_joint": -0.363,
    "right_ankle_roll_joint": 0.0,
    "waist_yaw_joint": 0.0,
    "waist_roll_joint": 0.0,
    "waist_pitch_joint": 0.0,
    "left_shoulder_pitch_joint": 0.2,
    "left_shoulder_roll_joint": 0.2,
    "left_shoulder_yaw_joint": 0.0,
    "left_elbow_joint": 0.6,
    "left_wrist_roll_joint": 0.0,
    "left_wrist_pitch_joint": 0.0,
    "left_wrist_yaw_joint": 0.0,
    "right_shoulder_pitch_joint": 0.2,
    "right_shoulder_roll_joint": -0.2,
    "right_shoulder_yaw_joint": 0.0,
    "right_elbow_joint": 0.6,
    "right_wrist_roll_joint": 0.0,
    "right_wrist_pitch_joint": 0.0,
    "right_wrist_yaw_joint": 0.0,
}

# PD gains from g1_scaletrack_constants (natural_freq=15*2pi, damping_ratio=2)
_NATURAL_FREQ = 10 * 2.0 * 3.1415926535
_DAMPING_RATIO = 2.0
_ARMATURE = {
    "5020": 0.003609725,
    "7520_14": 0.010177520,
    "7520_22": 0.025101925,
    "4010": 0.00425,
    "5010": 0.0021812,
}

# Joint → motor type mapping
_JOINT_MOTOR_TYPE = {
    "left_elbow_joint": "5020",
    "right_elbow_joint": "5020",
    "left_shoulder_pitch_joint": "5020",
    "right_shoulder_pitch_joint": "5020",
    "left_shoulder_roll_joint": "5020",
    "right_shoulder_roll_joint": "5020",
    "left_shoulder_yaw_joint": "5020",
    "right_shoulder_yaw_joint": "5020",
    "left_wrist_roll_joint": "5020",
    "right_wrist_roll_joint": "5020",
    "left_hip_pitch_joint": "7520_14",
    "right_hip_pitch_joint": "7520_14",
    "left_hip_yaw_joint": "7520_14",
    "right_hip_yaw_joint": "7520_14",
    "waist_yaw_joint": "7520_14",
    "left_hip_roll_joint": "7520_22",
    "right_hip_roll_joint": "7520_22",
    "left_knee_joint": "7520_22",
    "right_knee_joint": "7520_22",
    "left_wrist_pitch_joint": "5010",
    "right_wrist_pitch_joint": "5010",
    "left_wrist_yaw_joint": "5010",
    "right_wrist_yaw_joint": "5010",
    "waist_pitch_joint": "5020x2",
    "waist_roll_joint": "5020x2",
    "left_ankle_pitch_joint": "5020x2",
    "right_ankle_pitch_joint": "5020x2",
    "left_ankle_roll_joint": "5020x2",
    "right_ankle_roll_joint": "5020x2",
}


# Per-joint kd scale tweaks on top of the analytic gains (deploy tuning;
# applies to BOTH sim and real track so they stay matched).
_KD_SCALE = {
    "waist_roll_joint": 1.5,
}


def _compute_pd_gains() -> tuple[dict[str, float], dict[str, float]]:
    kp_map: dict[str, float] = {}
    kd_map: dict[str, float] = {}
    for jname, mtype in _JOINT_MOTOR_TYPE.items():
        if mtype == "5020x2":
            arm = _ARMATURE["5020"] * 2
        else:
            arm = _ARMATURE[mtype]
        kp = arm * _NATURAL_FREQ**2
        kd = 2.0 * _DAMPING_RATIO * arm * _NATURAL_FREQ
        kp_map[jname] = kp
        kd_map[jname] = kd * _KD_SCALE.get(jname, 1.0)
    return kp_map, kd_map


def _compute_action_scale() -> dict[str, float]:
    """action_scale = 0.5 * effort_limit / stiffness per joint."""
    effort_limits = {
        "5020": 25.0,
        "7520_14": 88.0,
        "7520_22": 139.0,
        "4010": 5.0,
        "5010": 13.4,
    }
    scale_map: dict[str, float] = {}
    for jname, mtype in _JOINT_MOTOR_TYPE.items():
        if mtype == "5020x2":
            arm = _ARMATURE["5020"] * 2
            effort = effort_limits["5020"] * 2
        else:
            arm = _ARMATURE[mtype]
            effort = effort_limits[mtype]
        stiffness = arm * _NATURAL_FREQ**2
        scale_map[jname] = 0.25 * effort / stiffness
    return scale_map


def _quat_to_rotmat(q: np.ndarray) -> np.ndarray:
    """Convert quaternion (w,x,y,z) to 3x3 rotation matrix. Supports batch."""
    if q.ndim == 1:
        q = q[None]
        squeeze = True
    else:
        squeeze = False
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    r = np.empty((q.shape[0], 3, 3), dtype=np.float32)
    r[:, 0, 0] = 1 - 2*(y*y + z*z)
    r[:, 0, 1] = 2*(x*y - w*z)
    r[:, 0, 2] = 2*(x*z + w*y)
    r[:, 1, 0] = 2*(x*y + w*z)
    r[:, 1, 1] = 1 - 2*(x*x + z*z)
    r[:, 1, 2] = 2*(y*z - w*x)
    r[:, 2, 0] = 2*(x*z - w*y)
    r[:, 2, 1] = 2*(y*z + w*x)
    r[:, 2, 2] = 1 - 2*(x*x + y*y)
    return r[0] if squeeze else r


def _yaw_quat(q: np.ndarray) -> np.ndarray:
    """Extract yaw-only quaternion (w,x,y,z). Supports batch (N,4)."""
    if q.ndim == 1:
        q = q[None]
        squeeze = True
    else:
        squeeze = False
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    yaw = np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
    out = np.zeros_like(q)
    out[:, 0] = np.cos(yaw / 2)
    out[:, 3] = np.sin(yaw / 2)
    return out[0] if squeeze else out


def _quat_inv(q: np.ndarray) -> np.ndarray:
    """Quaternion inverse (conjugate for unit quat). (w,x,y,z)."""
    out = q.copy()
    out[..., 1:] = -out[..., 1:]
    return out


def _quat_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product of two quaternions (w,x,y,z). Supports batch."""
    w1, x1, y1, z1 = q1[..., 0], q1[..., 1], q1[..., 2], q1[..., 3]
    w2, x2, y2, z2 = q2[..., 0], q2[..., 1], q2[..., 2], q2[..., 3]
    out = np.empty_like(q1)
    out[..., 0] = w1*w2 - x1*x2 - y1*y2 - z1*z2
    out[..., 1] = w1*x2 + x1*w2 + y1*z2 - z1*y2
    out[..., 2] = w1*y2 - x1*z2 + y1*w2 + z1*x2
    out[..., 3] = w1*z2 + x1*y2 - y1*x2 + z1*w2
    return out


def _quat_apply(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vector v by quaternion q. q: (...,4), v: (...,3)."""
    t = 2.0 * np.cross(q[..., 1:4], v)
    return v + q[..., 0:1] * t + np.cross(q[..., 1:4], t)


def _quat_conjugate(q: np.ndarray) -> np.ndarray:
    """Quaternion conjugate (same as inverse for unit quat)."""
    return _quat_inv(q)


def _quat_to_tan_norm(q: np.ndarray) -> np.ndarray:
    """Convert quaternion to 6D tan+norm representation. q: (...,4) → (...,6)."""
    ref_tan = np.zeros(q.shape[:-1] + (3,), dtype=np.float32)
    ref_tan[..., 0] = 1.0
    tan = _quat_apply(q, ref_tan)
    ref_norm = np.zeros(q.shape[:-1] + (3,), dtype=np.float32)
    ref_norm[..., 2] = 1.0
    norm = _quat_apply(q, ref_norm)
    return np.concatenate([tan, norm], axis=-1)


def _slerp_wxyz(q0: np.ndarray, q1: np.ndarray, alpha: float) -> np.ndarray:
    """Slerp two wxyz quats with alpha free to exceed [0,1] (extrapolation).
    alpha=0 → q0, alpha=1 → q1, alpha>1 extends along the same geodesic."""
    q0 = np.asarray(q0, dtype=np.float64)
    q1 = np.asarray(q1, dtype=np.float64)
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    if dot > 0.9995:
        out = (1.0 - alpha) * q0 + alpha * q1
    else:
        dot = max(min(dot, 1.0), -1.0)
        theta = np.arccos(dot)
        sin_theta = np.sin(theta)
        w0 = np.sin((1.0 - alpha) * theta) / sin_theta
        w1 = np.sin(alpha * theta) / sin_theta
        out = w0 * q0 + w1 * q1
    n = np.linalg.norm(out)
    out = out / n if n > 1e-8 else q0
    return out.astype(np.float32)


class ScaleTrackMotion:
    """Loaded motion data in ScaleTrack format."""

    def __init__(self, path: str | Path, vr_target: str = "torso_link"):
        # Default: no gripper trace; the parquet 5pt init may overwrite it.
        self.gripper: np.ndarray | None = None
        path = Path(path)
        if path.suffix.lower() == ".parquet":
            self._init_from_parquet_5pt(path, vr_target=vr_target)
            return
        data = np.load(str(path), allow_pickle=False)

        if "head_poses" in data.files and "body_pos_w" not in data.files:
            self._init_from_vr_raw(data, vr_target=vr_target)
            return

        self.body_pos_w = data["body_pos_w"].astype(np.float32)
        self.body_quat_w = data["body_quat_w"].astype(np.float32)
        self.joint_pos = data["joint_pos"].astype(np.float32)
        self.joint_vel = data["joint_vel"].astype(np.float32)
        self.num_frames = self.body_pos_w.shape[0]

        # Slice to tracked bodies if full body set is stored
        if "body_names" in data.files:
            stored_names = [
                b.decode("utf-8") if isinstance(b, bytes) else str(b)
                for b in data["body_names"]
            ]
            body_idx = [stored_names.index(n) for n in BODY_NAMES]
            self.body_pos_w = self.body_pos_w[:, body_idx]
            self.body_quat_w = self.body_quat_w[:, body_idx]

        if "body_lin_vel_w" in data.files:
            self.body_lin_vel_w = data["body_lin_vel_w"].astype(np.float32)
            if "body_names" in data.files:
                self.body_lin_vel_w = self.body_lin_vel_w[:, body_idx]
        else:
            self.body_lin_vel_w = None

        if "body_ang_vel_w" in data.files:
            self.body_ang_vel_w = data["body_ang_vel_w"].astype(np.float32)
            if "body_names" in data.files:
                self.body_ang_vel_w = self.body_ang_vel_w[:, body_idx]
        else:
            self.body_ang_vel_w = None

    def _init_from_vr_raw(self, data, vr_target: str = "torso_link") -> None:
        """Load raw VR pose npz with keys head_poses / l_hand_poses / r_hand_poses
        (each (T, 7) [x, y, z, qw, qx, qy, qz]).

        ``vr_target`` selects which body channel the head pose is mapped to:
          - "torso_link": rigid offset (0,0,0.43) from head sphere center,
            head orientation kept (used by Head-Hands-3).
          - "pelvis": rigid offset (0,0,0.87) under head, yaw-only quat
            (used by VR-3 — pitch/roll dropped because pelvis follows
            heading not head tilt).
        Other body channels stay zero; mode mask must drop them.
        """
        head = data["head_poses"].astype(np.float32)
        l_hand = data["l_hand_poses"].astype(np.float32)
        r_hand = data["r_hand_poses"].astype(np.float32)
        T = head.shape[0]
        num_bodies = len(BODY_NAMES)

        body_pos_w = np.zeros((T, num_bodies, 3), dtype=np.float32)
        body_quat_w = np.zeros((T, num_bodies, 4), dtype=np.float32)
        body_quat_w[:, :, 0] = 1.0  # identity wxyz on unused channels

        head_quat = head[:, 3:7]  # wxyz, (T, 4)

        if vr_target == "torso_link":
            # Head sphere is rigidly offset (0,0,0.43) in torso frame; assume
            # head orientation == torso orientation (no neck DoF in G1).
            offset_local = np.array([0.0, 0.0, 0.43], dtype=np.float32)
            target_pos = head[:, :3] - _quat_apply(
                head_quat, np.broadcast_to(offset_local, (T, 3))
            )
            target_quat = head_quat
        elif vr_target == "pelvis":
            # G1 standing: pelvis world z = 0.755, head world z = 1.229,
            # so head→pelvis offset along world z is 0.474. Use yaw-only
            # head quat (pelvis must stay upright).
            target_pos = head[:, :3].copy()
            target_pos[:, 2] -= 0.474
            # yaw-only wxyz quat
            qw, qx, qy, qz = head_quat[:, 0], head_quat[:, 1], head_quat[:, 2], head_quat[:, 3]
            yaw = np.arctan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
            cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
            target_quat = np.zeros((T, 4), dtype=np.float32)
            target_quat[:, 0] = cy
            target_quat[:, 3] = sy
        else:
            raise ValueError(f"Unsupported vr_target={vr_target!r}")

        ti = BODY_NAMES.index(vr_target)
        lwi = BODY_NAMES.index("left_wrist_yaw_link")
        rwi = BODY_NAMES.index("right_wrist_yaw_link")
        body_pos_w[:, ti] = target_pos
        body_quat_w[:, ti] = target_quat
        body_pos_w[:, lwi] = l_hand[:, :3]
        body_quat_w[:, lwi] = l_hand[:, 3:7]
        body_pos_w[:, rwi] = r_hand[:, :3]
        body_quat_w[:, rwi] = r_hand[:, 3:7]

        self.body_pos_w = body_pos_w
        self.body_quat_w = body_quat_w
        self.joint_pos = np.zeros((T, 29), dtype=np.float32)
        self.joint_vel = np.zeros((T, 29), dtype=np.float32)
        self.body_lin_vel_w = None
        self.body_ang_vel_w = None
        self.num_frames = T

    def _init_from_parquet_5pt(self, parquet_path: Path,
                               vr_target: str = "torso_link") -> None:
        """Load 5-point Pico-style trajectory from a parquet column-store.

        Schema (per row, all float64 except ``frame``):
          frame, head_{xyz qw qx qy qz},
          l_hand_{xyz qw qx qy qz}, r_hand_{xyz qw qx qy qz},
          l_ankle_{xyz qw qx qy qz}, r_ankle_{xyz qw qx qy qz}

        Same head -> torso/pelvis policy as ``_init_from_vr_raw`` (so VR-3 /
        Head-Hands-3 modes route the head consistently); ankle channels go
        straight to the ankle_roll links so UMI-4 / VR-5 / Head-Hands-Feet-5
        can read them. Frame is assumed to be the robot world frame (z-up).
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                f"Loading {parquet_path.name}: pandas/pyarrow are required for "
                "parquet motion files. `pip install pandas pyarrow`."
            ) from e

        df = pd.read_parquet(parquet_path)

        def _cols(prefix: str) -> np.ndarray:
            return df[[f"{prefix}_x", f"{prefix}_y", f"{prefix}_z",
                      f"{prefix}_qw", f"{prefix}_qx", f"{prefix}_qy",
                      f"{prefix}_qz"]].to_numpy(dtype=np.float32)

        head = _cols("head")
        l_hand = _cols("l_hand")
        r_hand = _cols("r_hand")
        l_ankle = _cols("l_ankle")
        r_ankle = _cols("r_ankle")

        T = head.shape[0]
        num_bodies = len(BODY_NAMES)
        body_pos_w = np.zeros((T, num_bodies, 3), dtype=np.float32)
        body_quat_w = np.zeros((T, num_bodies, 4), dtype=np.float32)
        body_quat_w[:, :, 0] = 1.0  # identity wxyz on unused channels

        head_quat = head[:, 3:7]
        if vr_target == "torso_link":
            offset_local = np.array([0.0, 0.0, 0.43], dtype=np.float32)
            target_pos = head[:, :3] - _quat_apply(
                head_quat, np.broadcast_to(offset_local, (T, 3))
            )
            target_quat = head_quat
        elif vr_target == "pelvis":
            target_pos = head[:, :3].copy()
            target_pos[:, 2] -= 0.474
            qw, qx, qy, qz = (head_quat[:, 0], head_quat[:, 1],
                              head_quat[:, 2], head_quat[:, 3])
            yaw = np.arctan2(2 * (qw * qz + qx * qy),
                             1 - 2 * (qy * qy + qz * qz))
            cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
            target_quat = np.zeros((T, 4), dtype=np.float32)
            target_quat[:, 0] = cy
            target_quat[:, 3] = sy
        else:
            raise ValueError(f"Unsupported vr_target={vr_target!r}")

        ti = BODY_NAMES.index(vr_target)
        lwi = BODY_NAMES.index("left_wrist_yaw_link")
        rwi = BODY_NAMES.index("right_wrist_yaw_link")
        lai = BODY_NAMES.index("left_ankle_roll_link")
        rai = BODY_NAMES.index("right_ankle_roll_link")
        body_pos_w[:, ti] = target_pos
        body_quat_w[:, ti] = target_quat
        body_pos_w[:, lwi] = l_hand[:, :3]
        body_quat_w[:, lwi] = l_hand[:, 3:7]
        body_pos_w[:, rwi] = r_hand[:, :3]
        body_quat_w[:, rwi] = r_hand[:, 3:7]
        body_pos_w[:, lai] = l_ankle[:, :3]
        body_quat_w[:, lai] = l_ankle[:, 3:7]
        body_pos_w[:, rai] = r_ankle[:, :3]
        body_quat_w[:, rai] = r_ankle[:, 3:7]

        self.body_pos_w = body_pos_w
        self.body_quat_w = body_quat_w
        self.joint_pos = np.zeros((T, 29), dtype=np.float32)
        self.joint_vel = np.zeros((T, 29), dtype=np.float32)
        self.body_lin_vel_w = None
        self.body_ang_vel_w = None
        self.num_frames = T
        # Optional gripper open/close trace (0=open, 1=closed). Some 5pt
        # parquet files add it; if present we map it to the right-hand dex3
        # trigger so the gripper follows the demo.
        if "gripper" in df.columns:
            self.gripper = df["gripper"].to_numpy(dtype=np.float32)
        else:
            self.gripper = None

    def reconstruct_missing_bodies(self, mj_model: mujoco.MjModel) -> int:
        """For any tracked body whose stored body_pos_w / body_quat_w is
        all-zero (commonly true for non-pelvis/non-wrist bodies in some
        retargeted npz files), recompute its world pose from joint_pos +
        pelvis pose via FK. Returns the number of bodies overwritten.
        """
        T = self.num_frames
        # A body is "missing" if its position is identically zero everywhere.
        pos_norm = np.linalg.norm(self.body_pos_w, axis=-1)  # (T, 14)
        quat_norm = np.linalg.norm(self.body_quat_w, axis=-1)  # (T, 14)
        missing_pos = (pos_norm < 1e-6).all(axis=0)  # (14,)
        # quaternions of (0,0,0,0) are also invalid; (1,0,0,0) is valid
        missing_quat = (quat_norm < 1e-6).all(axis=0)  # (14,)
        missing = missing_pos | missing_quat
        if not missing.any():
            return 0

        body_ids = np.array([
            mujoco.mj_name2id(mj_model, mujoco.mjtObj.mjOBJ_BODY, n)
            for n in BODY_NAMES
        ])
        # joint_pos columns are the 29 canonical policy joints; scatter by
        # name so models with extra joints (dex3 fingers) FK correctly.
        qadr29 = np.array([
            mj_model.jnt_qposadr[mj_model.joint(n).id] for n in DEFAULT_JOINT_POS
        ])
        data = mujoco.MjData(mj_model)
        for t in range(T):
            data.qpos[:] = 0.0
            data.qpos[0:3] = self.body_pos_w[t, 0]
            data.qpos[3:7] = self.body_quat_w[t, 0]
            data.qpos[qadr29] = self.joint_pos[t]
            data.qvel[:] = 0.0
            mujoco.mj_forward(mj_model, data)
            for bi, bid in enumerate(body_ids):
                if missing[bi]:
                    self.body_pos_w[t, bi] = data.xpos[bid]
                    self.body_quat_w[t, bi] = data.xquat[bid]
        n_fixed = int(missing.sum())
        return n_fixed

    def rebias(
        self,
        robot_pos: np.ndarray,
        robot_quat: np.ndarray,
        ref_body_name: str = "pelvis",
    ) -> "ScaleTrackMotion":
        """Return a copy with the trajectory rebiased so frame 0 of
        ``ref_body_name`` aligns (xy, yaw) with the given robot pose.

        z and roll/pitch are kept; only xy and yaw are aligned.
        Use a body that actually has motion data (e.g. ``torso_link`` for
        VR Head-Hands-3 inputs where pelvis is unfilled).
        """
        import copy
        out = copy.copy(self)

        ref_idx = BODY_NAMES.index(ref_body_name)
        ref_pos0 = self.body_pos_w[0, ref_idx]  # (3,)
        ref_quat0 = self.body_quat_w[0, ref_idx]  # (4,) wxyz

        # Extract yaw from both
        ref_yaw = np.arctan2(
            2 * (ref_quat0[0] * ref_quat0[3] + ref_quat0[1] * ref_quat0[2]),
            1 - 2 * (ref_quat0[2]**2 + ref_quat0[3]**2),
        )
        robot_yaw = np.arctan2(
            2 * (robot_quat[0] * robot_quat[3] + robot_quat[1] * robot_quat[2]),
            1 - 2 * (robot_quat[2]**2 + robot_quat[3]**2),
        )
        d_yaw = float(robot_yaw - ref_yaw)

        # Yaw rotation quaternion
        cy, sy = np.cos(d_yaw / 2), np.sin(d_yaw / 2)
        q_yaw = np.array([cy, 0, 0, sy], dtype=np.float32)

        # Vectorized position rotation: (T, 14, 3)
        dp = self.body_pos_w - ref_pos0[None, None, :]  # (T, 14, 3)
        cos_dy, sin_dy = np.cos(d_yaw), np.sin(d_yaw)
        new_pos = np.empty_like(dp)
        new_pos[..., 0] = cos_dy * dp[..., 0] - sin_dy * dp[..., 1]
        new_pos[..., 1] = sin_dy * dp[..., 0] + cos_dy * dp[..., 1]
        new_pos[..., 2] = dp[..., 2]
        offset = np.array([robot_pos[0], robot_pos[1], ref_pos0[2]], dtype=np.float32)
        out.body_pos_w = new_pos + offset[None, None, :]

        # Vectorized quaternion rotation: q_yaw * each quat
        # Broadcast q_yaw (4,) over (T, 14, 4)
        out.body_quat_w = _quat_mul(
            np.broadcast_to(q_yaw, self.body_quat_w.shape),
            self.body_quat_w,
        )

        out.num_frames = self.num_frames
        return out


# A-pose left arm joint targets: arm pushed outward in y (shoulder roll abducts
# the upper arm) with elbow folded so the wrist sits at pelvis height but
# noticeably outside the body.
_APOSE_LEFT_ARM = {
    "left_shoulder_pitch_joint": 0.0,
    "left_shoulder_roll_joint": 0.4,
    "left_shoulder_yaw_joint": 0.0,
    "left_elbow_joint": 1.6,
    "left_wrist_roll_joint": 0.0,
    "left_wrist_pitch_joint": 0.0,
    "left_wrist_yaw_joint": 0.0,
}


def _compute_apose_left_wrist_local(mj_model: mujoco.MjModel) -> tuple[np.ndarray, np.ndarray]:
    """Return (offset_in_pelvis, quat_rel_pelvis_wxyz) for left_wrist_yaw_link
    when the left arm is in A-pose. The rest of the body is at DEFAULT_JOINT_POS
    so the pelvis frame is well-defined.
    """
    data = mujoco.MjData(mj_model)
    data.qpos[:] = 0.0
    data.qpos[2] = 0.755
    data.qpos[3] = 1.0  # identity quat
    joint_names = []
    for i in range(1, mj_model.njnt):
        joint_names.append(mujoco.mj_id2name(mj_model, mujoco.mjtObj.mjOBJ_JOINT, i))
    for i, jname in enumerate(joint_names):
        if jname in _APOSE_LEFT_ARM:
            data.qpos[7 + i] = _APOSE_LEFT_ARM[jname]
        else:
            data.qpos[7 + i] = DEFAULT_JOINT_POS.get(jname, 0.0)
    mujoco.mj_forward(mj_model, data)

    pelvis_id = mujoco.mj_name2id(mj_model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
    wrist_id = mujoco.mj_name2id(mj_model, mujoco.mjtObj.mjOBJ_BODY, "left_wrist_yaw_link")

    pelvis_pos = np.array(data.xpos[pelvis_id], dtype=np.float32)
    pelvis_quat = np.array(data.xquat[pelvis_id], dtype=np.float32)
    wrist_pos = np.array(data.xpos[wrist_id], dtype=np.float32)
    wrist_quat = np.array(data.xquat[wrist_id], dtype=np.float32)

    offset_world = wrist_pos - pelvis_pos
    offset_local = _quat_apply(_quat_inv(pelvis_quat), offset_world)
    quat_rel = _quat_mul(_quat_inv(pelvis_quat), wrist_quat)
    return offset_local, quat_rel


def override_left_wrist_apose(motion: ScaleTrackMotion, mj_model: mujoco.MjModel) -> None:
    """Replace motion's left_wrist_yaw_link pos/quat per frame with an A-pose
    target expressed in the pelvis frame. Mutates `motion` in place.
    """
    lw_idx = BODY_NAMES.index("left_wrist_yaw_link")
    offset_local, quat_rel = _compute_apose_left_wrist_local(mj_model)

    pelvis_pos = motion.body_pos_w[:, 0]  # (T, 3)
    pelvis_quat = motion.body_quat_w[:, 0]  # (T, 4)

    offset_world = _quat_apply(
        pelvis_quat, np.broadcast_to(offset_local, pelvis_pos.shape)
    )
    motion.body_pos_w[:, lw_idx] = (pelvis_pos + offset_world).astype(np.float32)
    motion.body_quat_w[:, lw_idx] = _quat_mul(
        pelvis_quat, np.broadcast_to(quat_rel, pelvis_quat.shape)
    ).astype(np.float32)


def _foot_slip_max_still_ms(motion: ScaleTrackMotion, fps: float = 50.0,
                            still_mps: float = 0.05) -> float:
    """Discriminate "real footstep" vs "mocap-solver slip" data.

    Walking data has at least one foot resting motionless for >= ~250 ms at
    a time (stance phase); when the solver mis-classifies sliding feet as
    walking the same trajectory's longest single-foot still run is < 150 ms.
    Return ``max(L_longest, R_longest)`` in ms — higher = cleaner.
    """
    ankle_names = ("left_ankle_roll_link", "right_ankle_roll_link")
    best = 0.0
    for nm in ankle_names:
        idx = BODY_NAMES.index(nm)
        xy = motion.body_pos_w[:, idx, :2]
        v_mps = np.linalg.norm(np.diff(xy, axis=0), axis=1) * fps
        still = v_mps < still_mps
        run = 0
        longest = 0
        for s in still:
            run = run + 1 if s else 0
            if run > longest:
                longest = run
        ms = longest / fps * 1000.0
        if ms > best:
            best = ms
    return float(best)


def prepend_hold_frames(motion: ScaleTrackMotion, n_hold: int) -> ScaleTrackMotion:
    """Return a shallow copy of ``motion`` whose trajectory has ``n_hold``
    copies of frame 0 prepended in front of every per-time-step array. So the
    policy's future-offset reads see a TRULY frozen reference for the first
    ``n_hold`` ticks; once track_step crosses ``n_hold`` the original motion
    advances normally. Velocity-shaped arrays (lin_vel / ang_vel) hold zero
    during the prepended region — there's no motion at frame 0 by construction.
    """
    import copy
    if n_hold <= 0:
        return motion
    out = copy.copy(motion)
    hold_pos = np.broadcast_to(
        motion.body_pos_w[0:1], (n_hold, *motion.body_pos_w.shape[1:])
    ).copy()
    hold_quat = np.broadcast_to(
        motion.body_quat_w[0:1], (n_hold, *motion.body_quat_w.shape[1:])
    ).copy()
    out.body_pos_w = np.concatenate([hold_pos, motion.body_pos_w], axis=0)
    out.body_quat_w = np.concatenate([hold_quat, motion.body_quat_w], axis=0)
    hold_jp = np.broadcast_to(
        motion.joint_pos[0:1], (n_hold, *motion.joint_pos.shape[1:])
    ).copy()
    hold_jv = np.zeros((n_hold, *motion.joint_vel.shape[1:]),
                       dtype=motion.joint_vel.dtype)
    out.joint_pos = np.concatenate([hold_jp, motion.joint_pos], axis=0)
    out.joint_vel = np.concatenate([hold_jv, motion.joint_vel], axis=0)
    if motion.body_lin_vel_w is not None:
        zeros = np.zeros((n_hold, *motion.body_lin_vel_w.shape[1:]),
                         dtype=motion.body_lin_vel_w.dtype)
        out.body_lin_vel_w = np.concatenate(
            [zeros, motion.body_lin_vel_w], axis=0)
    if motion.body_ang_vel_w is not None:
        zeros = np.zeros((n_hold, *motion.body_ang_vel_w.shape[1:]),
                         dtype=motion.body_ang_vel_w.dtype)
        out.body_ang_vel_w = np.concatenate(
            [zeros, motion.body_ang_vel_w], axis=0)
    gripper = getattr(motion, "gripper", None)
    if gripper is not None:
        # Hold frame 0's gripper value across the prepended region so the
        # trigger does not jump when the trajectory begins playing.
        hold_g = np.full((n_hold,), float(gripper[0]), dtype=gripper.dtype)
        out.gripper = np.concatenate([hold_g, gripper], axis=0)
    out.num_frames = motion.num_frames + n_hold
    return out


def insert_hold_frames(motion: ScaleTrackMotion,
                       at_idx: int, n_hold: int) -> ScaleTrackMotion:
    """Return a shallow copy of ``motion`` with ``n_hold`` copies of
    ``motion[at_idx]`` inserted right after index ``at_idx``. Used to give the
    dex3 gripper a few extra ticks at the grasp instant to settle on the cube.
    Per-time-step arrays are spliced in place; velocity arrays use zeros for
    the hold region (no motion during a static hold).
    """
    import copy
    if n_hold <= 0:
        return motion
    out = copy.copy(motion)
    i = at_idx + 1
    n_hold = int(n_hold)

    def _splice_hold(arr, hold_value):
        if arr is None:
            return None
        return np.concatenate([arr[:i], hold_value, arr[i:]], axis=0)

    rep_pos = np.broadcast_to(motion.body_pos_w[at_idx:at_idx + 1],
                              (n_hold, *motion.body_pos_w.shape[1:])).copy()
    rep_quat = np.broadcast_to(motion.body_quat_w[at_idx:at_idx + 1],
                               (n_hold, *motion.body_quat_w.shape[1:])).copy()
    out.body_pos_w = _splice_hold(motion.body_pos_w, rep_pos)
    out.body_quat_w = _splice_hold(motion.body_quat_w, rep_quat)
    rep_jp = np.broadcast_to(motion.joint_pos[at_idx:at_idx + 1],
                             (n_hold, *motion.joint_pos.shape[1:])).copy()
    rep_jv = np.zeros((n_hold, *motion.joint_vel.shape[1:]),
                      dtype=motion.joint_vel.dtype)
    out.joint_pos = _splice_hold(motion.joint_pos, rep_jp)
    out.joint_vel = _splice_hold(motion.joint_vel, rep_jv)
    if motion.body_lin_vel_w is not None:
        zeros = np.zeros((n_hold, *motion.body_lin_vel_w.shape[1:]),
                         dtype=motion.body_lin_vel_w.dtype)
        out.body_lin_vel_w = _splice_hold(motion.body_lin_vel_w, zeros)
    if motion.body_ang_vel_w is not None:
        zeros = np.zeros((n_hold, *motion.body_ang_vel_w.shape[1:]),
                         dtype=motion.body_ang_vel_w.dtype)
        out.body_ang_vel_w = _splice_hold(motion.body_ang_vel_w, zeros)
    gripper = getattr(motion, "gripper", None)
    if gripper is not None:
        rep_g = np.full((n_hold,), float(gripper[at_idx]), dtype=gripper.dtype)
        out.gripper = _splice_hold(gripper, rep_g)
    out.num_frames = motion.num_frames + n_hold
    return out


def load_scaletrack_motions(
    motion_dir: str | Path,
    vr_target: str = "torso_link",
    filter_foot_slip: bool = False,
    slip_threshold_ms: float = 250.0,
) -> list[ScaleTrackMotion]:
    """Load all .npz / .parquet motion files from a directory.

    ``vr_target`` is forwarded to ``ScaleTrackMotion`` and only matters for
    raw VR npz inputs (head/l_hand/r_hand_poses) and parquet 5-point inputs;
    ScaleTrack-format full-body files ignore it.

    ``filter_foot_slip`` drops trajectories whose longer foot stance has the
    max contiguous-near-still run shorter than ``slip_threshold_ms`` (i.e. no
    foot ever truly rests; almost always a mocap solver bug). Skip-list is
    printed so it is easy to spot-check.
    """
    motion_dir = Path(motion_dir)
    if motion_dir.is_file():
        return [ScaleTrackMotion(motion_dir, vr_target=vr_target)]
    paths = sorted(list(motion_dir.glob("*.npz"))
                   + list(motion_dir.glob("*.parquet")))
    motions: list[ScaleTrackMotion] = []
    skipped: list[tuple[str, float]] = []
    for p in paths:
        m = ScaleTrackMotion(p, vr_target=vr_target)
        if filter_foot_slip:
            stance_ms = _foot_slip_max_still_ms(m)
            if stance_ms < slip_threshold_ms:
                skipped.append((p.name, stance_ms))
                continue
        motions.append(m)
    if skipped:
        print(f"[load_scaletrack_motions] filtered {len(skipped)}/{len(paths)} "
              f"slipping-foot motion(s) (max-still < {slip_threshold_ms:.0f} ms):")
        for name, ms in skipped[:10]:
            print(f"  - {name}  (max-still = {ms:.0f} ms)")
        if len(skipped) > 10:
            print(f"  ... (+{len(skipped) - 10} more)")
    return motions


class ScaleTrackInferFn:
    """Standalone ScaleTrack ONNX inference for deploy.

    Builds observations from raw sensor data and runs the ONNX model.
    """

    def __init__(
        self,
        onnx_path: str | Path | None,
        mj_model: mujoco.MjModel,
        mode_name: str = "Head-Hands-3",
        ctrl_dt: float = 0.02,
        future_idx: tuple[int, ...] = PLAY_FUTURE_IDX,
    ):
        self.mj_model = mj_model
        self.ctrl_dt = ctrl_dt
        self.future_idx = future_idx
        self.num_bodies = len(BODY_NAMES)
        self.num_joints = 29
        self.history_len = 3
        self.num_future = len(future_idx)

        # ONNX session.  ``onnx_path=None`` is the subclass entry point
        # (ScaleTrackRawInferFn runs the same policy in torch from a raw
        # rsl_rl checkpoint); everything below — joint maps, gains, mode
        # masks, history buffers — is shared by both paths.
        self.session = None
        if onnx_path is not None:
            assert ort is not None, "onnxruntime is required"
            sess_opts = ort.SessionOptions()
            sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_opts.log_severity_level = 4  # suppress all warnings including C++ ScatterND
            self.session = ort.InferenceSession(
                str(onnx_path), sess_options=sess_opts,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            active = self.session.get_providers()
            print(f"[ScaleTrack] Loaded {Path(onnx_path).name}  providers={active}")

        # Resolve body IDs in mj_model
        self.body_ids = np.array(
            [mj_model.body(n).id for n in BODY_NAMES], dtype=np.int32
        )

        # Joint names (order matches mj_model joints 1..njnt, skipping floating base)
        self.joint_names = []
        for i in range(1, mj_model.njnt):
            self.joint_names.append(mujoco.mj_id2name(mj_model, mujoco.mjtObj.mjOBJ_JOINT, i))

        # The 29 canonical policy joints (DEFAULT_JOINT_POS order == training
        # action order). On the plain track model this is the identity; on a
        # model with extra joints (e.g. dex3 fingers, interleaved after each
        # wrist_yaw in qpos) the policy I/O gathers/scatters through these maps
        # and the extra joints are left to the caller.
        canonical = list(DEFAULT_JOINT_POS.keys())
        self.policy_jnt_idx = np.array(
            [self.joint_names.index(n) for n in canonical], dtype=np.int64
        )
        self._policy_qpos_adr = np.array(
            [mj_model.jnt_qposadr[mj_model.joint(n).id] for n in canonical],
            dtype=np.int64,
        )
        self._policy_dof_adr = np.array(
            [mj_model.jnt_dofadr[mj_model.joint(n).id] for n in canonical],
            dtype=np.int64,
        )
        if len(self.joint_names) != len(canonical):
            extra = [n for n in self.joint_names if n not in canonical]
            print(f"[ScaleTrack] model has {len(extra)} extra (non-policy) joints: "
                  f"{extra[0]}..{extra[-1]} — policy I/O mapped by name.")

        # Default qpos and action scale (ordered by mj_model joints, full length)
        self.default_qpos = np.array(
            [DEFAULT_JOINT_POS.get(n, 0.0) for n in self.joint_names],
            dtype=np.float32,
        )
        action_scale_map = self._action_scale_map()
        self.action_scale = np.array(
            [action_scale_map.get(n, 0.5) for n in self.joint_names],
            dtype=np.float32,
        )
        # Policy-space (29, canonical-order) views used by obs/action code.
        self._default_qpos_p = self.default_qpos[self.policy_jnt_idx]
        self._action_scale_p = self.action_scale[self.policy_jnt_idx]

        # PD gains (full model joint order; gather with policy_jnt_idx for 29).
        kp_map, kd_map = self._pd_gain_maps(onnx_path)
        self.kp = np.array([kp_map.get(n, 30.0) for n in self.joint_names], dtype=np.float32)
        self.kd = np.array([kd_map.get(n, 1.0) for n in self.joint_names], dtype=np.float32)

        # Mode mask
        mode_links = MODE_CANDIDATES.get(mode_name, MODE_CANDIDATES["Head-Hands-3"])
        self.mode = np.zeros((1, self.num_bodies), dtype=np.float32)
        for link_name in mode_links:
            idx = BODY_NAMES.index(link_name)
            self.mode[0, idx] = 1.0

        # When the mode does not track pelvis, the policy must control pelvis
        # pitch / roll / yaw all freely, so we cannot collapse the anchor to
        # yaw-only — the ref points (which are expressed relative to the
        # robot anchor) need the full anchor quat to keep their pitch/roll
        # information intact.
        self._full_anchor_quat = "pelvis" not in mode_links

        # Mode mapping: expand mode to feature dims [3, 3, 6, 6] + time(1)
        feature_dims = [3, 3, 6, 6]
        mappings = []
        for dim in feature_dims:
            expanded = np.repeat(self.mode[0], dim)  # (14*dim,)
            mappings.append(expanded)
        mappings.append(np.ones(1, dtype=np.float32))  # time
        self.mode_mapping = np.concatenate(mappings)[None]  # (1, 253)

        # History buffers
        self.policy_history = np.zeros((1, self.history_len, 64), dtype=np.float32)
        self.action_history = np.zeros((1, self.history_len, self.num_joints), dtype=np.float32)

        # IMU sensor IDs (deploy XML uses gyro_pelvis, training uses imu_ang_vel)
        for gyro_name in ("gyro_pelvis", "imu_ang_vel"):
            try:
                self._gyro_sensor_id = mj_model.sensor(gyro_name).id
                break
            except KeyError:
                continue
        else:
            raise RuntimeError("No gyro sensor found (tried gyro_pelvis, imu_ang_vel)")
        self._gyro_adr = mj_model.sensor_adr[self._gyro_sensor_id]

    # ---- gain / scale hooks (overridden by ScaleTrackRawInferFn) ----------

    def _pd_gain_maps(
        self, ckpt_path: str | Path | None
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Joint-name → (kp, kd) for this checkpoint's training config.

        Prefer training-side gains from a sibling *_metadata.json (mjlab
        serializes g1_scaletrack_constants stiffness/damping there); fall
        back to the analytic 10Hz·2π/ζ=2 formula only when no metadata is
        present.  Reason: the analytic gains diverge from training for
        waist_{yaw,roll,pitch} (14–40% of trained kp) and
        {left,right}_wrist_{pitch,yaw} (~51% of trained kp) — running with
        softer wrists made the FSQ ONNX under-track the hand ref, and
        hand_comp (a 20 N task-space wrench) couldn't compensate for the
        under-stiff servo.
        """
        kp_map, kd_map = _compute_pd_gains()
        if ckpt_path is None:
            return kp_map, kd_map
        meta_candidates = sorted(Path(ckpt_path).parent.glob("*_metadata.json"))
        if meta_candidates:
            import json
            meta = json.load(open(meta_candidates[0]))
            meta_kp = dict(zip(meta["joint_names"], meta["stiffness"]))
            meta_kd = dict(zip(meta["joint_names"], meta["damping"]))
            kp_map = {n: meta_kp.get(n, kp_map.get(n, 30.0)) for n in kp_map}
            kd_map = {n: meta_kd.get(n, kd_map.get(n, 1.0)) for n in kd_map}
            print(f"[ScaleTrack] PD gains loaded from {meta_candidates[0].name}")
        return kp_map, kd_map

    def _action_scale_map(self) -> dict[str, float]:
        """Joint-name → action scale for this checkpoint's training config."""
        return _compute_action_scale()

    def _run_policy(self, policy_task: np.ndarray) -> np.ndarray:
        """(F, 253) task obs + the current history buffers → action (29,).

        The ONNX graph applies the mode mask and concatenates ``mode``
        internally, so the 253-d block is fed as-is here.
        """
        outputs = self.session.run(
            ["actions"],
            {
                "policy": self.policy_history,
                "policy_task": policy_task[None],  # (1, num_future, 253)
                "action": self.action_history,
                "mode": self.mode,
                "mode_mapping": self.mode_mapping,
            },
        )
        return outputs[0][0]  # (29,)

    def reset(self):
        """Reset history buffers."""
        self.policy_history[:] = 0
        self.action_history[:] = 0

    def warm_start(self, mj_data: mujoco.MjData):
        """Fill history buffers with current state to avoid soft start."""
        root_quat = mj_data.qpos[3:7].astype(np.float32)
        gyro = mj_data.sensordata[self._gyro_adr:self._gyro_adr+3].astype(np.float32)
        jnt_qpos = mj_data.qpos[self._policy_qpos_adr].astype(np.float32)
        jnt_qvel = mj_data.qvel[self._policy_dof_adr].astype(np.float32)
        obs = self._build_policy_obs(root_quat, gyro, jnt_qpos, jnt_qvel)
        for i in range(self.history_len):
            self.policy_history[0, i] = obs
        # Action history: current pose expressed as action
        action = (jnt_qpos - self._default_qpos_p) / self._action_scale_p
        for i in range(self.history_len):
            self.action_history[0, i] = action

    def _build_policy_obs(
        self,
        root_quat: np.ndarray,
        gyro: np.ndarray,
        jnt_qpos: np.ndarray,
        jnt_qvel: np.ndarray,
    ) -> np.ndarray:
        """Build single-frame policy observation (64,).

        Args:
            root_quat: pelvis quaternion (w,x,y,z) shape (4,)
            gyro: angular velocity in pelvis frame (3,)
            jnt_qpos: joint positions (29,)
            jnt_qvel: joint velocities (29,)
        """
        # projected_gravity = -R_pelvis^T @ [0,0,1]
        rot = _quat_to_rotmat(root_quat)  # (3,3)
        proj_grav = -rot.T @ np.array([0, 0, 1], dtype=np.float32)

        # joint_pos_rel
        joint_pos_rel = jnt_qpos - self._default_qpos_p

        # joint_vel scaled
        joint_vel_scaled = jnt_qvel * 0.05

        obs = np.concatenate([proj_grav, gyro, joint_pos_rel, joint_vel_scaled])
        return obs.astype(np.float32)

    def _build_policy_task(
        self,
        robot_anchor_pos: np.ndarray,
        robot_anchor_quat: np.ndarray,
        robot_body_pos: np.ndarray,
        robot_body_quat: np.ndarray,
        motion: ScaleTrackMotion,
        time_step: int,
    ) -> np.ndarray:
        """Build policy_task observation (num_future, 253).

        Computes target body pos/rot relative to robot anchor for future frames.
        """
        num_future = self.num_future
        task_obs = np.zeros((num_future, 253), dtype=np.float32)

        # Robot heading. Default (pelvis tracked) uses yaw-only — pelvis
        # pitch/roll are observed via gravity and the ref frame stays
        # heading-aligned. For modes that don't track pelvis (e.g.
        # Head-Hands-3), pelvis pitch/roll/yaw are all free DoFs, so the
        # anchor must keep the full quat — otherwise ref points lose their
        # pitch/roll information relative to the robot's actual base.
        if self._full_anchor_quat:
            heading_quat = robot_anchor_quat.astype(np.float32)
        else:
            heading_quat = _yaw_quat(robot_anchor_quat)
        heading_inv = _quat_inv(heading_quat)  # (4,)

        # Live Pico path: the ref stream is buffered into a real multi-frame
        # motion (resampled history, newest sample at the last frame) by
        # pico_source.RefBuffer, so no special case is needed here — every
        # future offset reads a genuine trajectory frame.
        for fi, offset in enumerate(self.future_idx):
            t = min(time_step + offset, motion.num_frames - 1)
            future_body_pos = motion.body_pos_w[t].copy()  # (14, 3)
            future_body_quat = motion.body_quat_w[t].copy()  # (14, 4)

            # target_body_pos: future pos relative to robot anchor in heading frame
            heading_inv_expand = np.tile(heading_inv, (self.num_bodies, 1))  # (14, 4)
            rel_pos = future_body_pos - robot_anchor_pos[None, :]  # (14, 3)
            target_pos = _quat_apply(heading_inv_expand, rel_pos)  # (14, 3)

            # target_body_pos_rel: future pos relative to current robot body pos
            rel_pos_to_body = future_body_pos - robot_body_pos  # (14, 3)
            target_pos_rel = _quat_apply(heading_inv_expand, rel_pos_to_body)  # (14, 3)

            # target_body_rot: future rot relative to heading
            target_rot_quat = _quat_mul(heading_inv_expand, future_body_quat)  # (14, 4)
            target_rot = _quat_to_tan_norm(target_rot_quat)  # (14, 6)

            # target_body_rot_rel: rotation difference from current to future
            current_body_quat = robot_body_quat  # (14, 4)
            rel_rot = _quat_mul(future_body_quat, _quat_conjugate(current_body_quat))
            # Transform to heading frame: heading_inv * rel * heading
            heading_expand = np.tile(heading_quat, (self.num_bodies, 1))
            target_rot_rel_quat = _quat_mul(
                _quat_mul(heading_inv_expand, rel_rot), heading_expand
            )
            target_rot_rel = _quat_to_tan_norm(target_rot_rel_quat)  # (14, 6)

            # timestamp
            timestamp = float(offset)

            # Pack: pos(42) + pos_rel(42) + rot(84) + rot_rel(84) + time(1) = 253
            idx = 0
            task_obs[fi, idx:idx+42] = target_pos.reshape(-1)
            idx += 42
            task_obs[fi, idx:idx+42] = target_pos_rel.reshape(-1)
            idx += 42
            task_obs[fi, idx:idx+84] = target_rot.reshape(-1)
            idx += 84
            task_obs[fi, idx:idx+84] = target_rot_rel.reshape(-1)
            idx += 84
            task_obs[fi, idx] = timestamp

        return task_obs

    def infer(
        self,
        mj_data: mujoco.MjData,
        motion: ScaleTrackMotion,
        time_step: int,
    ) -> np.ndarray:
        """Run inference from MuJoCo simulation state.

        Returns joint position targets (29,).
        """
        # Extract state from mj_data (29 policy joints, canonical order)
        root_quat = mj_data.qpos[3:7].astype(np.float32)
        gyro = mj_data.sensordata[self._gyro_adr:self._gyro_adr+3].astype(np.float32)
        jnt_qpos = mj_data.qpos[self._policy_qpos_adr].astype(np.float32)
        jnt_qvel = mj_data.qvel[self._policy_dof_adr].astype(np.float32)

        # Robot body state
        robot_anchor_pos = mj_data.xpos[self.body_ids[0]].astype(np.float32)  # pelvis
        robot_anchor_quat = self._body_quat_wxyz(mj_data, self.body_ids[0])
        robot_body_pos = mj_data.xpos[self.body_ids].astype(np.float32)  # (14, 3)
        robot_body_quat = np.array(
            [self._body_quat_wxyz(mj_data, bid) for bid in self.body_ids],
            dtype=np.float32,
        )  # (14, 4)

        return self._infer_common(
            root_quat, gyro, jnt_qpos, jnt_qvel,
            robot_anchor_pos, robot_anchor_quat,
            robot_body_pos, robot_body_quat,
            motion, time_step,
        )

    def infer_real(
        self,
        root_quat: np.ndarray,
        root_gyro: np.ndarray,
        jnt_qpos: np.ndarray,
        jnt_qvel: np.ndarray,
        robot_body_pos: np.ndarray,
        robot_body_quat: np.ndarray,
        motion: ScaleTrackMotion,
        time_step: int,
    ) -> np.ndarray:
        """Run inference from real robot sensor data.

        Args:
            root_quat: pelvis quaternion (w,x,y,z) shape (4,)
            root_gyro: angular velocity in pelvis frame (3,)
            jnt_qpos: joint positions (29,)
            jnt_qvel: joint velocities (29,)
            robot_body_pos: tracked body positions (14, 3) from FK
            robot_body_quat: tracked body quaternions (14, 4) wxyz from FK
            motion: reference motion
            time_step: current frame index

        Returns joint position targets (29,).
        """
        robot_anchor_pos = robot_body_pos[0]  # pelvis
        robot_anchor_quat = robot_body_quat[0]
        return self._infer_common(
            root_quat.astype(np.float32),
            root_gyro.astype(np.float32),
            jnt_qpos.astype(np.float32),
            jnt_qvel.astype(np.float32),
            robot_anchor_pos.astype(np.float32),
            robot_anchor_quat.astype(np.float32),
            robot_body_pos.astype(np.float32),
            robot_body_quat.astype(np.float32),
            motion, time_step,
        )

    def _infer_common(
        self,
        root_quat: np.ndarray,
        gyro: np.ndarray,
        jnt_qpos: np.ndarray,
        jnt_qvel: np.ndarray,
        robot_anchor_pos: np.ndarray,
        robot_anchor_quat: np.ndarray,
        robot_body_pos: np.ndarray,
        robot_body_quat: np.ndarray,
        motion: ScaleTrackMotion,
        time_step: int,
    ) -> np.ndarray:
        # Build policy obs
        policy_obs = self._build_policy_obs(root_quat, gyro, jnt_qpos, jnt_qvel)

        # Update policy history (shift left, append new)
        self.policy_history[0, :-1] = self.policy_history[0, 1:]
        self.policy_history[0, -1] = policy_obs

        # Build policy_task
        policy_task = self._build_policy_task(
            robot_anchor_pos, robot_anchor_quat,
            robot_body_pos, robot_body_quat,
            motion, time_step,
        )

        action = self._run_policy(policy_task)

        # Update action history
        self.action_history[0, :-1] = self.action_history[0, 1:]
        self.action_history[0, -1] = action

        # Convert action to joint targets (29, canonical policy order)
        joint_targets = action * self._action_scale_p + self._default_qpos_p
        return joint_targets

    def _body_quat_wxyz(self, mj_data: mujoco.MjData, body_id: int) -> np.ndarray:
        """Get body quaternion in (w,x,y,z) format from xmat."""
        xmat = mj_data.xmat[body_id].reshape(3, 3)
        # Convert rotation matrix to quaternion (w,x,y,z)
        from scipy.spatial.transform import Rotation as R
        rot = R.from_matrix(xmat)
        q_xyzw = rot.as_quat()  # (x,y,z,w)
        return np.array([q_xyzw[3], q_xyzw[0], q_xyzw[1], q_xyzw[2]], dtype=np.float32)


class ScaleTrackNaviInferFn(ScaleTrackInferFn):
    """Navi-frame ScaleTrack ONNX (``ckpts/navi_tracker_interface.md``).

    Same graph / proprio / FSQ / action decode as the FSQ ONNX baseline —
    the ONLY change is the ``policy_task`` coordinate convention
    (``policy_obs_navi_frame: true`` runs, e.g. ``model_2250.onnx``):

      - anchor rotation is ALWAYS yaw-only (``yaw_quat(pelvis)``), never the
        full pelvis quat, regardless of mode;
      - anchor origin z = 0, so target z is the reference's ABSOLUTE height
        (baseline subtracts robot pelvis z);
      - pos_rel zeroes the robot body z, so the per-body error is horizontal
        only (z again passes through as absolute reference height).

    Frame 5 of ``future_idx`` is the far-goal slot (trained offset 5–33
    steps); ``PLAY_FUTURE_IDX`` pins it to 25, mid training range.
    坑: navi ckpt 用 baseline pelvis 系公式喂也能跑, 只是默默变差 — 维度
    完全相同, 分派只能靠 --navi 开关, 没法从 ONNX 图嗅探.
    """

    def _build_policy_task(
        self,
        robot_anchor_pos: np.ndarray,
        robot_anchor_quat: np.ndarray,
        robot_body_pos: np.ndarray,
        robot_body_quat: np.ndarray,
        motion: ScaleTrackMotion,
        time_step: int,
    ) -> np.ndarray:
        num_future = self.num_future
        task_obs = np.zeros((num_future, 253), dtype=np.float32)

        navi_quat = _yaw_quat(robot_anchor_quat).astype(np.float32)
        navi_inv = _quat_inv(navi_quat)
        navi_inv_expand = np.tile(navi_inv, (self.num_bodies, 1))    # (14, 4)
        navi_expand = np.tile(navi_quat, (self.num_bodies, 1))       # (14, 4)
        o_navi = robot_anchor_pos.astype(np.float32).copy()
        o_navi[2] = 0.0                     # origin z=0 → ref z stays absolute
        body_pos_flat = robot_body_pos.astype(np.float32).copy()     # (14, 3)
        body_pos_flat[:, 2] = 0.0           # per-body error is horizontal only

        for fi, offset in enumerate(self.future_idx):
            t = min(time_step + offset, motion.num_frames - 1)
            future_body_pos = motion.body_pos_w[t]      # (14, 3)
            future_body_quat = motion.body_quat_w[t]    # (14, 4)

            target_pos = _quat_apply(
                navi_inv_expand, future_body_pos - o_navi[None, :])
            target_pos_rel = _quat_apply(
                navi_inv_expand, future_body_pos - body_pos_flat)
            target_rot = _quat_to_tan_norm(
                _quat_mul(navi_inv_expand, future_body_quat))
            rel_rot = _quat_mul(future_body_quat, _quat_conjugate(robot_body_quat))
            target_rot_rel = _quat_to_tan_norm(
                _quat_mul(_quat_mul(navi_inv_expand, rel_rot), navi_expand))

            idx = 0
            task_obs[fi, idx:idx + 42] = target_pos.reshape(-1)
            idx += 42
            task_obs[fi, idx:idx + 42] = target_pos_rel.reshape(-1)
            idx += 42
            task_obs[fi, idx:idx + 84] = target_rot.reshape(-1)
            idx += 84
            task_obs[fi, idx:idx + 84] = target_rot_rel.reshape(-1)
            idx += 84
            task_obs[fi, idx] = float(offset)   # timestamp 必须如实填 offset

        return task_obs
