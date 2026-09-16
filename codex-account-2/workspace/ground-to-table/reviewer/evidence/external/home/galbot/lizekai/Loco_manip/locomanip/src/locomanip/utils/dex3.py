"""Dex3 hand finger PD utilities.

`DEX3_CLOSED_POS` + KP/KD are the canonical finger targets; `setup_dex3_fingers`
builds actuator-id arrays from a MjModel, `finger_ctrl` writes the per-substep
`mj_data.ctrl` block for the fingers using a (left, right) trigger tuple.

Extracted from the original ``locomanip.datagen.bfm_track_to_lerobot`` grab-bag.
"""
from __future__ import annotations

import mujoco
import numpy as np

# 建库时 grip 标量的归一化分母，**冻结**在 teleop-v2.0（gr00t-v20 训的那批）
# 建库时用的值。`play_teleop_track.py` / `motion_clip.py` 算
# `grip = right_index_0 / GRIP_NORM_INDEX0`；改它 = 平移整个数据集的 grip
# 分布、和已训 ckpt 错开。它和下面的手型表**故意解耦**：调手型不该动数据定义。
GRIP_NORM_INDEX0 = 1.5

# 闭合姿态 = 各关节**闭合方向的机械行程端点**（MJCF g1_mjx_track_dex3.xml）。
#
# 2026-09-02 起这张表不再是可调参数：手指目标 = `grip × 本表`，把本表设成行程
# 端点之后，那个 0-1 的 grip 标量就**字面等于闭合百分比** —— 于是「手闭到哪」
# 由 `deploy/infer_common.py` 顶部那三行（GRIP_CLOSE_THR / GRIP_RELEASE_THR /
# GRIP_HALF_VALUE）统一决定，仿真与真机同一个数，不必再两处对表。
# 真机侧的同一套值见 `deploy/onboard/g1_constants.py`（那边是电机序数组）。
#
# thumb_0（CMC 对掌轴）恒为 0：它不参与握拳，非零会让拇指先对掌、扭出平面。
DEX3_CLOSED_POS = {
    "left_hand_index_0_joint": -1.5708,
    "left_hand_index_1_joint": -1.74533,
    "left_hand_middle_0_joint": -1.5708,
    "left_hand_middle_1_joint": -1.74533,
    "left_hand_thumb_0_joint": 0.0,
    "left_hand_thumb_1_joint": 1.0472,
    "left_hand_thumb_2_joint": 1.74533,
    "right_hand_index_0_joint": 1.5708,
    "right_hand_index_1_joint": 1.74533,
    "right_hand_middle_0_joint": 1.5708,
    "right_hand_middle_1_joint": 1.74533,
    "right_hand_thumb_0_joint": 0.0,
    "right_hand_thumb_1_joint": -1.0472,
    "right_hand_thumb_2_joint": -1.74533,
}


# Release-phase OPEN targets — thumb splays OUTWARD (opposite direction of
# grip closed pose) so a cube stuck between the fingers gets actively
# ejected instead of held by residual pinch force + high friction.
DEX3_OPEN_POS = {
    # All joints at natural extended pose (0).  Not splayed — a strong
    # splay (thumb_1 to opposite extreme) plus reduced friction was
    # kicking the cube meters into the air.  The friction drop alone is
    # enough to let the cube fall out under gravity.
    "left_hand_index_0_joint":  0.0,
    "left_hand_index_1_joint":  0.0,
    "left_hand_middle_0_joint": 0.0,
    "left_hand_middle_1_joint": 0.0,
    "left_hand_thumb_0_joint":  0.0,
    "left_hand_thumb_1_joint": -0.5,   # splay to eject cube stuck in grip
    "left_hand_thumb_2_joint":  0.0,
    "right_hand_index_0_joint":  0.0,
    "right_hand_index_1_joint":  0.0,
    "right_hand_middle_0_joint": 0.0,
    "right_hand_middle_1_joint": 0.0,
    "right_hand_thumb_0_joint":  0.0,
    "right_hand_thumb_1_joint":  0.5,   # splay to eject cube stuck in grip
    "right_hand_thumb_2_joint":  0.0,
}
DEX3_FINGER_KP = 20.0
DEX3_FINGER_KD = 1.0


def setup_dex3_fingers(mj_model: mujoco.MjModel, policy_jnames: list[str]) -> dict:
    all_jnames = [
        mujoco.mj_id2name(mj_model, mujoco.mjtObj.mjOBJ_JOINT, i)
        for i in range(1, mj_model.njnt)
    ]
    finger_jnames = [n for n in all_jnames if n not in policy_jnames and "_hand_" in n]
    if not finger_jnames:
        return dict(finger_jnames=[], finger_act=np.array([], dtype=np.int64),
                    finger_qadr=np.array([], dtype=np.int64),
                    finger_vadr=np.array([], dtype=np.int64),
                    finger_frc=np.array([], dtype=np.float32),
                    finger_is_left=np.array([], dtype=bool),
                    finger_closed=np.array([], dtype=np.float32))

    fj_ids = [mj_model.joint(n).id for n in finger_jnames]
    return dict(
        finger_jnames=finger_jnames,
        finger_act=np.array([mj_model.actuator(n).id for n in finger_jnames], dtype=np.int64),
        finger_qadr=np.array([mj_model.jnt_qposadr[j] for j in fj_ids], dtype=np.int64),
        finger_vadr=np.array([mj_model.jnt_dofadr[j] for j in fj_ids], dtype=np.int64),
        finger_frc=np.array([mj_model.jnt_actfrcrange[j, 1] for j in fj_ids], dtype=np.float32),
        finger_is_left=np.array([n.startswith("left_") for n in finger_jnames], dtype=bool),
        finger_closed=np.array([DEX3_CLOSED_POS.get(n, 0.0) for n in finger_jnames], dtype=np.float32),
        finger_open_splay=np.array([DEX3_OPEN_POS.get(n, 0.0) for n in finger_jnames], dtype=np.float32),
    )


def finger_ctrl_targets(mj_data: mujoco.MjData, fingers: dict,
                        targets: np.ndarray,
                        kp: float = DEX3_FINGER_KP,
                        kd: float = DEX3_FINGER_KD) -> None:
    """Per-substep dex3 finger PD with explicit per-joint targets.

    ``targets`` is (len(finger_jnames),) in ``fingers`` scan order — the
    caller owns any ordering conversion (e.g. sonic's official hand order).
    Same actuator clip as `finger_ctrl`; gains overridable because the SONIC
    stack drives hands with a much softer PD (kp=2.0, kd=0.05) than the
    grip-scalar path."""
    if fingers["finger_act"].size == 0:
        return
    tq = (
        kp * (targets - mj_data.qpos[fingers["finger_qadr"]])
        - kd * mj_data.qvel[fingers["finger_vadr"]]
    )
    mj_data.ctrl[fingers["finger_act"]] = np.clip(tq, -fingers["finger_frc"], fingers["finger_frc"])


def finger_ctrl(mj_data: mujoco.MjData, fingers: dict, finger_grip: np.ndarray) -> None:
    """Per-substep dex3 finger PD.  ``finger_grip`` is (left_trigger,
    right_trigger) in [0, 1]:

        target = grip * DEX3_CLOSED_POS + (1 - grip) * DEX3_OPEN_POS

    OPEN pose has thumb splayed OUTWARD (see DEX3_OPEN_POS) so that on
    grip → 0 fingers actively eject any cube pinched between them,
    instead of only relaxing to natural extension where residual friction
    can hold the cube.  Set finger_open_splay to zeros to keep pre-v2
    behaviour."""
    if fingers["finger_act"].size == 0:
        return
    g = np.where(fingers["finger_is_left"], finger_grip[0], finger_grip[1])
    # Splay only kicks in when grip is well past neutral (< 0.5).  For grip
    # >= 0.5 keep the plain grip*closed formula so partial-close motion
    # phases still grasp cleanly.  Below 0.5, blend from closed toward
    # DEX3_OPEN_POS (thumb splayed OUT) proportionally to (0.5 - g)/0.5.
    splay = fingers.get("finger_open_splay",
                        np.zeros_like(fingers["finger_closed"]))
    release_w = np.clip((0.5 - g) / 0.5, 0.0, 1.0)   # 0 above 0.5, 1 at 0
    tgt = g * fingers["finger_closed"] + release_w * splay
    tq = (
        DEX3_FINGER_KP * (tgt - mj_data.qpos[fingers["finger_qadr"]])
        - DEX3_FINGER_KD * mj_data.qvel[fingers["finger_vadr"]]
    )
    mj_data.ctrl[fingers["finger_act"]] = np.clip(tq, -fingers["finger_frc"], fingers["finger_frc"])
