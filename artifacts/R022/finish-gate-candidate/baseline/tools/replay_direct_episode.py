"""Replay recorded Direct commands without any GPT calls; host-only diagnostics."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np

from rsi.episode_video import EpisodeVideo
from rsi.evaluator import LiftEvaluator, GraspLiftEvaluator
from rsi.tool_host import LocoManipToolHost
from tools.codex_direct_sim import EvaluationHost, create_settled_backend


class AuditVideo(EpisodeVideo):
    def __init__(self, backend, output, *, label=None):
        self.diagnostics = []
        self.task_inputs = []
        original_run = backend.adapter._run_policy
        def record_policy_input(task):
            self.task_inputs.append(task.copy())
            return original_run(task)
        backend.adapter._run_policy = record_policy_input
        self.output = Path(output)
        super().__init__(backend, output, label=label or
                         'DIAGNOSTIC REPLAY | no new model call | not an evaluation trial')

    def record_tick(self, native_outcome):
        super().record_tick(native_outcome)
        b = self.backend
        contacts = []
        for i in range(b.data.ncon):
            c = b.data.contact[i]
            names = [b.model.geom(int(g)).name for g in (c.geom1, c.geom2)]
            if any(n and ('diagnostic_' in n or 'table_leg_' in n) for n in names):
                force = np.zeros(6)
                mujoco.mj_contactForce(b.model, b.data, i, force)
                contacts.append({'geoms': names, 'normal_force_n': float(force[0])})
        self.diagnostics.append({
            'sim_s': float(b.data.time), 'command_id': b.status().get('command_id'),
            'cube_world_m': b.data.body('diagnostic_cube').xpos.tolist(),
            'cube_quaternion_wxyz': b.data.body('diagnostic_cube').xquat.tolist(),
            'gripper_closure': b.gripper_command_at(b.data.time),
            'normalized_action29': b.adapter.action_history[0, -1].tolist(),
            'q29_rad': b.data.qpos[b.adapter._policy_qpos_adr].tolist(),
            'dq29_rad_s': b.data.qvel[b.adapter._policy_dof_adr].tolist(),
            'torque29_nm': b.data.ctrl[b.act].tolist(),
            'wrist_pi_torque29_nm': b.wrist_pi_tau.tolist(), 'contacts': contacts})

    def close(self):
        b = self.backend
        (self.output/'host_diagnostics.json').write_text(json.dumps({
            'actor_access': False, 'joint_names': b.adapter.metadata['joint_names'],
            'torque_limits_nm': b.limits.tolist(), 'ticks': self.diagnostics}))
        np.savez_compressed(self.output/'scalebfm_task_inputs.npz',
                            policy_task=np.asarray(self.task_inputs))
        super().close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--table-shift-x-m', type=float, default=0.)
    parser.add_argument('--replace-right-closure', type=float, nargs=2, metavar=('OLD', 'NEW'),
                        help='Counterfactual only: replace this right-hand closure in recorded commands')
    parser.add_argument('--learning-campaign', action='store_true',
                        help='Match R018 grasp evaluator and unrestricted per-episode action count')
    args = parser.parse_args()
    if args.replace_right_closure is not None and (
            not np.isfinite(args.replace_right_closure).all()
            or not all(0 <= v <= 1 for v in args.replace_right_closure)):
        parser.error('closure values must be finite and in [0, 1]')
    args.output.mkdir(parents=True, exist_ok=False)
    label = (f'COUNTERFACTUAL GRIP {args.replace_right_closure} | GPT calls 0 | not an evaluation trial'
             if args.replace_right_closure else None)
    def backend_factory():
        backend = create_settled_backend()
        # Counterfactual diagnostics only: preserve robot state and commands,
        # move table edge away. This is never training/evaluation success data.
        backend.model.geom('diagnostic_table').pos[0] += args.table_shift_x_m
        mujoco.mj_forward(backend.model, backend.data)
        return backend
    host_class = LocoManipToolHost if args.learning_campaign else EvaluationHost
    evaluator = GraspLiftEvaluator if args.learning_campaign else LiftEvaluator
    host = host_class(args.output/'rollout', backend_factory,
        evaluator_factory=evaluator,
        image_capture_factory=lambda b: AuditVideo(b, args.output/'video', label=label))
    comparisons = []
    replaced = 0
    error = None
    try:
        packet = host.dispatch('loco_start', {'task': 'Replay recorded Direct actions for diagnostics',
                              'output_dir': str((args.output/'rollout/episode').resolve())})
        for p in sorted((args.source/'agent/rpc_calls').glob('*_request.json')):
            request = json.loads(p.read_text())
            if request['tool'] != 'scalebfm_act':
                continue
            a = request['arguments']
            a = json.loads(a) if isinstance(a, str) else a
            if args.replace_right_closure:
                old, new = args.replace_right_closure
                for waypoint in a['response']['trajectory']:
                    if abs(waypoint['grippers']['right']-old) < 1e-9:
                        waypoint['grippers']['right'] = new
                        replaced += 1
            original = json.loads(p.with_name(p.name.replace('_request', '_result')).read_text())
            packet = host.dispatch('scalebfm_act', {
                'observation_path': str(host.harness.latest_path), 'response': a['response'],
                'output_dir': str((args.output/'rollout'/p.stem).resolve())})
            delta = abs(packet['execution'][0]['actual_error_m']-
                        original['execution'][0]['actual_error_m'])
            comparisons.append({'request': p.name, 'residual_difference_m': delta,
                                'status': packet['execution'][0]['status']})
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        host.close()
    result = {'gpt_calls': 0, 'replay_is_not_an_independent_policy_trial': True,
              'scalebfm_inference_calls': len(host.capture.task_inputs),
              'comparisons': comparisons, 'native_outcome': packet.get('native_outcome')}
    result['diagnostic_table_shift_x_m'] = args.table_shift_x_m
    result['counterfactual_right_closure_replacement'] = args.replace_right_closure
    result['replaced_waypoints'] = replaced
    result['error'] = error
    (args.output/'replay_result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    if error:
        raise RuntimeError(error)


if __name__ == '__main__':
    main()
