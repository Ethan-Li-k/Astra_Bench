"""Bounded simulation-only standing/one-wrist diagnostic, not a visual actor.

No object, external hand wrench, welded root, or writes to live robot drivers.
Robot simulator poses are used for this controller diagnostic only.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
from rsi.scalebfm import Model38000, SCENE, MODEL_SHA256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wrist-dx', type=float, default=0.)
    parser.add_argument('--scene', type=Path, default=SCENE)
    parser.add_argument('--seconds', type=int, default=5, choices=range(5, 31))
    args = parser.parse_args()
    if not np.isfinite(args.wrist_dx) or abs(args.wrist_dx) > .02:
        parser.error('This diagnostic limits wrist displacement to 2 cm')
    # Exclusive creation preserves previous attempts, including failures.
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'manifest.json').write_text(json.dumps({'scene': str(args.scene),
        'scene_sha256': hashlib.sha256(args.scene.read_bytes()).hexdigest(),
        'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_sha256': MODEL_SHA256, 'seconds': args.seconds, 'llm_calls': 0}, indent=2))
    model = mujoco.MjModel.from_xml_path(str(args.scene))
    model.opt.timestep = .004
    data = mujoco.MjData(model)
    adapter = Model38000(model)
    data.qpos[2] = .755  # Existing locomanip default standing reset height.
    data.qpos[adapter._policy_qpos_adr] = adapter._default_qpos_p
    mujoco.mj_forward(model, data)
    adapter.warm_start(data)
    names = adapter.metadata['joint_names']
    actuators = np.array([model.actuator(n).id for n in names])
    joints = np.array([model.joint(n).id for n in names])
    limits = model.jnt_actfrcrange[joints]
    if not np.all(model.jnt_actfrclimited[joints]):
        raise ValueError('Expected explicit torque limits for all policy joints')
    kp = adapter.kp[adapter.policy_jnt_idx]
    kd = adapter.kd[adapter.policy_jnt_idx]
    fingers = [model.joint(i).name for i in range(model.njnt)
               if model.joint(i).name and '_hand_' in model.joint(i).name]
    finger_q = np.array([model.joint(n).qposadr[0] for n in fingers], dtype=int)
    finger_v = np.array([model.joint(n).dofadr[0] for n in fingers], dtype=int)
    finger_act = np.array([model.actuator(n).id for n in fingers], dtype=int)
    finger_limits = model.jnt_actfrcrange[[model.joint(n).id for n in fingers]]
    pos0 = data.xpos[adapter.body_ids].copy()
    quat0 = data.xquat[adapter.body_ids].copy()
    count = args.seconds * 50 + 50
    pos = np.tile(pos0, (count, 1, 1)).astype(np.float32)
    quat = np.tile(quat0, (count, 1, 1)).astype(np.float32)
    wrist = adapter.metadata['selected_body_names'].index('right_wrist_yaw_link')
    phase = np.clip((np.arange(count) * .02 - 1.) / 2., 0., 1.)
    pos[:, wrist, 0] += args.wrist_dx * (3 * phase**2 - 2 * phase**3)
    reference = SimpleNamespace(num_frames=count, body_pos_w=pos, body_quat_w=quat)
    rows, samples = [], []
    reason = None
    start = time.monotonic()
    with (args.output / 'ticks.jsonl').open('x') as log:
        for tick in range(args.seconds * 50):
            target = adapter.infer(data, reference, tick)
            if not np.isfinite(target).all():
                reason = 'nonfinite_policy_output'
                break
            clips = 0
            for _ in range(5):
                torque = kp * (target - data.qpos[adapter._policy_qpos_adr]) - kd * data.qvel[adapter._policy_dof_adr]
                clips += int(np.count_nonzero((torque < limits[:, 0]) | (torque > limits[:, 1])))
                data.ctrl[actuators] = np.clip(torque, limits[:, 0], limits[:, 1])
                ft = -20. * data.qpos[finger_q] - data.qvel[finger_v]
                data.ctrl[finger_act] = np.clip(ft, finger_limits[:, 0], finger_limits[:, 1])
                mujoco.mj_step(model, data)
            mujoco.mj_forward(model, data)
            pelvis = data.xpos[adapter.body_ids[0]]
            tilt = float(np.rad2deg(np.arccos(np.clip(data.xmat[adapter.body_ids[0]].reshape(3, 3)[2, 2], -1, 1))))
            actual_wrist = data.xpos[adapter.body_ids[wrist]]
            row = {'tick': tick, 'sim_s': float(data.time), 'wall_s': time.monotonic() - start,
                   'pelvis_z_m': float(pelvis[2]), 'tilt_deg': tilt,
                   'pelvis_xy_drift_m': float(np.linalg.norm(pelvis[:2] - pos0[0, :2])),
                   'wrist_error_m': float(np.linalg.norm(actual_wrist - pos[tick, wrist])),
                   'wrist_actual_m': actual_wrist.tolist(), 'wrist_reference_m': pos[tick, wrist].tolist(),
                   'torque_clips': clips, 'q_target_rad': target.tolist()}
            rows.append(row)
            samples.append(data.qpos.copy())
            log.write(json.dumps(row) + '\n')
            log.flush()
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                reason = 'nonfinite_state'
            elif pelvis[2] < .55:
                reason = 'diagnostic_height_stop'
            elif tilt > 25.:
                reason = 'diagnostic_tilt_stop'
            if reason:
                break
    np.savez(args.output / 'robot_states.npz', qpos=np.asarray(samples), reference_pos=pos, reference_quat=quat)
    summary = {'status': 'FAIL' if reason else 'PASS_SHORT_PROBE', 'reason': reason,
               'scope': 'controller diagnostic, not grasp or P0 visual evaluation',
               'seconds_requested': args.seconds, 'sim_s': float(data.time), 'wall_s': time.monotonic() - start,
               'wrist_dx_requested_m': args.wrist_dx, 'model_sha256': MODEL_SHA256,
               'physics_dt_s': .004, 'controller_dt_s': .02, 'far_offset': 25,
               'max_tilt_deg': max((r['tilt_deg'] for r in rows), default=None),
               'min_pelvis_z_m': min((r['pelvis_z_m'] for r in rows), default=None),
               'last': rows[-1] if rows else None, 'llm_calls': 0}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)
    return int(reason is not None)


if __name__ == '__main__':
    raise SystemExit(main())
