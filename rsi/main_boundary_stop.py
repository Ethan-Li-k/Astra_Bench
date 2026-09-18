"""Honor an explicit user/manager stop after a complete dynamic-tool request."""
import json,time
from pathlib import Path

def stop_at_tool_boundary(host, tool):
    if getattr(host,'output',None) is None:return None
    request=Path(host.output)/'stop-request.json'
    if not request.is_file() or getattr(host,'finished',False):return None
    if getattr(host.backend,'active',None):
        # This is normally unreachable with the synchronous action host. Never
        # convert an unresolved command into an exception that closes transport.
        return {'stop_pending':True,'rollout_finished':False,'no_execution':True,
            'rejected_tool':tool,'next_call':None,
            'reason':'Await the existing physical command ACK; no new action is admitted.'}
    reason=json.loads(request.read_text())
    host.finished=True;host.stop_reason='user_stop_at_completed_boundary'
    receipt={'reason':host.stop_reason,'requested':reason,'applied_at':time.time(),
        'actions':host.actions,'rejected_tool':tool,'no_execution':True,
        'inference_interrupted':False,'boundary':'complete_dynamic_tool_request',
        'goal_or_evaluator_changed':False}
    (Path(host.output)/'user_stop.json').write_text(json.dumps(receipt,indent=2))
    public=host.rollout_root/'policy_stop.json';public.parent.mkdir(exist_ok=True,parents=True)
    public.write_text(json.dumps({k:v for k,v in receipt.items() if k!='requested'},indent=2))
    return dict({k:v for k,v in receipt.items() if k!='requested'},rollout_finished=True,stop_reason=host.stop_reason,
        next_call=host.next_call(),evidence_path=str(public))
