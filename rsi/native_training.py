"""Native-terminal learning contract; stricter evidence remains diagnostic only."""
import copy
from functools import partial
from rsi.evaluator import SimpleNativeEvaluator

ID = 'native-terminal-learning-20260917-v1'


def contract(env_id):
    return dict(id=ID, env_id=env_id, phase='learning',
        success='original_native_task_success', extra_success_requirements=False,
        diagnostic_metrics_may_veto_success=False, applies_to='new_resets_only')


def enabled(spec):
    value = spec.get('native_terminal_contract')
    if value is None:
        return False
    if value != contract(spec.get('env_id')) or spec.get('curriculum_contract'):
        raise ValueError('Native terminal contract mismatch or competing curriculum gate')
    return True


class NativeTerminalEvaluator(SimpleNativeEvaluator):
    """Use the existing native latch, never add contact/height/dwell gates."""
    def __init__(self, binding, diagnostic_factory):
        self.binding = copy.deepcopy(binding)
        self.diagnostic_factory = diagnostic_factory
        self.completion_contract = dict(id=ID, scope=binding['env_id'],
            native_reward_unchanged=True, native_trigger_alone_terminates=True,
            unmodified_native_benchmark=False, additional_conditions=False)

    def reset(self, backend):
        super().reset(backend)
        self.reset_id = backend.scene_setup['reset_provenance']['reset_id']
        self.backend_identity = id(backend)
        self.native_seen = False
        self.native_event = None
        self.diagnostic = None
        self.diagnostic_error = None
        try:
            self.diagnostic = self.diagnostic_factory()
            self.diagnostic.reset(backend)
        except Exception as error:
            self.diagnostic_error = repr(error)
            self.diagnostic = None
        backend.placement_evaluator = self
        backend.scene_setup['previous_completion_contract'] = backend.scene_setup.get('completion_contract')
        backend.scene_setup['completion_contract'] = self.completion_contract
        backend.scene_setup['native_terminal_contract'] = self.binding

    def update(self, backend):
        if (id(backend) != self.backend_identity or
                backend.scene_setup['reset_provenance']['reset_id'] != self.reset_id):
            raise RuntimeError('Native evaluator reset changed; engineering interruption')
        native_now = bool(backend._native_task_success)
        self.native_seen |= native_now
        if self.native_seen:
            self._outcome = 'success'
        else:
            super().update(backend)
        if self.diagnostic:
            try:
                self.diagnostic.update(backend)
            except Exception as error:
                self.diagnostic_error = repr(error)
                self.diagnostic = None
        if native_now and self.native_event is None:
            status = copy.deepcopy(backend.status())
            self.native_event = dict(reset_id=self.reset_id, sim_s=float(backend.data.time),
                command_id=status.get('command_id'), command_status=status.get('status'),
                backend_reason=backend.reason, original_native_success=True)
            # A native terminal ends this new-mode physical rollout immediately.
            # Preserve its real control status, then cancel any remaining knots.
            backend.cancel()
            command = status.get('command_id')
            if command in backend.commands:
                backend.commands[command]['status_before_native_terminal'] = status.get('status')
                backend.commands[command]['status'] = 'cancelled_after_native_success'
            self.native_event['remaining_reference_cancelled'] = backend.active is None

    def host_audit_state(self):
        diagnostic = None
        if self.diagnostic and hasattr(self.diagnostic, 'host_audit_state'):
            try:
                diagnostic = self.diagnostic.host_audit_state()
            except Exception as error:
                self.diagnostic_error = repr(error)
        return dict(contract=ID, reset_id=self.reset_id, outcome=self._outcome,
            native_milestone_seen=self.native_seen, diagnostic=diagnostic,
            native_event=self.native_event, diagnostic_error=self.diagnostic_error, diagnostic_may_veto=False)


def bind_host(host, spec):
    if not enabled(spec):
        return
    if host.backend is not None or spec.get('execution_profile', {}).get('phase') != 'learning':
        raise ValueError('Native learning contract requires a fresh learning reset')
    host.evaluator_factory = partial(NativeTerminalEvaluator,
        spec['native_terminal_contract'], host.evaluator_factory)
    host.task = spec['instruction']
    host.native_terminal_contract = copy.deepcopy(spec['native_terminal_contract'])
    # A meaningful attempt can be deferred at an acknowledged idle boundary;
    # no compulsory extra correction or hidden contact proof is required.
    host.allow_voluntary_deferral = True
    host.corrective_attempt_required = False
