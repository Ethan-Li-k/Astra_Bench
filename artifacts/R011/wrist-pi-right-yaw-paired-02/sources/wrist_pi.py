"""双腕 6 维（位置 + 姿态）PI → 臂关节力矩前馈（部署链路，sim 与真机同一份）。

量到的部署偏置（2026-09-03，teleop replay dump 两集）：右腕整集稳定地比 ref
**前 3 cm / 低 2 cm**，45 mm 平均误差里 37 mm 是这个恒定偏置；换到关节空间
是肩 pitch +6°、肩 roll −4°、肘 −5° 的稳定偏移，折算力矩只有 1-2 Nm/关节
（kp≈14）——正是积分项该消掉的东西。

为什么不用"腕部虚拟力经 Jᵀ"（已退役的 hand_comp）：误差有相当一部分落在手
臂的硬轴上（肘近伸直，该轴 PD 刚度 ≈1.7 kN/m，其余轴 ≈110 N/m），Jᵀ 在硬轴
上把再大的力也映成很小的关节力矩，按此消偏名义上需要 ≈140 N。这里改用阻尼
最小二乘 J⁺ 把误差映成"要修正它各关节该动多少"，以 PD 目标平移的形式下发：
τ = kp·Δq。环路时间常数 = 1/ki，比手臂 ~1 Hz 的 PD 动力学慢一个量级，也就
避开了旧方案（任务空间刚度是 PD 的 15-30 倍）在真机上的抖动。

积分状态放在**任务空间**（每腕一个 6 维向量 e_int = [位置; 旋转向量]，位置 /
姿态分别限幅），每拍用当前 6×7 Jacobian（jacp; jacr，姿态行乘长度权重 w_rot
统一量纲）映射 e_int + kp·e。第一版把状态放在关节空间并逐关节截断，在
tools/deploy/wrist_pi_bench.py 的挥舞工况里 1/3 seed 整机失衡：肘积分顶死后
其余关节继续沿过期/掰歪的方向积分，BFM 看到一个方向不对的外力矩。
只做位置（w_rot=0）时姿态误差反而变差（为了位置改手臂构型不管手的朝向），
所以姿态必须一起进来。

实测（腕 |e| 均值，位置 mm / 姿态 deg）：
- run_sim.sh vla --headless（gr00t-v20，同一集 ×2）：右 47 → 23、左 33 → 19；
  姿态 5.5° → 3.2° / 5.0° → 2.8°；偏置全部归零，脚误差不变，无纹波。
- wrist_pi_bench（站立、双臂在整个可达空间随机路点 min-jerk 挥舞，3 seeds × 40 s）：
  右 114 → 54、左 91 → 38；姿态 17.6° → 13.2° / 13.1° → 8.1°；3/3 无迈步
  （off 组反而有 1 集自己迈步）。BFM 对举过头顶/背到身后这类姿态欠伸 7-9 cm，
  e_max / tau_frac 在此工况会卡住（放宽到 15 cm / 0.4 再降 ~15%），部署工况
  偏置只有 3 cm，默认值不动。
ki 2.0 距振铃边（纯 PD 最坏情况 ki≈4）有 2 倍裕度。真机若见低幅 hunting
（积分 + 静摩擦）先把 ki 降到 1.0。
"""
from __future__ import annotations

import mujoco
import numpy as np


def rotvec_err(q_ref_wxyz, q_act_wxyz) -> np.ndarray:
    """log(R_ref · R_actᵀ) 的旋转向量（世界系）：把 act 转到 ref 的最短旋转，
    与 mj_jacBody 的角速度 Jacobian 同一个系。"""
    q, qc, w = np.empty(4), np.empty(4), np.empty(3)
    mujoco.mju_negQuat(qc, np.asarray(q_act_wxyz, dtype=np.float64))
    mujoco.mju_mulQuat(q, np.asarray(q_ref_wxyz, dtype=np.float64), qc)
    if q[0] < 0:
        q = -q
    mujoco.mju_quat2Vel(w, q, 1.0)
    return w


class WristPI:
    ARM = ("shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow",
           "wrist_roll", "wrist_pitch", "wrist_yaw")

    def __init__(self, mj_model, joint_names29, kp29, torque_limit29,
                 ki: float = 2.0, kp: float = 0.3, e_max: float = 0.08,
                 r_max: float = 0.35, w_rot: float = 0.15,
                 tau_frac: float = 0.3, lam: float = 0.05):
        """6 维（位置 + 姿态）任务空间 PI。
        ki: 积分速率 (1/s)，准静态下腕部误差按 exp(-ki·t) 衰减；
        kp: 比例项（0.3 ≈ 任务空间刚度 +30%）；
        e_max / r_max: 位置 (m) / 姿态 (rad) 积分量上限 —— 积分器最多把 PD 目标
        平移 / 旋转这么多（抗饱和，分别按范数缩回）；
        w_rot: 姿态行在 DLS 里的长度权重 (m/rad)，统一量纲；0 = 只管位置；
        tau_frac: 每关节力矩硬限幅 = tau_frac × torque_limit（奇异姿态兜底）；
        lam: DLS 阻尼 (m)，肘伸直奇异附近压住 J⁺ 的放大。"""
        self.m = mj_model
        self.d = mujoco.MjData(mj_model)
        self.ki, self.kp, self.lam = float(ki), float(kp), float(lam)
        self.e_max, self.r_max = float(e_max), float(r_max)
        self.W = np.array([1.0, 1.0, 1.0, w_rot, w_rot, w_rot])
        names = list(joint_names29)
        kp29 = np.asarray(kp29, dtype=np.float64)
        tl29 = np.asarray(torque_limit29, dtype=np.float64)
        self.qadr29 = np.array(
            [mj_model.jnt_qposadr[mj_model.joint(n).id] for n in names])
        self.arms = []
        for side in ("left", "right"):
            jn = [f"{side}_{j}_joint" for j in self.ARM]
            i29 = np.array([names.index(n) for n in jn])
            dof = np.array(
                [mj_model.jnt_dofadr[mj_model.joint(n).id] for n in jn])
            self.arms.append((mj_model.body(f"{side}_wrist_yaw_link").id,
                              dof, i29, kp29[i29], tau_frac * tl29[i29]))
        self.e_int = np.zeros((2, 6))
        self._jacp = np.zeros((3, mj_model.nv))
        self._jacr = np.zeros((3, mj_model.nv))

    def reset(self) -> None:
        self.e_int[:] = 0.0

    def __call__(self, root_quat_wxyz, q29, ref_pos, ref_quat, act_pos, act_quat,
                 dt: float) -> np.ndarray:
        """ref_* / act_*: (2,3) 位置与 (2,4) wxyz 四元数，左/右腕，任一与 root_quat
        同朝向的系。返回 canonical 29 序的力矩前馈（只有 14 个臂关节非零）。

        积分状态放在任务空间（每腕一个 6 维向量），每拍用**当前** Jacobian 映射：
        手臂一动，旧的关节空间积分量对应的笛卡尔修正就变了，而且逐关节截断会
        把 J⁺ 方向掰歪（2026-09-03 挥舞 bench 里 1/3 seed 因此失衡）。"""
        d = self.d
        d.qpos[3:7] = root_quat_wxyz
        d.qpos[self.qadr29] = q29
        mujoco.mj_kinematics(self.m, d)
        mujoco.mj_comPos(self.m, d)
        tau = np.zeros(len(self.qadr29))
        for k, (bid, dof, i29, kp_j, tau_max) in enumerate(self.arms):
            e = np.concatenate([ref_pos[k] - act_pos[k],
                                rotvec_err(ref_quat[k], act_quat[k])])
            e_int = self.e_int[k] + self.ki * dt * e
            e_int[:3] /= max(1.0, np.linalg.norm(e_int[:3]) / self.e_max)
            e_int[3:] /= max(1.0, np.linalg.norm(e_int[3:]) / self.r_max)
            self.e_int[k] = e_int
            mujoco.mj_jacBody(self.m, d, self._jacp, self._jacr, bid)
            J = self.W[:, None] * np.vstack([self._jacp[:, dof], self._jacr[:, dof]])
            u = self.W * (e_int + self.kp * e)
            dq = J.T @ np.linalg.solve(J @ J.T + self.lam ** 2 * np.eye(6), u)
            tau[i29] = np.clip(kp_j * dq, -tau_max, tau_max)
        return tau
