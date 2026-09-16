"""Task-space force compensation for hand tracking.

Extracted into its own module so it can be imported without pulling in the
full play_track.py dependency tree (e.g. pygame).
"""
from __future__ import annotations

from typing import Optional

import mujoco
import numpy as np


class HandForceCompensation:
    """Compute extra joint torques to pull hands toward reference positions.

    Uses Jacobian transpose to map Cartesian force errors into joint torques.
    Output torques are nonzero only on arm DOFs.
    """

    ARM_JOINTS_L = [
        "left_shoulder_pitch_joint",
        "left_shoulder_roll_joint",
        "left_shoulder_yaw_joint",
        "left_elbow_joint",
        "left_wrist_roll_joint",
        "left_wrist_pitch_joint",
        "left_wrist_yaw_joint",
    ]
    ARM_JOINTS_R = [
        "right_shoulder_pitch_joint",
        "right_shoulder_roll_joint",
        "right_shoulder_yaw_joint",
        "right_elbow_joint",
        "right_wrist_roll_joint",
        "right_wrist_pitch_joint",
        "right_wrist_yaw_joint",
    ]

    def __init__(self, mj_model: "mujoco.MjModel", kp_task: float = 5500.0,
                 kd_task: float = 40.0, max_force: float = 100.0,
                 use_gravity_comp: bool = False,
                 use_relative_vel: bool = False):
        self._kp = kp_task
        self._kd = kd_task
        self._max_force = max_force
        self._use_gravity_comp = use_gravity_comp
        self._use_relative_vel = use_relative_vel

        self._left_body_id = mj_model.body("left_wrist_yaw_link").id
        self._right_body_id = mj_model.body("right_wrist_yaw_link").id

        self._nv = mj_model.nv
        self._nj = mj_model.nv - 6

        def _arm_dof_idx(joint_names):
            idx = []
            for n in joint_names:
                jid = mj_model.joint(n).id
                idx.append(int(mj_model.jnt_dofadr[jid]) - 6)
            return np.array(idx, dtype=np.int64)

        self._left_arm_idx = _arm_dof_idx(self.ARM_JOINTS_L)
        self._right_arm_idx = _arm_dof_idx(self.ARM_JOINTS_R)
        self._arm_idx = np.concatenate([self._left_arm_idx, self._right_arm_idx])

    def compute(self, mj_model: "mujoco.MjModel", mj_data: "mujoco.MjData",
                ref_left_pos: np.ndarray, ref_right_pos: np.ndarray,
                ref_left_vel: Optional[np.ndarray] = None,
                ref_right_vel: Optional[np.ndarray] = None) -> np.ndarray:
        extra_torques = np.zeros(self._nj, dtype=np.float64)

        for body_id, ref_pos, ref_vel, arm_idx in [
            (self._left_body_id, ref_left_pos, ref_left_vel, self._left_arm_idx),
            (self._right_body_id, ref_right_pos, ref_right_vel, self._right_arm_idx),
        ]:
            cur_pos = mj_data.xpos[body_id]
            pos_err = ref_pos - cur_pos

            jacp = np.zeros((3, self._nv), dtype=np.float64)
            mujoco.mj_jacBody(mj_model, mj_data, jacp, None, body_id)
            cart_vel = jacp @ mj_data.qvel

            if self._use_relative_vel and ref_vel is not None:
                vel_err = cart_vel - np.asarray(ref_vel, dtype=np.float64)
            else:
                vel_err = cart_vel

            force = self._kp * pos_err - self._kd * vel_err
            force_norm = np.linalg.norm(force)
            if force_norm > self._max_force:
                force = force * (self._max_force / force_norm)

            jac_arm = jacp[:, 6 + arm_idx]
            extra_torques[arm_idx] += jac_arm.T @ force

        if self._use_gravity_comp:
            extra_torques[self._arm_idx] += mj_data.qfrc_bias[6 + self._arm_idx]

        return extra_torques.astype(np.float32)
