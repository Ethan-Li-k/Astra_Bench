"""Same-caller quota handoff; no reset, automatic approval or request replay."""
import hashlib
import json
import time
from pathlib import Path

from rsi.actor_inputs import verify_actor_inputs
from rsi.same_reset_api import SameResetAPI, digest

BACKEND_POLICY = 'api-first-reviewed-responses-v1'
LEGACY_BACKEND_POLICY = 'account2-closed-quota-to-reviewed-responses-v1'


def continue_after_quota(adapter, output, specification, instructions, *, wait=None,
                         batch_factory=None, send=None, initial=False):
    host = adapter.host
    reset, actions = adapter._reset_id(), host.actions
    if (specification or {}).get('actor_backend_policy') != (BACKEND_POLICY if initial else LEGACY_BACKEND_POLICY):
        raise RuntimeError('API backend not registered in this episode contract')
    def check():
        verify_actor_inputs(adapter.input_manifest, adapter.developer_instructions)
        if (not getattr(host, '_actor_caller_open', False) or not reset
                or adapter.turn_id is not None or host is not adapter._episode_host
                or host.backend is not adapter._episode_backend
                or adapter._reset_id() != reset or reset != adapter._episode_reset_id
                or host.actions != actions or host.finished or host.skill_updated
                or host.execution_error or host.initialization_error
                or getattr(host.backend, 'active', None) or getattr(host.backend, 'reason', None)):
            raise RuntimeError('Quota boundary cannot retain the original live scene')
    check()
    output = Path(output)
    terminal = output / ('api-initial-host.json' if initial else f'turn_{adapter.turns_started:03d}.json')
    project=Path('/home/galbot/lizekai/RSI')
    reference = lambda p: {'path': str(p.resolve().relative_to(project)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    if initial:
        with terminal.open('x') as stream:
            json.dump(dict(contract='api-first-live-host-v1',reset_id=reset,actions=actions,
                codex_turns=0,physical_backend_unchanged=True,
                input_manifest_sha256=hashlib.sha256((adapter.workspace/'input-manifest.json').read_bytes()).hexdigest()),stream,indent=2)
    required = dict(operation_kind='same_reset_api_transport',owner='01a0a867-d7aa-71f2-8547-e264d6d09ede', reset_id=reset,
        env_id=specification['env_id'], model='gpt-6-astra', effort='xhigh',
        backend_policy=(BACKEND_POLICY if initial else LEGACY_BACKEND_POLICY), api_tool_contract_sha256=digest(SameResetAPI.build_specs(host)),
        instruction_sha256=hashlib.sha256(instructions.encode()).hexdigest(),
        sources=[dict(path=str(Path(p).relative_to(project)),sha256=s) for p,s in sorted(adapter.input_manifest['files'].items())])
    if specification.get('direct_api') is True:
        required['direct_api']=True
        required['owner']=json.loads((project/'artifacts/six-transfer-20260917/execution/run-plan.json').read_text())['id']
    binding_path = output/'api-continuation-binding.json'
    request = dict(status='waiting_normal_execution_review', required_binding=required,
        quota_receipt=(None if initial else reference(terminal)), initial_receipt=(reference(terminal) if initial else None), same_host=True, same_backend=True,
        actions=actions, binding_path=str(binding_path), no_request_sent=True,
        stop_path=str(output/'api-continuation-stop.json'))
    with (output/'api-continuation-required.json').open('x') as stream:
        json.dump(request,stream,indent=2)
    if initial and specification.get('direct_api') is True:
        from rsi.direct_api import authorize_direct_binding
        binding=authorize_direct_binding(required)
        from rsi.actor_transport import atomic
        if binding_path.exists():raise ValueError('Existing binding must not be replaced')
        atomic(binding_path,binding)
    # The original caller owns the idle scene. No new watcher/model/API request.
    # The existing supervisor obtains normal execution approval for this exact
    # binding and supplies its hash-bound receipt; this code never approves it.
    while not binding_path.exists():
        check()
        if (output/'api-continuation-stop.json').exists():
            host.stop_reason='user_or_owner_api_handoff_stop'
            raise RuntimeError('Explicit stop at quota handoff; normal cleanup follows')
        (wait or time.sleep)(1.)
    check();binding=json.loads(binding_path.read_text())
    if {k:v for k,v in binding.items() if k not in ('execution_approval','user_authorization')} != required:
        raise ValueError('Reviewed API binding must equal the required live input contract')
    if batch_factory is None:
        if binding.get('direct_api') is True:
            from rsi.direct_api import DirectActorBatches
            batch_factory=DirectActorBatches(binding)
        else:
            from rsi.actor_budget import RegisteredActorBatches
            batch_factory=RegisteredActorBatches(binding)
    # Initial API input includes only the pinned public workspace, current public
    # observation and same-episode notes. Audit/budget/management data stay host-side.
    agent=adapter.workspace
    observation=Path(host.harness.latest_path)
    packet={'workspace':json.loads((agent/'workspace.json').read_text()),
            'observation':json.loads(observation.read_text()),
            'observation_path':str(observation),'next_call':host.next_call(),
            'public_input_paths':[str(agent/name) for name in ('workspace.json','task_specification.json','CONTROL_CONTRACT.md') if str(agent/name) in adapter.input_manifest['files']]}
    packet['workspace'].pop('transferred_self_experience',None)
    packet['workspace'].pop('public_evidence_root',None)
    control=agent/'CONTROL_CONTRACT.md'
    if str(control) in adapter.input_manifest['files']:packet['control_contract']=control.read_text()
    notes=agent/'NOTES.md'
    if notes.is_file() and not notes.is_symlink():packet['same_episode_notes']=notes.read_text()
    api=SameResetAPI(adapter,output/'api-continuation',quota_receipt=(None if initial else reference(terminal)),initial_receipt=(reference(terminal) if initial else None),
        binding=binding,initial_public_packet=packet,instructions=instructions,
        batch_factory=batch_factory,send=send)
    result=api.run()
    return dict(contract='same-reset-api-terminal-v1', result=dict(path=str(api.out/'result.json'),sha256=hashlib.sha256((api.out/'result.json').read_bytes()).hexdigest()),
        reset_id=reset, codex_thread_id=adapter.thread_id, codex_turn_id=(adapter.turn_ids[-1] if adapter.turn_ids else None),initial_receipt=(reference(terminal) if initial else None),
        start_actions=actions,end_actions=host.actions,api_requests=result['new_requests'],tool_calls=result['tool_calls'],backend_policy=(BACKEND_POLICY if initial else LEGACY_BACKEND_POLICY))


def start_api_episode(adapter, output, specification, instructions, **kwargs):
    """SIMPLE's single admitted new reset, then API; no Codex thread/model call."""
    from rsi.actor_inputs import verify_actor_inputs
    verify_actor_inputs(adapter.input_manifest,adapter.developer_instructions)
    if specification.get('actor_backend_policy')!=BACKEND_POLICY:
        raise ValueError('New actor must use the published API-first policy')
    if adapter.host.backend is not None or adapter.host.harness is not None:
        raise ValueError('New episode initializer is once-only; never reset a live host')
    call=adapter.host.next_call()
    if call.get('tool')!='loco_start':raise ValueError('Expected exactly one initial reset')
    adapter.host.dispatch('loco_start',{k:v for k,v in call.items() if k!='tool'})
    if adapter.host.initialization_error or adapter.host.finished:
        raise RuntimeError('Initialization terminal; no model request dispatched')
    adapter._episode_backend=adapter.host.backend;adapter._episode_reset_id=adapter._reset_id()
    return continue_after_quota(adapter,output,specification,instructions,initial=True,**kwargs)
