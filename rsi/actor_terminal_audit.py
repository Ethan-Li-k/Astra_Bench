"""Host-only cross-transport completeness; never certifies task success."""
import hashlib
import json
from pathlib import Path


def referenced(ref):
    path=Path(ref['path'])
    if not path.is_absolute():path=Path('/home/galbot/lizekai/RSI')/path
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:
        raise ValueError('Terminal evidence hash changed')
    return json.loads(raw)


def diagnostic_resume(episode, sequence, row):
    from rsi.codex_app_server import _closed_network_failure
    if not _closed_network_failure(row):
        raise ValueError('Diagnostic receipt cannot recover a non-network failure')
    path=Path(episode)/'recovery-diagnostic'/f'pause-{sequence:03d}.json'
    raw=path.read_bytes();pause=json.loads(raw)
    decision=json.loads(path.with_name(path.stem+'-consumed.json').read_text())
    meta=row['_rsi_terminal']
    if (pause.get('turn_id')!=row['id'] or pause.get('thread_id')!=meta['thread_id']
            or pause.get('reset_id')!=meta['reset_id']
            or decision.get('boundary_sha256')!=hashlib.sha256(raw).hexdigest()
            or decision.get('owner')!='01a0a867-d7aa-71f2-8547-e264d6d09ede'
            or decision.get('decision')!='resume' or decision.get('consumed') is not True
            or decision.get('actions')!=pause.get('actions')
            or decision.get('reset_id')!=meta['reset_id']):
        raise ValueError('Unconfirmed diagnostic continuation')


def complete_api_chain(result, terminal):
    from rsi.actor_quota_boundary import quota_terminal
    ref=result['api_continuation'];api=referenced(ref['result'])
    if terminal is None:
        initial=referenced(ref['initial_receipt'])
        reset=initial.get('reset_id');thread=None;turn=None
        if (initial.get('contract')!='api-first-live-host-v1' or not reset
                or initial.get('codex_turns')!=0
                or initial.get('physical_backend_unchanged') is not True
                or initial.get('actions')!=ref['start_actions']
                or api.get('initial_receipt')!=ref['initial_receipt']
                or ref.get('backend_policy')!='api-first-reviewed-responses-v1'):
            raise ValueError('Missing original API-first live-host receipt')
    else:
        reset=terminal['_rsi_terminal']['reset_id']
        thread=terminal['_rsi_terminal']['thread_id'];turn=terminal['id']
        if not quota_terminal(terminal):raise ValueError('Not a typed Codex quota terminal')
    if (not reset or ref['contract']!='same-reset-api-terminal-v1'
            or ref['reset_id']!=reset or ref['codex_turn_id']!=turn
            or ref['codex_thread_id']!=thread or api.get('reset_id')!=reset
            or api.get('codex_turn_id')!=turn or api.get('codex_thread_id')!=thread
            or api.get('contract')!=ref['contract']
            or api.get('status')!='host_finished_and_skill_recorded'
            or api.get('model')!='gpt-6-astra' or api.get('effort')!='xhigh'
            or api.get('skill_updated') is not True or api.get('host_finished') is not True
            or api.get('same_host') is not True or api.get('same_backend') is not True
            or api.get('start_actions')!=ref['start_actions']
            or api.get('end_actions')!=ref['end_actions'] or ref['end_actions']!=result['actions']):
        raise ValueError('API terminal identity/contract mismatch')
    exchanges=api.get('exchanges',[])
    if not exchanges or len(exchanges)!=api.get('new_requests'):
        raise ValueError('Missing API exchanges')
    seen=set();actions=api['start_actions'];last=None
    for number,row in enumerate(exchanges,1):
        receipt=referenced(row['receipt']);public=referenced(row['public_output'])
        if (row.get('sequence')!=number or row.get('reset_id')!=reset
                or row['receipt']['path'] in seen or row['actions_before']!=actions
                or receipt.get('state')!='completed' or receipt.get('error_type')
                or receipt.get('model')!='gpt-6-astra' or receipt.get('effort')!='xhigh'
                or receipt.get('returned_model')!='gpt-6-astra'
                or receipt.get('returned_reasoning',{}).get('effort')!='xhigh'
                or not isinstance(public,list)):
            raise ValueError('Incomplete/misordered API exchange')
        seen.add(row['receipt']['path']);after=row['actions_after']
        if type(after) is not int or after-actions not in (0,1):
            raise ValueError('API action sequence mismatch')
        if after>actions and (row.get('tool')!='scalebfm_act' or not row.get('confirmed_tool')):
            raise ValueError('Unconfirmed API action')
        calls=[x for x in public if x.get('type')=='function_call']
        if row.get('tool') is not None:
            if (len(calls)!=1 or calls[0]['name']!=row['tool'] or calls[0]['call_id']!=row['call_id']):
                raise ValueError('API tool identity mismatch')
            arguments=json.loads(calls[0]['arguments'])
            if hashlib.sha256(json.dumps(arguments,sort_keys=True).encode()).hexdigest()!=row['arguments_sha256']:
                raise ValueError('API tool arguments mismatch')
        elif calls:raise ValueError('Lost API tool record')
        actions=after;last=row
    if actions!=api['end_actions'] or last.get('tool')!='skill_update' or not last.get('confirmed_tool'):
        raise ValueError('Final API skill record incomplete')
    return True
