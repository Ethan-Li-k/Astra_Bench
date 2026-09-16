"""Synchronized command -> model inputs -> targets -> PD -> motion trace.

No interventions in this recorder. The optional reference servo is recorded as
a separate input stage. No VLM, task commands, gripper commands or object reads.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import mujoco
import numpy as np
from rsi.live import LiveSim
from rsi.scalebfm import MODEL_SHA256


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--servo', action='store_true')
    p.add_argument('--freeze', choices=('none','task','wrist_orientation_error','wrists'), default='none')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source_dir = args.output / 'sources'
    source_dir.mkdir()
    sources = [Path(__file__)] + [Path(__file__).parents[1]/'rsi'/n for n in ('live.py', 'scalebfm.py', 'reference_servo.py')]
    for source in sources:
        (source_dir/source.name).write_bytes(source.read_bytes())
    (args.output/'manifest.json').write_text(json.dumps({
        'command': 'HOLD_INITIAL_WORLD_REFERENCE; no movement or finger requests',
        'reference_servo': args.servo, 'table_offset_x_m': .1,
        'diagnostic_freeze': args.freeze, 'freeze_window_s': [10,12],
        'physics_dt_s': .004, 'control_dt_s': .02, 'model_sha256': MODEL_SHA256,
        'sources': {str(s): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
        'llm_calls': 0}, indent=2))
    s = LiveSim(reference_servo=args.servo, table_offset_x=.1)
    a = s.adapter
    trace = {key: [] for key in ('sim_s', 'nominal_pos', 'tracker_pos', 'tracker_quat',
        'body_pos', 'body_quat', 'policy', 'policy_task', 'policy_task_computed', 'action_history_in',
        'raw_action', 'q_target', 'q_after', 'body_after', 'substep_s',
        'q_before_pd', 'dq_before_pd', 'pd_unclipped', 'torque_sent', 'q_after_pd')}
    original_infer, original_policy, original_step = a.infer, a._run_policy, mujoco.mj_step
    target = None
    frozen_task = None

    def run_policy(task):
        nonlocal frozen_task
        trace['policy_task_computed'].append(task.copy())
        if args.freeze != 'none' and 10 <= s.data.time < 12:
            if frozen_task is None:
                frozen_task = task.copy()
            task = task.copy()
            if args.freeze == 'task':
                task[:] = frozen_task
            else:
                for wrist in s.wrists:
                    columns = np.arange(168+6*wrist,174+6*wrist)
                    if args.freeze == 'wrists':
                        columns = np.r_[np.arange(3*wrist,3*wrist+3), np.arange(42+3*wrist,45+3*wrist),
                                        np.arange(84+6*wrist,90+6*wrist), columns]
                    task[:,columns] = frozen_task[:,columns]
        trace['policy'].append(a.policy_history[0].copy())
        trace['policy_task'].append(task.copy())
        trace['action_history_in'].append(a.action_history[0].copy())
        out = original_policy(task)
        trace['raw_action'].append(out.copy())
        return out

    def infer(data, motion, frame):
        nonlocal target
        trace['sim_s'].append(float(data.time))
        nominal = np.tile(s.pos0, (a.num_future, 1, 1))
        nominal[:, s.wrist] = s.reference_at(data.time+np.asarray(a.future_idx)*.02)
        trace['nominal_pos'].append(nominal)
        trace['tracker_pos'].append(motion.body_pos_w[list(a.future_idx)].copy())
        trace['tracker_quat'].append(motion.body_quat_w[list(a.future_idx)].copy())
        trace['body_pos'].append(data.xpos[a.body_ids].copy())
        trace['body_quat'].append(data.xquat[a.body_ids].copy())
        target = original_infer(data, motion, frame)
        trace['q_target'].append(target.copy())
        return target

    def step(model, data):
        q = data.qpos[a._policy_qpos_adr].copy()
        dq = data.qvel[a._policy_dof_adr].copy()
        trace['substep_s'].append(float(data.time))
        trace['q_before_pd'].append(q)
        trace['dq_before_pd'].append(dq)
        trace['pd_unclipped'].append(s.kp*(target-q)-s.kd*dq)
        trace['torque_sent'].append(data.ctrl[s.act].copy())
        original_step(model, data)
        trace['q_after_pd'].append(data.qpos[a._policy_qpos_adr].copy())

    a.infer, a._run_policy, mujoco.mj_step = infer, run_policy, step
    start = time.monotonic()
    error = None
    try:
        for _ in range(1000):
            s.tick()
            trace['q_after'].append(s.data.qpos[a._policy_qpos_adr].copy())
            trace['body_after'].append(s.data.xpos[a.body_ids].copy())
            if s.reason:
                break
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        a.infer, a._run_policy, mujoco.mj_step = original_infer, original_policy, original_step
        np.savez(args.output/'chain.npz', **{k: np.asarray(v) for k,v in trace.items()},
                 mode=a.mode, mode_mapping=a.mode_mapping, joint_names=a.metadata['joint_names'],
                 body_names=a.metadata['selected_body_names'], scale=a._action_scale_p,
                 default=a._default_qpos_p, kp=s.kp, kd=s.kd, limits=s.limits)
        (args.output/'summary.json').write_text(json.dumps({'reason': 'recorder_failure' if error else s.reason,
            'error': error,
            'sim_s': float(s.data.time), 'wall_s': time.monotonic()-start, 'llm_calls': 0}, indent=2))
    print('Recorded', args.output, 'stop:', s.reason, flush=True)


if __name__ == '__main__':
    main()
