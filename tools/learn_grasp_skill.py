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

from rsi.codex_app_server import CodexPolicyAdapter, TURN_RECORD_CONTRACT, NETWORK_CONTINUATION
from rsi.evaluator import GraspLiftEvaluator
from rsi.episode_video import EpisodeVideo
from rsi.policy_harness import _object, tool_specs
from rsi.public_robot_interface import dispatch as public_robot_dispatch, tool_specs as public_robot_tool_specs
from rsi.skill_learning import CampaignLedger, SkillMemory, usage_exhausted, validate_policy_instructions
from rsi.actor_quota_boundary import CodexQuotaBoundary
from rsi.actor_api_handoff import continue_after_quota, start_api_episode, BACKEND_POLICY
from rsi.episode_continuation import ClosedNetworkNoProgress, wait_for_network_diagnosis
from rsi.actor_inputs import context_text, pin_actor_inputs, stage_claim, ambient_contract
from rsi.public_clock import public_clock
from rsi.stdio_transport import StdioAppServer
from rsi.tool_host import LocoManipToolHost
from tools.codex_direct_sim import ROOT, create_settled_backend

SKILL = ROOT/'skills/loco-manip-direct/SKILL.md'
CODEX_LAUNCHER = ROOT/'codex-account-2/run.sh'
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
                 require_selection=False, execution_profile=None):
        super().__init__(output/'rollout', backend_factory,
            evaluator_factory=evaluator_factory,
            image_capture_factory=image_capture_factory or (lambda b: EpisodeVideo(b, output/'video',
                label='Astra/xhigh | self-learning Direct | no human demonstration')))
        self.task, self.support_plane_z_m = task, support_plane_z_m
        self.geometry_provider = geometry_provider
        profile = execution_profile or {'id':'legacy-finite-v1', 'phase':'legacy',
            'max_episode_steps':max_episode_steps, 'checkpoint_steps':12000}
        if profile.get('id') == 'learning-horizon-v1':
            if profile.get('phase') not in ('learning','stability') or max_episode_steps is not None:
                raise ValueError('Learning horizon requires a non-terminating cumulative budget')
        elif type(max_episode_steps) is not int or max_episode_steps <= 0:
            raise ValueError('Finite execution requires a positive step budget')
        if profile.get('max_episode_steps') != max_episode_steps:
            raise ValueError('Execution profile and budget disagree')
        self.execution_profile = dict(profile)
        self.max_episode_steps = max_episode_steps
        self.episode_start_sim_s = 5.  # overwritten by the actual loco_start observation
        self.output, self.memory, self.episode_id = output, memory, episode_id
        self.finished = self.skill_updated = False
        self.execution_error = None
        self.calls = self.actions = 0
        self.successes = successes
        self.stop_reason = None
        self.require_selection = require_selection
        self.selection_recorded = False
        self.skill_sources = {}
        self.selected_source_ids = []
        self.stage_progress_required = False
        self.native_start_steps = None
        self.declared_native_max = None
        self.attempt_progress_config = None
        self.progress_contract = None
        self.progress_supervisor = None
        self.corrective_action_checkpoint = None
        self.corrective_attempt_required = False
        self.allow_voluntary_deferral = False  # Exact learning hosts opt in; no hidden progress signal.

    def tool_specs(self):
        string = {'type': 'string'}
        return tool_specs('direct') + public_robot_tool_specs() + [
            {'type':'function','name':'experience_select',
             'description':'Record which listed self-experience/skill sources you choose, why, adaptation to current observations, and what you reject. Required before the first action when workspace says so; reselect when needed.',
             'inputSchema':_object({'selected_ids':{'type':'array','items':string,'minItems':0},
                 'rationale':string,'adaptation':string,'not_reused':string})},
            {'type':'function', 'name':'finish_attempt',
             'description':'Record public stall evidence and a changed hypothesis. Revised progress contracts first request a corrective attempt in this reset. Optional defer_outside_workspace declares a publicly observed floor/out-of-workspace target; it is not an audited fact. Follow next_call, never stop for reasoning latency.',
             'inputSchema':{'type':'object','additionalProperties':False,
                 'properties':{'reason':string,'next_hypothesis':string,
                    'evidence_paths':{'type':'array','items':string,'minItems':1},
                    'disposition':{'type':'string','enum':['revise_here','defer_outside_workspace']}},
                 'required':['reason','next_hypothesis','evidence_paths']}},
            {'type': 'function', 'name': 'experience_read',
             'description': 'Read current skill, recent lessons and earliest completed task-audited success matching the current completion contract. Unknown/rejected records are not success-prioritized; pass a version for original evidence and current retrieval labels.',
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
                     self.rollout_root/'policy_stall.jsonl',
                     self.rollout_root/'initialization_error.json',
                     self.rollout_root/'execution_error.json') if p.is_file()]}
        if self.harness is None:
            return {'tool': 'loco_start', 'task': self.task,
                    'output_dir': str(self.rollout_root/'episode')}
        if self.require_selection and not self.selection_recorded:
            return {'tool':'experience_select','available_source_ids':list(self.skill_sources)}
        return {
            'tool': 'scalebfm_act', 'observation_path': str(self.harness.latest_path),
            'output_dir': str(self.rollout_root/f'call_{self.calls:04d}')}

    def dispatch(self, name, arguments):
        if name in ('robot_brief', 'transform_pose'):
            if self.harness is None or self.harness.latest_path is None:
                return dict(status='rejected', error='Call loco_start before public robot reads.',
                    no_execution=True, no_physical_action=True, retryable=True)
            return public_robot_dispatch(name, self.harness.latest_path, arguments)
        claim = (stage_claim(arguments['response']['reason'])
                 if name == 'scalebfm_act' and self.stage_progress_required else None)
        if name == 'scalebfm_act':
            from rsi.attempt_progress import admit_claim
            admit_claim(self,claim)
        if name == 'experience_select':
            self._strict(arguments, ('selected_ids','rationale','adaptation','not_reused'))
            from rsi.reset_experience import record_selection
            record_selection(self,arguments)
            ids=arguments['selected_ids']
            if not isinstance(ids,list) or len(set(ids))!=len(ids) or not set(ids)<=set(self.skill_sources):
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
            fields=('reason','next_hypothesis','evidence_paths')
            if 'disposition' in arguments:fields+=('disposition',)
            self._strict(arguments, fields)
            disposition=arguments.get('disposition','revise_here')
            if disposition not in ('revise_here','defer_outside_workspace'):
                raise ValueError('Unknown stall disposition')
            if (self.finished or self.harness is None or self.backend.active
                    or (self.actions < 3 and disposition != 'defer_outside_workspace')):
                raise ValueError('Need three completed physical actions in an unfinished attempt')
            paths = [Path(p).resolve() for p in arguments['evidence_paths']]
            if (not paths or any(self.rollout_root.resolve() not in p.parents or not p.is_file() for p in paths)
                    or not arguments['reason'].strip() or not arguments['next_hypothesis'].strip()):
                raise ValueError('Current public evidence, a reason and a changed hypothesis are required')
            if self.progress_supervisor:
                guard=self.progress_supervisor.guard
                correction_required=guard.config.get('corrective_attempt_required',False)
                corrected=(self.corrective_action_checkpoint is not None
                           and self.actions>self.corrective_action_checkpoint)
                if (not correction_required or corrected or guard.stop_reason
                        or disposition=='defer_outside_workspace'):
                    guard.stop('progress_actor_stall')
                    self.finished = True
                    self.stop_reason = guard.stop_reason
                    self.progress_supervisor.publish(self.rollout_root/'progress.json')
                elif self.corrective_action_checkpoint is None:
                    self.corrective_action_checkpoint=self.actions
            elif self.allow_voluntary_deferral and self.execution_profile['phase'] == 'learning':
                corrected=(self.corrective_action_checkpoint is not None
                           and self.actions>self.corrective_action_checkpoint)
                if not self.corrective_attempt_required or corrected or disposition=='defer_outside_workspace':
                    self.finished = True
                    self.stop_reason = 'actor_learning_deferral'
                elif self.corrective_action_checkpoint is None:
                    self.corrective_action_checkpoint=self.actions
            packet = dict(arguments, rollout_finished=self.finished, stop_reason=self.stop_reason,
                native_outcome=self.harness.evaluator.outcome(self.backend),
                actions_so_far=self.actions, observation_path=str(self.harness.latest_path),
                next_call=self.next_call(),
                continuation=('Learning attempt stopped. Save the missing prerequisite, '
                    'failure evidence and changed hypothesis with skill_update.' if self.finished else
                    'Stall recorded, not a terminal outcome. Use the current observation '
                    'and next_call to test next_hypothesis in this episode; avoid unchanged retries '
                    'and idle holds. Submit skill_update only after rollout_finished=true.'))
            from rsi.attempt_progress import record as record_progress
            record_progress(self)
            with (self.rollout_root/'policy_stall.jsonl').open('a') as stream:
                stream.write(json.dumps(packet,ensure_ascii=False)+'\n')
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
            from rsi.reset_experience import save_lesson
            save_lesson(self,arguments)
            self.skill_updated = True
            print(json.dumps({'event': 'skill_updated', **row}, ensure_ascii=False), flush=True)
            return row
        if self.finished:
            raise ValueError('Episode ended; read its evidence and submit skill_update')
        if name == 'scalebfm_act' and self.require_selection and not self.selection_recorded:
            raise ValueError('Call experience_select before the first physical action')
        if (name == 'scalebfm_act' and len(arguments.get('response', {}).get('trajectory', [])) != 1
                and not getattr(self.backend, 'continuous_chunks_enabled', False)):
            raise ValueError('Use one waypoint and reobserve before the next')
        if name == 'scalebfm_act' and self.progress_supervisor:
            # Validate normal action identity/schema before progress admission.
            self.harness._require_latest(arguments['observation_path'])
            from rsi.policy_harness import validate_response
            validate_response(arguments['response'])
            observation = json.loads(self.harness.latest_path.read_text())
            if not self.progress_supervisor.admit(claim, arguments['response'], observation):
                self.stop_reason = self.progress_supervisor.guard.stop_reason
                self.finished = self.stop_reason is not None
                progress = self.progress_supervisor.publish(self.rollout_root/'progress.json')
                packet = dict(no_execution=True, rollout_finished=self.finished, stop_reason=self.stop_reason,
                    admission_error=getattr(self.progress_supervisor.guard,'admission_error',None),
                    correction='Use current RGB to reacquire the original target; no empty-hand transport. No action executed.',
                    observation_path=str(self.harness.latest_path), progress=progress,
                    next_call=self.next_call())
                with (self.rollout_root/'policy_rejections.jsonl').open('a') as stream:
                    stream.write(json.dumps(dict(packet,rejected_request=arguments['response']))+'\n')
                if self.finished:
                    (self.rollout_root/'policy_stop.json').write_text(json.dumps(packet,indent=2))
                output = self._new_output(arguments['output_dir'], create=True)
                self._write(output, 'tool_result.json', packet)
                return packet
        before_sim_s = (float(self.backend.data.time)
                        if name == 'scalebfm_act' and self.backend is not None else None)
        try:
            packet = super().dispatch(name, arguments)
        except Exception as exc:
            after_sim_s = (float(self.backend.data.time)
                           if before_sim_s is not None else None)
            advanced = before_sim_s is not None and after_sim_s > before_sim_s
            active = bool(getattr(self.backend, 'active', None))
            if name != 'scalebfm_act' or (isinstance(exc, ValueError) and not active and not advanced):
                raise
            # A request rejected after admission is not a safe validation retry.
            # End this environment while preserving the model's complete turn
            # and allowing its normal terminal skill_update.
            if active:
                self.backend.cancel()
            if advanced:
                self.actions += 1
            self.finished = True
            self.stop_reason = 'backend_execution_error'
            self.execution_error = {
                'error_type':type(exc).__name__, 'error':str(exc),
                'no_execution':not advanced, 'retryable':False,
                'admitted_command_cancelled':active,
                'sim_s_before':before_sim_s, 'sim_s_after':after_sim_s,
                'rollout_finished':True, 'stop_reason':self.stop_reason,
                'native_outcome':self.harness.evaluator.outcome(self.backend)}
            (self.rollout_root/'execution_error.json').write_text(
                json.dumps(self.execution_error,indent=2))
            print(json.dumps({'event':'execution_error',**self.execution_error}),flush=True)
            return self.execution_error | {'next_call':self.next_call()}
        self.calls += 1
        if name == 'loco_start' and self.initialization_error is not None:
            self.finished = True
            self.stop_reason = 'backend_initialization_error'
            return packet | {'next_call': self.next_call()}
        if name == 'scalebfm_act':
            self.actions += 1
            if hasattr(self.harness.evaluator, 'acknowledge_action'):
                try:
                    self.harness.evaluator.acknowledge_action(self.backend)
                except Exception as exc:
                    self.execution_error={'error_type':type(exc).__name__,'error':str(exc),
                        'no_execution':False,'action_ack_preserved':True,'retryable':False,
                        'classification':'host_evaluator_error_not_API'}
                    self.finished=True;self.stop_reason='curriculum_evaluator_error'
                    (self.rollout_root/'execution_error.json').write_text(json.dumps(self.execution_error,indent=2))
                    return packet | {'rollout_finished':True,'stop_reason':self.stop_reason,
                                     'next_call':self.next_call()}
        if self.harness:
            if name == 'loco_start':
                self.episode_start_sim_s = float(self.backend.data.time)
                if getattr(self, 'curriculum_contract', None):
                    receipt=dict(curriculum_contract=self.curriculum_contract,
                        completion_contract=self.harness.evaluator.completion_contract,
                        reset_id=self.backend.scene_setup['reset_provenance']['reset_id'],
                        evaluator=type(self.harness.evaluator).__name__,
                        initialization_manifest_is_pre_actor=True,
                        original_initialization_contract=self.backend.scene_setup.get('initialization_completion_contract'))
                    (Path(self.output)/'curriculum-binding.json').write_text(json.dumps(receipt,indent=2))
                if self.attempt_progress_config:
                    reset=packet.get('observation',{}).get('reset_id') or json.loads(self.harness.latest_path.read_text()).get('reset_id')
                    (self.output/'reset-receipt.json').write_text(json.dumps({'method':'fresh_loco_start','recorded_at':time.time(),'reset_id':reset,'env_id':self.attempt_progress_config['env_id'],'pid':os.getpid(),'physical_action_count':0},indent=2))
                self.native_start_steps = getattr(getattr(self.backend,'env',None),'step_count',None)
                if self.progress_contract:
                    from rsi.task_progress import MobileProgressSupervisor
                    from rsi.handover_progress import HANDOVER_PROGRESS, HandoverProgressSupervisor
                    supervisor=(HandoverProgressSupervisor if self.progress_contract==HANDOVER_PROGRESS else MobileProgressSupervisor)
                    self.progress_supervisor = supervisor(
                        self.backend, self.output/'progress-host', self.progress_contract)
                    self.harness.progress_supervisor = self.progress_supervisor
            native = self.harness.evaluator.outcome(self.backend)
            steps = round((float(self.backend.data.time)-self.episode_start_sim_s)/.02)
            if native in ('success', 'failure'):
                prefix = ('curriculum_' if getattr(self, 'curriculum_contract', {}).get('goal_scope') == 'curriculum_stage' else 'task_' if getattr(self.harness.evaluator,'completion_contract',None) else 'native_')
                self.stop_reason = prefix+native
            elif self.max_episode_steps is not None and steps >= self.max_episode_steps:
                self.stop_reason = 'episode_step_budget'
            if self.progress_supervisor:
                progress = self.progress_supervisor.publish(self.rollout_root/'progress.json')
                packet['progress'] = progress
                if not self.stop_reason and progress['stop_reason']:
                    self.stop_reason = progress['stop_reason']
                    (self.rollout_root/'policy_stop.json').write_text(json.dumps(progress,indent=2))
            self.finished = self.stop_reason is not None
            packet.update(native_outcome=native, rollout_finished=self.finished,
                stop_reason=self.stop_reason, step_id=steps, max_episode_steps=self.max_episode_steps,
                remaining_steps=(None if self.max_episode_steps is None else max(0, self.max_episode_steps-steps)),
                execution_profile=self.execution_profile,
                progress_checkpoint=steps//self.execution_profile['checkpoint_steps'],
                next_call=self.next_call())
            clock = public_clock(self.backend, self.episode_start_sim_s, steps,
                self.max_episode_steps, native_start=self.native_start_steps,
                declared_native_max=self.declared_native_max)
            packet['execution_clock'] = clock
            if claim is not None:
                with (self.rollout_root/'stage_progress.jsonl').open('a') as stream:
                    stream.write(json.dumps(dict(claim, actor_claim_not_host_audit=True,
                        request_id=arguments['response']['request_id'],
                        based_on_observation=arguments['observation_path'],
                        returned_observation=packet.get('observation_path'),
                        rollout_finished=self.finished))+'\n')
            from rsi.attempt_progress import record as record_progress
            record_progress(self,claim)
            if 'observation' in packet:
                packet['observation']['execution_clock'] = clock
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
                task_specification=None, skill_sources=None, protocol_registration=None,
                frozen_context=None, preflight_only=False, expected_instruction_sources=None,
                api_send=None, auxiliary_exhaustion=None, main_account=False):
    prompt = memory.skill.read_text()
    immutable = ('\nRuntime: use gpt-6-astra/xhigh. All physical actions must use the registered '
        'services. Never inspect or modify hidden evaluator state, simulator objects, runtime '
        'code or other experiment directories. Analyze only this campaign public evidence and '
        'robot geometry. Preserve original task. Use only registered public tools. After configured termination, submit skill_update using evidence '
        'from this episode, then return. Length caps are maxima, not targets: keep the main '
        'skill concise and reusable; keep lessons concise and detailed evidence in original '
        'trajectory files and references. The self-experience archive and skill versions '
        'listed in workspace.json, plus their cited public rollout evidence from this '
        'campaign, and explicitly listed transferred_self_experience public sources, '
        'are allowed inputs. Retrieve selectively: you may reuse your own '
        'successful procedure and candidate waypoints after checking current public '
        'observations and adapting as needed. Verify each action with fresh observations; '
        'independent physics resets do not require planning from scratch. Do not blindly '
        'replay or retry uncertain executed actions. The host continues the campaign. '
        'Use supplied workspace/CONTROL; read workspace.json only if absent. Current task specification and observed interface contract '
        'override obsolete interface limits in prior skills. Multiple timed waypoints '
        'are permitted only when the observation explicitly enables continuous chunks; '
        'otherwise use one waypoint and reobserve. A continuous chunk supplies references, '
        'not a promised walking primitive or successful trajectory. '
        'The current progress contract overrides historical endless-retry rules. '
        'Progress rejects unsupported actions before execution; correct them in this reset. '
        'finish_attempt follows the pinned correction/deferral contract and next_call. '
        'Task completion, safety/system faults and '
        'the registered evaluation budget remain terminal. Never interrupt inference '
        'because of its latency. Terminal skill_update '
        'saves a proposal; only central publication changes loaded skills.\n')
    if frozen_context is not None:
        start = immutable.index('The self-experience archive')
        end = immutable.index('Use supplied workspace/CONTROL;')
        immutable = immutable[:start] + (
            'Frozen candidate: read only the explicitly listed frozen public inputs '
            'and this episode public observations/notes. Cited paths outside that set '
            'are not authorized. Never read other evaluation episodes, live campaign '
            'memory, host manifests/audits, or saved revision proposals. Same-episode '
            'observation, calculation and correction remain allowed. skill_update '
            'saves an isolated proposal; it cannot change the loaded candidate. '
            'Verify actions with fresh observations; never replay uncertain actions. '
        ) + immutable[end:]
    # Reserve the additional network prompt for admission AND later skill updates.
    optional_context = context_text(memory.skill)
    ambient_sources, ambient_text = ambient_contract(memory.skill)
    if expected_instruction_sources is not None and expected_instruction_sources != ambient_sources:
        raise ValueError('Frozen ambient contract differs from the released short role entry')
    instruction_overhead = immutable + NETWORK_CONTINUATION + optional_context + ambient_text
    combined_size = validate_policy_instructions(prompt, instruction_overhead)
    memory.runtime_instructions = instruction_overhead
    instruction_budget = {'contract': 'skill-plus-runtime-v1',
        'combined_size': combined_size,
        'skill_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'runtime_sha256': hashlib.sha256(instruction_overhead.encode()).hexdigest(),
        'combined_sha256': hashlib.sha256((prompt+instruction_overhead).encode()).hexdigest(),
        'caps': {'words':831,'characters':6250,'non_whitespace':5357},
        'scope': 'SKILL + runtime + reserved continuation + complete CONTROL_CONTRACT + actual short ambient ROLE_CONTRACT; structured task data, observations and tool schemas separately pinned.',
        'ambient_instruction_sources': ambient_sources,
        'optional_context_sha256': hashlib.sha256(optional_context.encode()).hexdigest(),
        'network_continuation': NETWORK_CONTINUATION,
        'developer_instructions_sha256': hashlib.sha256((prompt+immutable).encode()).hexdigest()}
    if preflight_only:
        return instruction_budget
    from rsi.main_account import MAIN_ONLY_POLICY, LAUNCHER as MAIN_LAUNCHER
    policy=(task_specification or {}).get('actor_backend_policy')
    direct = (task_specification or {}).get('direct_api') is True
    if auxiliary_exhaustion is not None or main_account == direct:
        raise ValueError('Choose authorized main or direct API; auxiliary disabled')
    if (main_account and policy != MAIN_ONLY_POLICY) or (direct and policy != BACKEND_POLICY):
        raise ValueError('Actor route differs from pinned release')
    if direct:
        from rsi.direct_api import require_direct_policy
        require_direct_policy()
    route = 'main_chatgpt' if main_account else 'authorized_responses_api'
    launcher = MAIN_LAUNCHER if main_account else None
    exhaustion = None
    output.mkdir(parents=True, exist_ok=False)
    if protocol_registration is not None:
        (output/'protocol-registration.json').write_text(json.dumps(protocol_registration, indent=2))
    (output/'policy_instruction_budget.json').write_text(json.dumps(instruction_budget, indent=2))
    host = host_factory(output, memory, episode_id, successes)
    from rsi.curriculum import bind_host
    bind_host(host, task_specification or {})
    from rsi.native_training import enabled as native_terminal_enabled
    native_terminal = native_terminal_enabled(task_specification or {})
    host.skill_sources = skill_sources or {}
    host.required_experience_groups=(task_specification or {}).get('reset_experience',{}).get('required_selection_groups',[])
    from rsi.attempt_progress import configuration
    host.attempt_progress_config=configuration((task_specification or {}).get('env_id','unknown'),task_specification) if (task_specification or {}).get('reset_experience') else None
    host.stage_progress_required = (task_specification or {}).get('stage_progress_contract') == 'public-stages-v1'
    if not native_terminal and (task_specification or {}).get('training_scope') and (task_specification or {}).get('execution_profile',{}).get('phase')=='learning':
        host.allow_voluntary_deferral=True
        host.corrective_attempt_required=True
    progress_contract = (task_specification or {}).get('progress_contract')
    if not native_terminal and progress_contract and not (isinstance(progress_contract,dict) and 'stage_order' in progress_contract):
        from rsi.task_progress import MOBILE_ENV, MOBILE_PROGRESS
        from rsi.handover_progress import HANDOVER_PROGRESS
        from rsi.simple_handover import HANDOVER_ENVS
        admitted=((progress_contract==MOBILE_PROGRESS and task_specification.get('env_id')==MOBILE_ENV)
            or (progress_contract==HANDOVER_PROGRESS and task_specification.get('env_id') in HANDOVER_ENVS))
        if (not admitted or
                task_specification.get('execution_profile',{}).get('phase') != 'learning' or
                not host.stage_progress_required):
            raise ValueError('Progress supervision requires its exact published learning-only task contract')
        host.progress_contract = progress_contract
    host.declared_native_max = (task_specification or {}).get('native_step_contract',{}).get('registered_max_steps')
    (output/'model_backend.json').write_text(json.dumps({
        'configured_launcher': str(launcher), 'account_route': route,
        'model': 'gpt-6-astra', 'effort': 'xhigh', 'fallback': exhaustion is not None,
        'api_exhaustion': exhaustion,
        'initial_backend': route, 'codex_started': False}, indent=2))
    agent = output/'agent'; agent.mkdir()
    (agent/'scratch').mkdir()
    context = {'python': python, 'task': host.task, 'skill': str(agent/'SKILL.md'),
        'python_usage': 'Use this exact interpreter for NumPy, SciPy and PIL; do not install packages.',
        'public_evidence_root': str(host.rollout_root), 'notes': str(agent/'NOTES.md'),
        'skill_version': memory.read()['version'], 'model': 'gpt-6-astra', 'effort': 'xhigh'}
    context.update(task_specification=task_specification,
        skill_sources=host.skill_sources, require_experience_selection=host.require_selection)
    if frozen_context is not None:
        context['frozen_candidate'] = frozen_context
    context['policy_instruction_budget'] = instruction_budget
    context['camera_calibration_contract'] = (
        'Use delivered calibration.render_intrinsics fx/fy/cx/cy when present. '
        'They describe the actual delivered viewport, including off-axis and aspect '
        'effects. Pixel (u,v) has centre (u+0.5,v+0.5); camera x right, y up, -z forward. '
        'Older fovy-only depth/position estimates and empirical fits must be revalidated. '
        'Calibration is camera information, not object depth or contact truth.')
    if memory.journal.exists():
        context['self_experience_archive'] = str(memory.journal.resolve())
        context['self_skill_versions'] = str((memory.root/'versions').resolve())
    if transfer_sources:
        context['transferred_self_experience'] = list(map(str, transfer_sources))
    (agent/'workspace.json').write_text(json.dumps(context, indent=2))
    (output/'SKILL.md').write_text(prompt)
    (agent/'SKILL.md').write_text(prompt)
    if optional_context:
        (agent/'CONTROL_CONTRACT.md').write_text(optional_context)
    (agent/'ROLE_CONTRACT.md').write_text(ambient_text)
    (agent/'ambient-instructions.json').write_text(json.dumps(ambient_sources,sort_keys=True))
    pinned_public = list(transfer_sources)
    if frozen_context is not None and frozen_context.get('readable_public_root'):
        # Caller already verifies this exact public snapshot (never an episode parent).
        public_root = Path(frozen_context['readable_public_root'])
        pinned_public.extend(str(p) for p in public_root.rglob('*') if p.is_file())
    if memory.journal.exists():
        pinned_public.append(str(memory.journal))
    pinned_public.extend(str(p) for p in (memory.root/'versions').glob('*.md'))
    input_manifest = pin_actor_inputs(agent, immutable, task_specification,
        host.tool_specs(), prompt+immutable, pinned_public, ambient_sources=ambient_sources)
    (output/'actor-input-receipt.json').write_text(json.dumps(input_manifest,indent=2))
    def record_terminal(sequence, thread_id, turn, recovery_reason, reset_id):
        if '_rsi_terminal' in turn:
            raise ValueError('Reserved terminal receipt metadata collision')
        receipt = dict(turn, _rsi_terminal={'contract': TURN_RECORD_CONTRACT,
            'sequence': sequence, 'thread_id': thread_id,
            'recovery_reason': recovery_reason, 'reset_id': reset_id})
        # Exclusive creation preserves earlier evidence; partial writes fail audit.
        with (output/f'turn_{sequence:03d}.json').open('x') as stream:
            json.dump(receipt, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())

    transport = None  # API-first: no account2 thread or model is started.
    adapter = CodexPolicyAdapter(transport, host, agent,
        developer_instructions=prompt+immutable, normal_tools=True,
        terminal_callback=record_terminal,expected_instruction_sources=ambient_sources,input_manifest=input_manifest)
    started = time.monotonic(); error = None; api_continuation = None
    host._actor_caller_open = True
    try:
        if main_account:
            from rsi.main_account import run_main
            run_main(adapter, output)
        else:
            from rsi.main_account import record_feedback_intake
            record_feedback_intake(output)
            api_continuation = start_api_episode(adapter, output, task_specification,
                prompt+immutable, send=api_send)

    except Exception as exc:
        if (task_specification or {}).get('direct_api') is True:
            from rsi.direct_api import retain_live_scene
            retain_live_scene(adapter, output, exc)
        error = f'{type(exc).__name__}: {exc}'
        print(json.dumps({'event': 'episode_error', 'error': error}), flush=True)
    finally:
        host._actor_caller_open = False
        host.close()
        if transport is not None: transport.close()
    native = (host.harness.evaluator.outcome(host.backend)
              if host.harness and host.initialization_error is None else 'not_started')
    if host.initialization_error is not None and error is None:
        error = ('BackendInitializationError: '+host.initialization_error['error'])
    if host.execution_error is not None and error is None:
        error = ('BackendExecutionError: '+host.execution_error['error'])
    result = {'success': native == 'success' and error is None, 'native_outcome': native,
        'episode_id': episode_id, 'skill_updated': host.skill_updated,
        'execution_profile':getattr(host,'execution_profile',None),
        'error': error, 'stop_reason': host.stop_reason, 'model': 'gpt-6-astra', 'effort': 'xhigh',
        'backend_stop_reason':getattr(host.backend,'reason',None),
        'account_route': route, 'api_exhaustion': exhaustion,
        'api_continuation': api_continuation, 'codex_launcher': str(launcher),
        'codex_turns': adapter.turns_started, 'dynamic_tool_calls': adapter.call_index if main_account or exhaustion else (api_continuation or {}).get('tool_calls',0),
        'api_requests': (api_continuation or {}).get('api_requests',0),
        'turn_record_contract': TURN_RECORD_CONTRACT if main_account or exhaustion else 'api-terminal-sequence-v1',
        'codex_thread_id': adapter.thread_id, 'codex_turn_ids': list(adapter.turn_ids),
        'actions': host.actions, 'wall_s': time.monotonic()-started,
        'sim_s': float(host.backend.data.time)-host.episode_start_sim_s if host.backend else 0,
        'starting_skill_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'no_human_demonstration': True, 'self_experience_enabled': True,
        'human_feedback_used':bool((task_specification or {}).get('human_feedback',{}).get('used')),
        'human_demonstration_used':False,
        'protocol_registration':protocol_registration,
        'completion_contract':(task_specification or {}).get('completion_contract'),
        'progress_contract':host.progress_contract,
        'feedback_tier':(task_specification or {}).get('feedback_tier'),
        'outcome_semantics':'Configured host evaluator; raw SIMPLE rewards/flags, where available, remain in host video trace.',
        'human_feedback_sources':[{k:s[k] for k in ('path','sha256')}
            for s in (task_specification or {}).get('human_feedback',{}).get('sources',[])],
        'video': str(output/'video/episode.mp4')}
    if host.harness and host.initialization_error is None and getattr(host.harness.evaluator,'completion_contract',None):
        state=host.harness.evaluator.host_audit_state()
        result.update(completion_outcome=native,raw_native_success_seen=state['native_milestone_seen'],
            raw_native_final_flag=bool(host.backend._native_task_success),
            completion_host_state=state,
            outcome_semantics='native_outcome retains configured-evaluator legacy meaning; raw_native_* separately record original task milestone; independent audit is still required')
    curriculum = (task_specification or {}).get('curriculum_contract')
    if native_terminal:
        result['native_terminal_contract'] = task_specification['native_terminal_contract']
        result['native_terminal_event'] = state.get('native_event') if host.harness and host.initialization_error is None else None
        result['diagnostic_may_veto_success'] = False
    if curriculum:
        from rsi.curriculum import accounting
        result['curriculum_contract'] = curriculum
        result['configured_outcome'] = native
        result['curriculum_binding_receipt'] = str(output/'curriculum-binding.json')
        if curriculum['goal_scope'] == 'curriculum_stage' and native in ('success','failure'):
            result['native_outcome'] = 'curriculum_' + native
        result.update(accounting(curriculum, native == 'success' and error is None,
                                 getattr(host.backend, '_native_task_success', False)))
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
