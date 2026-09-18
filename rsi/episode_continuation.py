"""Keep an already closed network turn's live scene inside its original caller.

This is an idle diagnostic boundary, not an inference retry or new supervisor.
Only the existing SIMPLE owner can write the per-boundary decision file.
"""
import hashlib,json,os,time
from pathlib import Path

class ClosedNetworkNoProgress(RuntimeError):
    pass


def pending_diagnostic(output):
    """A retained idle scene is paused until its exact decision is consumed."""
    root=Path(output)/'recovery-diagnostic'
    for path in sorted(root.glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True):
        if path.stem.endswith(('-decision','-consumed')):continue
        try:
            row=json.loads(path.read_text());consumed=path.with_name(path.stem+'-consumed.json')
            decision=json.loads(consumed.read_text()) if consumed.exists() else {}
        except (FileNotFoundError,json.JSONDecodeError):continue
        if (decision.get('consumed') is True and decision.get('reset_id')==row.get('reset_id')
                and decision.get('actions')==row.get('actions')):continue
        if row.get('status')=='blocked_waiting_owner_diagnosis':return row
    return {}


def wait_for_network_diagnosis(adapter, output, *, wait=None, boundary_name=None, reason='closed_network_without_new_action'):
    host,backend=adapter.host,adapter.host.backend
    reset=adapter._reset_id();actions=host.actions
    def check():
        if (host is not adapter._episode_host or host.backend is not backend
                or backend is not adapter._episode_backend or not reset
                or adapter._reset_id()!=reset or reset!=adapter._episode_reset_id
                or host.actions!=actions or adapter.turn_id is not None
                or getattr(backend,'active',None) or getattr(backend,'reason',None)
                or host.finished or host.skill_updated or host.execution_error
                or host.initialization_error):
            raise RuntimeError('Diagnostic boundary no longer matches the live episode')
    check();root=Path(output)/'recovery-diagnostic';root.mkdir(exist_ok=True)
    stem=boundary_name or f'pause-{adapter.turns_started:03d}'
    if Path(stem).name!=stem:raise ValueError('Invalid boundary name')
    receipt=root/(stem+'.json');decision=root/(stem+'-decision.json')
    row=dict(status='blocked_waiting_owner_diagnosis',reason=reason,
             thread_id=adapter.thread_id,turn_id=(adapter.turn_ids[-1] if adapter.turn_ids else None),reset_id=reset,
             actions=actions,pid=os.getpid(),host_still_owned_by_original_caller=True,
             inference_or_physics_running=False,decision_path=str(decision),
             cleanup_performed=False,automatic_retry=False)
    raw=json.dumps(row,sort_keys=True).encode();key=hashlib.sha256(raw).hexdigest()
    with receipt.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    # No paid/physical polling, no inference deadline. Existing owner supplies a
    # one-use decision at a confirmed terminal boundary; every re-pause is new.
    while not decision.exists():
        check()
        (wait or time.sleep)(1.)
    check();cmd=json.loads(decision.read_text())
    if (set(cmd)!={'owner','boundary_sha256','decision'}
            or cmd['owner']!='01a0a867-d7aa-71f2-8547-e264d6d09ede'
            or cmd['boundary_sha256']!=key or cmd['decision'] not in ('resume','stop')):
        raise RuntimeError('Invalid or stale diagnostic decision; no new turn sent')
    with (root/(stem+'-consumed.json')).open('x') as f:
        json.dump(dict(cmd,consumed=True,actions=actions,reset_id=reset),f)
    if cmd['decision']=='stop':
        host.stop_reason='user_or_owner_diagnostic_stop'
        raise RuntimeError('Owner stopped the paused episode; normal cleanup follows')
    check()
    return {'resume_after_diagnosis':True,'reset_id':reset,'actions':actions}
