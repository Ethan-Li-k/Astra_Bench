"""Explicit GPT-6 Astra direct-policy simulation entrypoint."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time
import hashlib

os.environ.setdefault('MUJOCO_GL', 'egl')

from rsi.codex_app_server import CodexPolicyAdapter
from rsi.evaluator import LiftEvaluator
from rsi.episode_video import EpisodeVideo
from rsi.live import LiveSim
from rsi.stdio_transport import StdioAppServer
from rsi.tool_host import LocoManipToolHost


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'.cursor/skills/loco-manip-four-point-policy'


def policy_prompt(rollout_root):
    sources = [SKILL/'SKILL.md', SKILL/'CONTROL_CONTRACT.md',
               SKILL/'tasks/grasp_red_cube/TASK.md']
    body = '\n\n'.join(path.read_text() for path in sources)
    return body + f'''\n\n# Runtime boundary
This is one DRAFT simulation episode. Use registered tools only. Never claim
that a request was executed until a fresh receipt and observation show it.
Every tool output_dir must be a new child of {Path(rollout_root).resolve()}.
The first output_dir is {Path(rollout_root).resolve()/'episode'}; use monotonically
numbered call directories afterward. Do not use privileged simulator state.
Zero-demonstration trial: no examples, no pi0.5 and no other-episode memory.
Only inspect the returned head/right-wrist RGB and named robot state. Do not
read source code, logs, files outside returned observation paths, or evaluator
internals. Do not use native shell, browser or unrelated tools. The policy
context persists within this episode; retain brief evidence-based progress,
failed attempt and next hypothesis in public action reasons. Weights do not learn.
Use a SINGLE waypoint per call for this pilot. Reobserve before the next action.
After a timeout, reconsider direction, scale or approach using measured state;
do not blindly repeat. Continue until rollout_finished=true, then report the
native outcome and failure evidence. Missing demonstration is not a stop reason.
'''


class EvaluationHost(LocoManipToolHost):
    """Pilot budget and public outcomes; never exposes evaluator geometry."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_count = self.timeouts = 0
        self.finished = False
        self.stop_reason = None

    def dispatch(self, name, arguments):
        if self.finished:
            raise ValueError('Episode is finished; no further execution is allowed')
        if name == 'scalebfm_act' and len(arguments.get('response', {}).get('trajectory', [])) != 1:
            raise ValueError('This pilot requires exactly one waypoint before reobserving')
        packet = super().dispatch(name, arguments)
        if name == 'scalebfm_act':
            self.action_count += 1
            self.timeouts = self.timeouts+1 if self.backend.status()['status'] == 'timed_out' else 0
        outcome = packet.get('native_outcome')
        if outcome in ('success', 'failure'):
            self.stop_reason = 'native_'+outcome
        elif self.timeouts >= 3:
            self.stop_reason = 'three_consecutive_tracking_timeouts'
        elif self.action_count >= 12:
            self.stop_reason = 'action_budget'
        self.finished = self.stop_reason is not None
        packet.update(rollout_finished=self.finished, stop_reason=self.stop_reason,
                      executed_chunks=self.action_count, remaining_chunks=12-self.action_count)
        return packet


def create_settled_backend(*, table_only_offset_x=0.):
    backend = LiveSim(wrist_pi=True, table_only_offset_x=table_only_offset_x)
    for _ in range(250):
        backend.tick()
    if backend.reason:
        raise RuntimeError(f'Initial 5 s settling failed: {backend.reason}')
    return backend


def main():
    parser = argparse.ArgumentParser(
        description='Run one explicit Codex/Astra vision-only MuJoCo episode.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--task', default='Visually grasp and lift the red cube.')
    parser.add_argument('--model', choices=('gpt-6-astra',), default='gpt-6-astra')
    parser.add_argument('--effort', choices=('xhigh',), default='xhigh')
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--table-only-offset-x-m', type=float, default=0.)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise ValueError('output must be a new path')
    output.mkdir(parents=True)
    codex = shutil.which('codex')
    if codex is None:
        raise RuntimeError('codex CLI is unavailable')

    rollout_root = output/'rollout'
    host = EvaluationHost(
        rollout_root, lambda: create_settled_backend(table_only_offset_x=args.table_only_offset_x_m), method='direct',
        evaluator_factory=LiftEvaluator,
        image_capture_factory=lambda backend: EpisodeVideo(backend, output/'video'))
    transport = StdioAppServer([codex, 'app-server', '--stdio'], output/'app_server')
    adapter = CodexPolicyAdapter(
        transport, host, output/'agent',
        developer_instructions=policy_prompt(rollout_root),
        model=args.model, effort=args.effort, timeout=args.timeout)
    started = time.monotonic()
    prompt = policy_prompt(rollout_root)
    (output/'actor_prompt.md').write_text(prompt)
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for folder in ('rsi', 'tools', '.cursor/skills/loco-manip-four-point-policy')
               for p in (ROOT/folder).rglob('*') if p.suffix in ('.py', '.md')}
    (output/'source_hashes.json').write_text(json.dumps(sources, indent=2))
    error = None
    try:
        adapter.connect()
        first_call = {'tool': 'loco_start', 'task': args.task,
                      'output_dir': str(rollout_root/'episode')}
        turn = adapter.run_turn(
            'Run one authorized vision-only simulation episode. Keep acting until the '
            'native outcome is success/failure or a declared stop condition occurs. '
            'First call: ' + json.dumps(first_call))
        (output/'turn_result.json').write_text(json.dumps(turn, indent=2))
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        host.close()
        transport.close()
        native = host.harness.evaluator.outcome(host.backend) if host.harness else 'not_started'
        timings = [json.loads(p.read_text()) for p in sorted(adapter.calls.glob('*_timing.json'))]
        result = {'method': 'gpt_direct_zero_demo', 'backend': 'MuJoCo',
                  'model': args.model, 'effort': args.effort,
                  'codex_turns_started': adapter.turns_started,
                  'dynamic_tool_calls': adapter.call_index,
                  'internal_model_request_count': None,
                  'wall_s': time.monotonic()-started,
                  'sim_s': float(host.backend.data.time)-5 if host.backend else 0,
                  'native_outcome': native,
                  'success': native == 'success' and error is None,
                  'stop_reason': error or host.stop_reason or 'model_ended_before_native_success',
                  'executed_chunks': host.action_count,
                  'timings': timings, 'simulation_pauses_during_planning': True,
                  'actor_cameras': ['head_cam', 'right_wrist_cam'],
                  'demonstrations': 0, 'cross_episode_memory': False}
        result['scene_table_only_offset_x_m'] = args.table_only_offset_x_m
        (output/'evaluation.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({k:v for k,v in result.items() if k != 'timings'}), flush=True)


if __name__ == '__main__':
    main()
