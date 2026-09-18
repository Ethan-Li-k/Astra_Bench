"""Learning-only objective/evaluator binding, separate from native benchmark."""
import copy
import hashlib
import json
from functools import partial
from pathlib import Path

import numpy as np
from rsi.curriculum_retained import RetainedCurriculumGate
from rsi.simple_grasp_mp import RetainedGraspEvaluator

SPEC = Path('/home/galbot/lizekai/RSI/skills/curricula/curriculum-20260917-v1-0950b635108d0beb.json')
SPEC_SHA256 = '0950b635108d0beb42da631a90c7692177e34138f9e2f86ce1cee490f1e0a889'
UIDS = {
    'simple/G1WholebodyTabletopGraspVariant1MP-v0': 'g1_wholebody_tabletop_grasp_variant1_mp',
    'simple/G1WholebodyBendPickSimToRealTeleop-v0': 'g1_wholebody_bend_pick_sim_to_real_teleop',
    'simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0': 'g1_wholebody_handover_place_back_sim_to_real_teleop',
}


def contract(env_id, level_id):
    raw = SPEC.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SPEC_SHA256:
        raise ValueError('Immutable published curriculum source changed')
    source = json.loads(raw)
    task = next(t for t in source['tasks'] if t['env_id'] == env_id)
    level = copy.deepcopy(next(l for l in task['levels'] if l['level'] == level_id))
    handover_kind = {'C1': 'ordered_handover', 'C2': 'ordered_handover_place'}
    exact_handover = (env_id == 'simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0'
                      and handover_kind.get(level_id) == level['kind'])
    if env_id not in UIDS or (level['kind'] != 'retained_lift' and not exact_handover):
        raise ValueError('This curriculum stage awaits its exact physical sampler/guard')
    instruction = level['instruction_template'].format(target=task['target'], **level)
    return dict(id=source['id'], spec_sha256=hashlib.sha256(raw).hexdigest(),
                env_id=env_id, level=level_id, instruction=instruction, criteria=level,
                goal_scope='full_task' if level['counts_as_full_task'] else 'curriculum_stage',
                official_evaluation=False)


def verify_contract(binding):
    if binding != contract(binding['env_id'], binding['level']):
        raise ValueError('Actor/host curriculum spec or selected level differs')


class CurriculumRetainedEvaluator(RetainedGraspEvaluator):
    def __init__(self, binding):
        verify_contract(binding)
        self.binding = copy.deepcopy(binding)
        self.env_id = binding['env_id']; self.task_uid = UIDS[self.env_id]
        self.completion_contract = dict(id=binding['id']+'-'+binding['level'],
            scope=self.env_id, curriculum_contract=self.binding,
            native_reward_unchanged=True, unmodified_native_benchmark=False)

    def reset(self, backend):
        super().reset(backend)
        if self.binding['criteria']['kind'] == 'ordered_handover':
            from rsi.curriculum_handover import HandoverC1Gate
            self.gate = HandoverC1Gate(self._reset_id, self.binding)
        elif self.binding['criteria']['kind'] == 'ordered_handover_place':
            from rsi.curriculum_handover_place import HandoverC2Gate
            self.gate = HandoverC2Gate(self._reset_id, self.binding)
        else:self.gate = RetainedCurriculumGate(self.binding['criteria'])
        self._gate_progress = None
        self._acknowledging = False
        backend.scene_setup['initialization_completion_contract'] = backend.scene_setup.get('completion_contract')
        backend.scene_setup['completion_contract'] = self.completion_contract
        backend.scene_setup['curriculum_contract'] = self.binding

    def sample(self, backend):
        sample = super().sample(backend)
        # Reuse the actual backend's 0.55m/25deg fall envelope and failure flag.
        body = int(backend.model.body('pelvis').id)
        height = float(backend.data.xpos[body, 2])
        native_mp = getattr(backend, 'control_configuration', {}).get('controller') == 'native-mp-amo15-arm-ik-stationary-v1'
        if native_mp:
            height -= float(backend.ground)
        tilt = float(np.degrees(np.arccos(np.clip(backend.data.xmat[body].reshape(3, 3)[2, 2], -1, 1))))
        finite = np.isfinite(backend.data.qpos).all() and np.isfinite(backend.data.qvel).all()
        sample.update(reset_id=self._reset_id,
            standing_ok=bool(finite and not backend.reason and height >= .55 and tilt <= 25.),
            command_complete=bool(self._acknowledging and not backend.active
                and backend.status().get('status') in ('target_reached', 'gripper_duration_elapsed', 'timed_out', 'ik_blocked')))
        return sample

    def update(self, backend):
        if id(backend) != self._backend_identity or backend.scene_setup['reset_provenance']['reset_id'] != self._reset_id:
            self._host_error = 'backend_or_reset_changed'
            raise RuntimeError('Curriculum host identity changed; no task-failure credit')
        self.update_sample(self.sample(backend), backend.reason)

    def update_sample(self, sample, reason=None):
        self._last_sample = dict(sample)
        status = self.gate.update(sample)
        if hasattr(status, 'host_dict'):
            self._gate_progress=status.host_dict();status=status.status.value
        if status == 'unavailable':
            # Missing host signals are an engineering error, never a grasp failure.
            raise RuntimeError('Curriculum host signal unavailable: ' + str(getattr(self.gate,'reason',None) or getattr(self.gate,'error',None)))
        self._outcome = ('failure' if reason else
            'success' if status == 'curriculum_success' else 'in_progress')

    def acknowledge_action(self, backend):
        self._acknowledging = True
        try:
            self.update(backend)
        finally:
            self._acknowledging = False

    def host_audit_state(self):
        return dict(contract=self.completion_contract['id'], curriculum_contract=self.binding,
            sample=self._last_sample, native_milestone_seen=self.gate.native_seen,
            hold_since=getattr(self.gate,'since',None), acquire_action=getattr(self.gate,'acquire_action',None),
            outcome=self._outcome, curriculum_status=(getattr(self,'_gate_progress',None) or {}).get('status',getattr(self.gate,'status',None)), curriculum_progress=getattr(self,'_gate_progress',None),
            reset_id=self._reset_id, error=self._host_error or getattr(self.gate,'reason',None) or getattr(self.gate,'error',None))


def bind_host(host, task_spec):
    from rsi.native_training import enabled, bind_host as bind_native
    if enabled(task_spec):
        return bind_native(host, task_spec)
    binding = task_spec.get('curriculum_contract')
    if binding is None:
        return
    verify_contract(binding)
    if task_spec.get('execution_profile', {}).get('phase') != 'learning':
        raise ValueError('Curriculum cannot change official evaluation settings')
    if host.backend is not None:
        raise ValueError('Curriculum only binds before a fresh reset')
    # Every verified learning curriculum needs a bounded correction/deferral path.
    host.allow_voluntary_deferral = True
    host.corrective_attempt_required = True
    host.task = binding['instruction']
    host.evaluator_factory = partial(CurriculumRetainedEvaluator, binding)
    host.curriculum_contract = copy.deepcopy(binding)


def accounting(binding, host_success, native_flag):
    verify_contract(binding)
    return dict(success=bool(host_success and binding['criteria']['counts_as_full_task']),
                configured_goal_success=bool(host_success),
                goal_scope=binding['goal_scope'], curriculum_level=binding['level'],
                curriculum_spec_sha256=binding['spec_sha256'],
                curriculum_success=bool(host_success),
                full_task_success=bool(host_success and binding['criteria']['counts_as_full_task']),
                official_success=False, raw_native_final_flag=bool(native_flag))
