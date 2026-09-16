"""Frozen-state reference sensitivity; no target execution or actor evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np

from rsi.simple_environment import create_closed_door_backend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    b = create_closed_door_backend(seed=0, pd_profile='checkpoint')
    try:
        a = b.adapter
        history, actions = a.policy_history.copy(), a.action_history.copy()
        measured_pos = b.data.xpos[a.body_ids].copy()
        measured_quat = b.data.xquat[a.body_ids].copy()
        foot = a.metadata['selected_body_names'].index('left_ankle_roll_link')
        feet = [a.metadata['selected_body_names'].index(n) for n in
                ('left_ankle_roll_link', 'right_ankle_roll_link')]
        wrists = [a.metadata['selected_body_names'].index(n) for n in
                  ('left_wrist_yaw_link', 'right_wrist_yaw_link')]
        fk = mujoco.MjData(b.model)
        fk.qpos[:] = b.data.qpos
        baseline_fk = baseline_target = None
        rows = []
        cases = [('hold', 0., 0., 0., 0.)]
        # Abrupt and ramped candidates distinguish absolute displacement and
        # future velocity sensitivity. Larger inputs are diagnostic only.
        cases += [(f'z{z}-x{x}-ramp{ramp}', z, x, ramp, 0.)
                  for z in (.06, .12, .20, .30)
                  for x in (0., .15) for ramp in (0., .5)]
        cases += [(f'coordinated-z{z}', z, .15, .5, .15)
                  for z in (.06, .12, .20)]
        sim_time = float(b.data.time)
        for label, z, x, ramp, wrist_forward in cases:
            pos = np.tile(measured_pos, (34, 1, 1)).astype(np.float32)
            quat = np.tile(measured_quat, (34, 1, 1)).astype(np.float32)
            weight = np.clip(np.arange(34)*.02/ramp, 0., 1.) if ramp else np.ones(34)
            pos[:, foot] += weight[:, None]*[x, 0., z]
            for wrist in wrists:
                pos[:, wrist, 0] += weight*wrist_forward
            a.policy_history[:] = history
            a.action_history[:] = actions
            target = a.infer(b.data, SimpleNamespace(num_frames=34, body_pos_w=pos,
                                                     body_quat_w=quat), 0)
            fk.qpos[a._policy_qpos_adr] = target
            mujoco.mj_forward(b.model, fk)
            foot_pos = fk.xpos[a.body_ids[feet]].copy()
            if baseline_fk is None:
                baseline_fk, baseline_target = foot_pos.copy(), target.copy()
            rows.append({'case': label, 'foot_delta_reference_m': [x, 0., z],
                         'ramp_s': ramp, 'wrist_forward_m': wrist_forward,
                         'joint_target29_rad': target.tolist(),
                         'joint_target29_difference_from_hold_rad': (target-baseline_target).tolist(),
                         'ankle_fk_delta_from_hold_m': (foot_pos-baseline_fk).tolist(),
                         'ankle_fk_delta_from_measured_m': (foot_pos-measured_pos[feet]).tolist(),
                         'left_leg_change_l2_rad': float(np.linalg.norm((target-baseline_target)[:6]))})
        assert float(b.data.time) == sim_time, 'Frozen-state audit advanced physics'
        result = {'gpt_calls': 0, 'executed_targets': 0, 'task_success_credit': False,
                  'actor_access': False, 'hypothesis': 'Small sparse references may be too weak to elicit swing commands; sweep displacement and future velocity at identical state/history.',
                  'limitations': 'Fixed-base FK only; not dynamic stability, contact clearance, or successful walking. Larger inputs are outside current actor per-action limits.',
                  'initial_state_sha256': hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest(),
                  'joint_names': a.metadata['joint_names'], 'mode': a.mode.tolist(),
                  'rows': rows}
        (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        for row in rows:
            print(json.dumps({k: row[k] for k in ('case', 'ankle_fk_delta_from_hold_m',
                                                 'left_leg_change_l2_rad')}), flush=True)
    finally:
        b.close()


if __name__ == '__main__':
    main()
