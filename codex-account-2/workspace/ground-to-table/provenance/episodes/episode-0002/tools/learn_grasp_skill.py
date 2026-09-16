"""Astra/xhigh learns its skill from physical trials until ten grasp successes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.environ.setdefault('MUJOCO_GL', 'egl')
import numpy as np

from rsi.codex_app_server import CodexPolicyAdapter
from rsi.evaluator import GraspLiftEvaluator
from rsi.episode_video import EpisodeVideo
from rsi.policy_harness import _object, tool_specs
from rsi.skill_learning import CampaignLedger, SkillMemory, usage_exhausted
from rsi.stdio_transport import StdioAppServer
from rsi.tool_host import LocoManipToolHost
from tools.codex_direct_sim import ROOT, create_settled_backend

SKILL = ROOT/'skills/loco-manip-direct/SKILL.md'
CODEX_LAUNCHER = Path('/home/galbot/lizekai/RSI/codex-account-2/run.sh')
PYTHON = '/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python'
TASK = ('Use either DEX3 hand to grasp the red cube seen on the tabletop. '
        'Lift the cube at least 5 cm above its starting height and retain the grasp '
        'for at least 0.5 seconds while keeping the humanoid standing. '
        'Choose actions from RGB, named robot state and your own observed experience. '
        'There is no human demonstration. Do not count hand closure, wrist motion, '
        'pushing the cube, or a single image as task completion. Verify cube-hand '
        'co-motion and continued support in successive observations. The host '
        'confirms the native outcome. Learn from failed attempts and keep trying; '
        'ten independently reset successful grasps are required before SIMPLE door pushing.')


def finger_geometry(backend):
    result = {}
    for side in ('left', 'right'):
        wrist = backend.model.body(f'{side}_wrist_yaw_link').id
        origin = backend.data.xpos[wrist]
        rotation = backend.data.xmat[wrist].reshape(3, 3)
        result[side] = {}
        for finger, segment in (('thumb', 2), ('index', 1), ('middle', 1)):
            geom = backend.model.geom(f'{side}_hand_{finger}_{segment}_collision')
            center = backend.data.geom_xpos[geom.id]
            axis = backend.data.geom_xmat[geom.id].reshape(3, 3)[:, 2]*geom.size[1]
            result[side][finger] = {'capsule_endpoints_wrist_m':
                [((center-axis-origin)@rotation).tolist(), ((center+axis-origin)@rotation).tolist()],
                'radius_m': float(geom.size[0])}
    return result


class LearningHost(LocoManipToolHost):
    def __init__(self, output, memory, episode_id, successes, *, task=TASK,
                 backend_factory=create_settled_backend, evaluator_factory=GraspLiftEvaluator,
                 image_capture_factory=None, support_plane_z_m=.630,
                 geometry_provider=finger_geometry, max_episode_steps=6000,
                 require_selection=False):
        super().__init__(output/'rollout', backend_factory,
            evaluator_factory=evaluator_factory,
            image_capture_factory=image_capture_factory or (lambda b: EpisodeVideo(b, output/'video',
                label='Astra/xhigh | self-learning Direct | no human demonstration')))
        self.task, self.support_plane_z_m = task, support_plane_z_m
        self.geometry_provider = geometry_provider
        self.max_episode_steps = max_episode_steps
        self.episode_start_sim_s = 5.  # overwritten by the actual loco_start observation
        self.output, self.memory, self.episode_id = output, memory, episode_id
        self.finished = self.skill_updated = False
        self.calls = self.actions = 0
        self.successes = successes
        self.stop_reason = None
        self.require_selection = require_selection
        self.selection_recorded = False
        self.skill_sources = {}
        self.selected_source_ids = []

    def tool_specs(self):
        string = {'type': 'string'}
        return tool_specs('direct') + [
            {'type':'function','name':'experience_select',
             'description':'Record which listed self-experience/skill sources you choose, why, adaptation to current observations, and what you reject. Required before the first action when workspace says so; reselect when needed.',
             'inputSchema':_object({'selected_ids':{'type':'array','items':string,'minItems':1},
                 'rationale':string,'adaptation':string,'not_reused':string})},
            {'type':'function', 'name':'finish_attempt',
             'description':'After at least three executed actions, end an unproductive attempt with public evidence and a changed hypothesis. This is NOT success. Use instead of repeated idle holds; then submit skill_update. Never call merely because reasoning is slow.',
             'inputSchema':_object({'reason':string, 'next_hypothesis':string,
                 'evidence_paths':{'type':'array','items':string,'minItems':1}})},
            {'type': 'function', 'name': 'experience_read',
             'description': 'Read current skill, recent brief lessons and earliest self-generated native success; pass a version for its full original lesson and evidence.',
             'inputSchema': {'type': 'object', 'properties': {'version': {'type': 'integer', 'minimum': 1}},
                             'additionalProperties': False}},
            {'type': 'function', 'name': 'skill_update',
             'description': 'After this episode ends, submit the revised local skill, lesson and change summary. shared_candidate stores a proposal for later cross-task validation; it never overwrites the shared core.',
             'inputSchema': _object({'markdown': string, 'lesson': string,
                'transfer_scope':{'type':'string','enum':['task_specific','shared_candidate']},
                'change_summary':string,
                'evidence_paths': {'type': 'array', 'items': string, 'minItems': 1}})}]

    def next_call(self):
        if self.finished:
            return {'tool':'skill_update', 'evidence_root':str(self.rollout_root),
                'suggested_existing_evidence':[str(p) for p in
                    (self.rollout_root/'history.jsonl',self.rollout_root/'policy_stop.json',
                     self.rollout_root/'initialization_error.json') if p.is_file()]}
        if self.harness is None:
            return {'tool': 'loco_start', 'task': self.task,
                    'output_dir': str(self.rollout_root/'episode')}
        if self.require_selection and not self.selection_recorded:
            return {'tool':'experience_select','available_source_ids':list(self.skill_sources)}
        return {
            'tool': 'scalebfm_act', 'observation_path': str(self.harness.latest_path),
            'output_dir': str(self.rollout_root/f'call_{self.calls:04d}')}

    def dispatch(self, name, arguments):
        if name == 'experience_select':
            self._strict(arguments, ('selected_ids','rationale','adaptation','not_reused'))
            ids=arguments['selected_ids']
            if not ids or len(set(ids))!=len(ids) or not set(ids)<=set(self.skill_sources):
                raise ValueError('Select unique IDs from workspace skill_sources')
            if any(not arguments[k].strip() for k in ('rationale','adaptation','not_reused')):
                raise ValueError('Selection rationale, adaptation and exclusions are required')
            self.selection_recorded=True;self.selected_source_ids=list(ids)
            row=dict(arguments,episode_id=self.episode_id,actions_so_far=self.actions,
                     selected_sources={i:self.skill_sources[i] for i in ids})
            with (self.rollout_root/'skill_selection.jsonl').open('a') as stream:
                stream.write(json.dumps(row,ensure_ascii=False)+'\n')
            return row | {'next_call':self.next_call()}
        if name == 'finish_attempt':
            self._strict(arguments, ('reason','next_hypothesis','evidence_paths'))
            if self.finished or self.harness is None or self.actions < 3 or self.backend.active:
                raise ValueError('Need three completed physical actions in an unfinished attempt')
            paths = [Path(p).resolve() for p in arguments['evidence_paths']]
            if (not paths or any(self.rollout_root.resolve() not in p.parents or not p.is_file() for p in paths)
                    or not arguments['reason'].strip() or not arguments['next_hypothesis'].strip()):
                raise ValueError('Current public evidence, a reason and a changed hypothesis are required')
            self.finished = True
            self.stop_reason = 'policy_declared_stall'
            packet = dict(arguments, rollout_finished=True, stop_reason=self.stop_reason,
                native_outcome=self.harness.evaluator.outcome(self.backend), next_call=self.next_call())
            (self.rollout_root/'policy_stop.json').write_text(json.dumps(packet,indent=2))
            return packet
        if name == 'experience_read':
            if not isinstance(arguments, dict) or set(arguments)-{'version'}:
                raise ValueError('experience_read accepts only an optional version')
            return self.memory.read(**arguments) | {'next_call': self.next_call(), 'successes_so_far': self.successes}
        if name == 'skill_update':
            fields=('markdown','lesson','evidence_paths')
            if self.require_selection or 'transfer_scope' in arguments:
                fields+=('transfer_scope','change_summary')
            self._strict(arguments, fields)
            if not self.finished:
                raise ValueError('Finish this physical episode before revising its skill')
            if self.skill_updated:
                raise ValueError('This episode already produced its skill revision')
            row = self.memory.update(**arguments, evidence_root=self.rollout_root,
                episode_id=self.episode_id, outcome=(self.harness.evaluator.outcome(self.backend)
                    if self.harness and self.initialization_error is None else 'not_started'),
                selected_source_ids=self.selected_source_ids)
            self.skill_updated = True
            print(json.dumps({'event': 'skill_updated', **row}, ensure_ascii=False), flush=True)
            return row
        if self.finished:
            raise ValueError('Episode ended; read its evidence and submit skill_update')
        if name == 'scalebfm_act' and self.require_selection and not self.selection_recorded:
            raise ValueError('Call experience_select before the first physical action')
        if name == 'scalebfm_act' and len(arguments.get('response', {}).get('trajectory', [])) != 1:
            raise ValueError('Use one waypoint and reobserve before the next')
        packet = super().dispatch(name, arguments)
        self.calls += 1
        if name == 'loco_start' and self.initialization_error is not None:
            self.finished = True
            self.stop_reason = 'backend_initialization_error'
            return packet | {'next_call': self.next_call()}
        if name == 'scalebfm_act':
            self.actions += 1
        if self.harness:
            if name == 'loco_start':
                self.episode_start_sim_s = float(self.backend.data.time)
            native = self.harness.evaluator.outcome(self.backend)
            steps = round((float(self.backend.data.time)-self.episode_start_sim_s)/.02)
            if native in ('success', 'failure'):
                self.stop_reason = 'native_'+native
            elif steps >= self.max_episode_steps:
                self.stop_reason = 'episode_step_budget'
            self.finished = self.stop_reason is not None
            packet.update(native_outcome=native, rollout_finished=self.finished,
                stop_reason=self.stop_reason, step_id=steps, max_episode_steps=self.max_episode_steps,
                remaining_steps=max(0, self.max_episode_steps-steps), successes_so_far=self.successes,
                next_call=self.next_call())
            if 'observation' in packet:
                if self.geometry_provider is not None:
                    packet['observation']['finger_geometry'] = self.geometry_provider(self.backend)
                if self.support_plane_z_m is not None:
                    packet['workspace_calibration'] = {'horizontal_support_plane_z_m': self.support_plane_z_m}
                Path(packet['observation_path']).write_text(json.dumps(packet['observation'], indent=2))
            if name in ('loco_start', 'scalebfm_act'):
                with (self.rollout_root/'history.jsonl').open('a') as stream:
                    stream.write(json.dumps({'tool': name, 'arguments': arguments,
                        'observation_path': packet.get('observation_path'),
                        'execution': packet.get('execution'), 'native_outcome': native})+'\n')
                print(json.dumps({'event': name, 'episode': self.episode_id, 'actions': self.actions,
                    'sim_steps': steps, 'native_outcome': native, 'finished': self.finished,
                    'status': self.backend.status().get('status'),
                    'error_m': self.backend.status().get('actual_error_m')}), flush=True)
            self._write(Path(arguments['output_dir']), 'tool_result.json', packet)
        return packet


def run_episode(output, memory, episode_id, successes, *, host_factory=LearningHost,
                python=PYTHON, required_successes=10, transfer_sources=(),
                task_specification=None, skill_sources=None):
    output.mkdir(parents=True, exist_ok=False)
    host = host_factory(output, memory, episode_id, successes)
    host.skill_sources = skill_sources or {}
    if not os.access(CODEX_LAUNCHER, os.X_OK):
        raise RuntimeError('Authorized second-account launcher unavailable; no account fallback')
    transport = StdioAppServer([str(CODEX_LAUNCHER), 'app-server', '--stdio'], output/'app_server')
    (output/'model_backend.json').write_text(json.dumps({
        'launcher': str(CODEX_LAUNCHER), 'account_route': 'authorized_account_2',
        'model': 'gpt-6-astra', 'effort': 'xhigh', 'fallback': False}, indent=2))
    agent = output/'agent'; agent.mkdir()
    (agent/'scratch').mkdir()
    context = {'python': python, 'task': host.task, 'skill': str(memory.skill),
        'python_usage': 'Use this exact interpreter for NumPy, SciPy and PIL; do not install packages.',
        'public_evidence_root': str(host.rollout_root), 'notes': str(agent/'NOTES.md'),
        'skill_version': memory.read()['version'], 'successes_so_far': successes,
        'required_successes': required_successes, 'model': 'gpt-6-astra', 'effort': 'xhigh'}
    context.update(task_specification=task_specification,
        skill_sources=host.skill_sources, require_experience_selection=host.require_selection)
    if memory.journal.exists():
        context['self_experience_archive'] = str(memory.journal.resolve())
        context['self_skill_versions'] = str((memory.root/'versions').resolve())
    if transfer_sources:
        context['transferred_self_experience'] = list(map(str, transfer_sources))
    (agent/'workspace.json').write_text(json.dumps(context, indent=2))
    prompt = memory.skill.read_text()
    (output/'SKILL.md').write_text(prompt)
    (agent/'SKILL.md').write_text(prompt)
    immutable = ('\nRead workspace.json. Its ground-to-table task overrides historical task goals. '
        'Use registered physical tools and listed public evidence only. Never inspect host audit '
        'or simulator internals. Await complete Astra/xhigh responses. After the episode '
        'ends submit skill_update. The complete prompt must fit 831 words / 6250 characters.\n')
    from rsi.skill_learning import skill_size
    size = skill_size(prompt+immutable)
    if size['words'] > 831 or size['characters'] > 6250:
        raise ValueError('Combined main skill/runtime prompt exceeds cap')
    (output/'prompt_size.json').write_text(json.dumps(size,indent=2))
    adapter = CodexPolicyAdapter(transport, host, agent,
        developer_instructions=prompt+immutable, normal_tools=True)
    started = time.monotonic(); error = None
    try:
        adapter.connect()
        while not host.skill_updated:
            turn = adapter.run_turn('Continue the authorized autonomous skill-learning attempt. '
                'Use experience_read, follow SKILL.md and the current next_call: '+json.dumps(host.next_call())+
                '. Do not treat a finished model turn as a finished physical episode. '
                'When rollout_finished=true, submit your evidence-backed skill_update.')
            (output/f'turn_{adapter.turns_started:03d}.json').write_text(json.dumps(turn, indent=2))
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        print(json.dumps({'event': 'episode_error', 'error': error}), flush=True)
    finally:
        host.close(); transport.close()
    native = (host.harness.evaluator.outcome(host.backend)
              if host.harness and host.initialization_error is None else 'not_started')
    if host.initialization_error is not None and error is None:
        error = ('BackendInitializationError: '+host.initialization_error['error'])
    result = {'success': native == 'success' and error is None, 'native_outcome': native,
        'episode_id': episode_id, 'skill_updated': host.skill_updated,
        'error': error, 'stop_reason': host.stop_reason, 'model': 'gpt-6-astra', 'effort': 'xhigh',
        'account_route': 'authorized_account_2', 'codex_launcher': str(CODEX_LAUNCHER),
        'codex_turns': adapter.turns_started, 'dynamic_tool_calls': adapter.call_index,
        'actions': host.actions, 'wall_s': time.monotonic()-started,
        'sim_s': float(host.backend.data.time)-host.episode_start_sim_s if host.backend else 0,
        'starting_skill_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'no_human_demonstration': True, 'self_experience_enabled': True,
        'video': str(output/'video/episode.mp4')}
    (output/'result.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.output.resolve(); root.mkdir(parents=True, exist_ok=True)
    memory = SkillMemory(root/'memory', SKILL)
    ledger = CampaignLedger(root/'progress.json')
    while not ledger.simple_unlocked:
        existing = [int(p.name.split('-')[1]) for p in root.glob('episode-*')]
        episode_id = f'episode-{max(existing, default=0)+1:04d}'
        result = run_episode(root/episode_id, memory, episode_id, ledger.successes)
        ledger.record(episode_id, result)
        print(json.dumps({'event': 'campaign_progress', 'successes': ledger.successes,
                          'attempts': len(ledger.rows)}, ensure_ascii=False), flush=True)
        if usage_exhausted(result):
            (root/'quota_pause.json').write_text(json.dumps({
                'episode_id': episode_id, 'reason': 'usageLimitExceeded',
                'resume': 'Restart this same command after subscription usage is available.'}, indent=2))
            raise SystemExit('Subscription usage exhausted; no automatic retry or model fallback.')
        if result['error']:
            time.sleep(30)
    # Stage transition is gated by distinct, host-verified physical successes.
    print(json.dumps({'event': 'entering_simple', 'successes': ledger.successes}), flush=True)
    simple_python = '/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python'
    env = dict(os.environ, PYTHONPATH=str(ROOT)+':/home/galbot/lizekai/Loco_manip/locomanip/src')
    with (root/'simple-transition.log').open('a') as log:
        code = subprocess.call([simple_python, str(ROOT/'tools/simple_scalebfm_audit.py'),
            '--output', str(root/f'simple-transition-{int(time.time())}'),
            '--data-root', str(ROOT/'data/simple/runtime')], stdout=log, stderr=log, env=env)
    (root/'stage.json').write_text(json.dumps({'stage': 'simple', 'entry_exit_code': code,
                                             'grasp_successes': ledger.successes}, indent=2))


if __name__ == '__main__':
    main()
