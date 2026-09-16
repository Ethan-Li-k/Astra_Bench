"""Synchronized command -> model inputs -> targets -> PD -> motion trace.

Default recording is passive. Explicit flags enable bounded diagnostic
interventions and one small movement. No VLM, gripper commands or object reads.
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
    movement = p.add_mutually_exclusive_group()
    movement.add_argument('--move', action='store_true')
    movement.add_argument('--reference-step', choices=('x','y','z'))
    p.add_argument('--reference-adapter', action='store_true')
    p.add_argument('--freeze', choices=('none','task','wrist_orientation_error','wrists'), default='none')
    p.add_argument('--quantizer', choices=('onnx','torch_raw','hysteresis','continuous'), default='onnx')
    p.add_argument('--inertia-damping', action='store_true')
    args = p.parse_args()
    if args.reference_adapter and (not args.move or args.quantizer != 'onnx' or args.servo or args.freeze != 'none' or args.inertia_damping):
        p.error('Reference adapter diagnostic requires --move and the unchanged ONNX controller')
    args.output.mkdir(parents=True, exist_ok=False)
    source_dir = args.output / 'sources'
    source_dir.mkdir()
    sources = [Path(__file__)] + [Path(__file__).parents[1]/'rsi'/n for n in ('live.py', 'scalebfm.py', 'reference_servo.py', 'diagnostic_latent.py')]
    for source in sources:
        (source_dir/source.name).write_bytes(source.read_bytes())
    (args.output/'manifest.json').write_text(json.dumps({
        'command': f'At 10s: nominal right wrist reference +2cm world-{args.reference_step.upper()}, duration 2s' if args.reference_step else ('At 10s: observed right wrist +2cm world-X, duration 2s' if args.move else 'HOLD_INITIAL_WORLD_REFERENCE; no movement or finger requests'),
        'diagnostic_reference_step_axis': args.reference_step,
        'reference_step_contract': 'At 10s shift nominal reference +2cm in one world axis over 2s; not an observed-anchor move_wrist request' if args.reference_step else None,
        'reference_servo': args.servo, 'table_offset_x_m': .1,
        'diagnostic_freeze': args.freeze, 'freeze_window_s': [10,12],
        'quantizer': args.quantizer, 'hysteresis_margin_bin': .1 if args.quantizer=='hysteresis' else 0.,
        'inertia_damping': args.inertia_damping,
        'diagnostic_reference_adapter': args.reference_adapter,
        'physics_dt_s': .004, 'control_dt_s': .02, 'model_sha256': MODEL_SHA256,
        'sources': {str(s): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
        'llm_calls': 0}, indent=2))
    s = LiveSim(reference_servo=args.servo, table_offset_x=.1)
    a = s.adapter
    if args.inertia_damping:
        baseline = mujoco.MjModel.from_xml_path('artifacts/R004/reference_scene.xml')
        baseline_data = mujoco.MjData(baseline)
        names = a.metadata['joint_names']
        bq = np.array([baseline.joint(n).qposadr[0] for n in names])
        bv = np.array([baseline.joint(n).dofadr[0] for n in names])
        baseline_data.qpos[bq] = s.data.qpos[a._policy_qpos_adr]
        br = baseline.jnt_qposadr[baseline.body_jntadr[baseline.body('pelvis').id]]
        cr = s.model.jnt_qposadr[s.model.body_jntadr[s.model.body('pelvis').id]]
        baseline_data.qpos[br:br+7] = s.data.qpos[cr:cr+7]
        mujoco.mj_forward(baseline,baseline_data)
        current_m = np.zeros((s.model.nv,s.model.nv))
        baseline_m = np.zeros((baseline.nv,baseline.nv))
        mujoco.mj_fullM(s.model,current_m,s.data.qM)
        mujoco.mj_fullM(baseline,baseline_m,baseline_data.qM)
        ratio = np.sqrt(np.diag(current_m)[a._policy_dof_adr]/np.diag(baseline_m)[bv])
        arm = np.array([any(x in n for x in ('shoulder','elbow','wrist')) for n in names])
        original_kd = s.kd.copy()
        s.kd[arm] *= ratio[arm]
        (args.output/'damping.json').write_text(json.dumps({'joint_names':names,
            'original_kd':original_kd.tolist(),'diagnostic_kd':s.kd.tolist(),
            'sqrt_diagonal_inertia_ratio':ratio.tolist(),
            'limit':'Diagonal-inertia heuristic; not full coupled pole matching or hardware calibration.'},indent=2))
    trace = {key: [] for key in ('sim_s', 'nominal_pos', 'tracker_pos', 'tracker_quat',
        'body_pos', 'body_quat', 'policy', 'policy_task', 'policy_task_computed', 'action_history_in',
        'raw_action', 'q_target', 'q_after', 'body_after', 'substep_s', 'fsq_raw', 'fsq_used',
        'q_before_pd', 'dq_before_pd', 'pd_unclipped', 'torque_sent', 'q_after_pd')}
    original_infer, original_policy, original_step = a.infer, a._run_policy, mujoco.mj_step
    backend = None
    if args.quantizer != 'onnx':
        from rsi.diagnostic_latent import DiagnosticLatentPolicy
        backend = DiagnosticLatentPolicy(a, args.quantizer)
        def latent_policy(task):
            out = backend(task)
            trace['fsq_raw'].append(backend.raw_code.copy())
            trace['fsq_used'].append(backend.used_code.copy())
            return out
        original_policy = latent_policy
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
        for tick in range(1000):
            if args.reference_step and tick == 500:
                s.start = s.reference_at(s.data.time).copy()
                s.goal = s.start.copy()
                s.goal['xyz'.index(args.reference_step)] += .02
                s.t0, s.duration = float(s.data.time), 2.
            if args.move and tick == 500:
                obs = s.observe()
                s.move_wrist(obs['observation_id'], 'diagnostic_x_2cm', [.02, 0, 0], duration=2.)
                if args.reference_adapter:
                    calibration_path = Path('artifacts/R008/reference_step_analysis.json')
                    calibration = json.loads(calibration_path.read_text())['runs']
                    response = np.column_stack([calibration[f'reference-{axis}-onnx']['actual_delta_mm'] for axis in 'xyz'])/20.
                    reference_delta = np.linalg.solve(response, s.goal-np.asarray(obs['wrist_world_m']))
                    if np.linalg.norm(reference_delta) > .03:
                        raise ValueError('Diagnostic reference increment exceeds 3cm; no extrapolation escalation')
                    origin = s.start.copy()
                    def reference_at(when):
                        u = np.clip((np.asarray(when)-s.t0)/s.duration, 0., 1.)
                        return origin + np.asarray(3*u*u-2*u*u*u)[...,None]*reference_delta
                    s.reference_at = reference_at
                    (args.output/'reference_adapter.json').write_text(json.dumps({
                        'scope':'Single-pose offline response inverse; not a deployable general controller',
                        'calibration':str(calibration_path),
                        'calibration_sha256':hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
                        'response_matrix':response.tolist(), 'condition_number':float(np.linalg.cond(response)),
                        'reference_increment_m':reference_delta.tolist(), 'tracker_reference_goal_m':(origin+reference_delta).tolist(),
                        'unchanged_user_goal_m':s.goal.tolist()},indent=2))
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
            'error': error, 'motion': s.status(),
            'diagnostic_raw_onnx_parity_max_error': backend.parity_error if backend else None,
            'sim_s': float(s.data.time), 'wall_s': time.monotonic()-start, 'llm_calls': 0}, indent=2))
    print('Recorded', args.output, 'stop:', s.reason, flush=True)


if __name__ == '__main__':
    main()
