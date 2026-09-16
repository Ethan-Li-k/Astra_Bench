"""Host liveness and immutable prior evidence, no network/API operations."""
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));from actor import save
sys.path.insert(0,str(OUT/'supervision'));import watch
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
changed=[]
for file in (OUT/'manifest.json',OUT/'episode004-review/original-episode-manifest.json'):
    for row in json.loads(file.read_text()):
        if row['path'] in ('api-ground-to-table/status.json','api-ground-to-table/actor-adapter/auxiliary-progress.json') or row.get('exists') is False:continue
        p=ROOT/row['path']
        if not p.is_file() or ref(p)['sha256']!=row['sha256']:changed.append(row['path'])
assert not changed,changed
old=json.loads((OUT/'episode004-review/ledger-snapshot.json').read_text())
now=json.loads((ROOT/'artifacts/R020/shared-budget-ledger.json').read_text())
old_changed=[k for k,v in old['requests'].items() if k.startswith('api-ground-') and now['requests'].get(k)!=v]
assert not old_changed,old_changed
for key in ('api-ground-002-call-55','api-ground-004-call-43'):
    assert now['requests'][key]['state']=='inflight' and now['requests'][key]['reserved_fen']==1217
assert (ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002/api_calls/55/receipt.json').stat().st_size==0
assert (ROOT/'artifacts/R021/api-ground-002/api-ground-002-call-55-plan.json').stat().st_size==0
origin=json.loads((OUT/'supervision/active-owner.json').read_text())
state=json.loads((OUT/'supervision/owner-state.json').read_text())
ws=json.loads((OUT/'supervision/watch-status.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert state['owner_log']==origin['log'] and state['written_ns']>=origin['started_ns'] and state['episode']=='episode-0005'
assert origin['thread']==watch.THREAD and origin['boot_id']==boot
assert watch.process_alive(watch.identity(ws['watcher_pid']))
with (OUT/'supervision/owner.lock').open('a') as lock:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locked=False
    except BlockingIOError:locked=True
assert locked
assert watch.actor_is_alive(state,boot)
owner_alive=any(watch.process_alive(x) for x in origin['processes']);assert owner_alive
ep=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0005'
reset=json.loads((ep/'reset_provenance.json').read_text());actor_identity=watch.identity(reset['pid'])
assert watch.process_alive(actor_identity)
command=Path(f"/proc/{reset['pid']}/cmdline").read_bytes()
assert b'actor.py' in command and b'episode-0005' in command
public=json.loads((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_text())
first=json.loads((ep/'api_calls/01/receipt.json').read_text())
assert first['state']=='completed' and first['transport']['stream_evidence']['terminal_event_seen']
v=dict(at_unix=time.time(),owner=watch.THREAD,boot_id=boot,owner_alive=owner_alive,
    actor_identity=actor_identity,actor_alive=True,watcher_pid=ws['watcher_pid'],watcher_alive=True,owner_lock_held=True,
    origin=origin,owner_state=state,public_progress=public,reset=ref(ep/'reset_provenance.json'),
    completed_stream_evidence=ref(ep/'api_calls/01/receipt.json'),
    original002_004_files_changed=changed,old_ground_rows_changed=old_changed,
    unknown_requests_retained=['api-ground-002-call-55','api-ground-004-call-43'],
    old004_runtime_log=ref(OUT/'run-004.log'),current_blocker=None,
    next_boundary='Both engineering turn/process and005 actor natural exit, followed by same auxiliary owner review.')
with (OUT/'episode005-preparation/live-verification.json').open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
for p in (OUT/'progress.json',ROOT/'api-ground-to-table/status.json'):
    save(p,dict(public,administrative_updated_at_unix=time.time(),actor_alive=True,supervisor_alive=True,
        supervisor_pid=ws['watcher_pid'],supervisor_owner=watch.THREAD,supervisor_state='current_owner_active_then_wait005',
        previous_episode='episode-0004',previous_episode_review_complete=True,
        previous_episode_review='api-ground-to-table/recovery-20260916/episode004-review/review.json',
        previous_complete_video='/videos/api-ground-episode-0004.mp4',current_reset_uuid=reset['reset_uuid'],blocker=None))
ack=dict(ack='IKEA-BUDGET-PARALLEL-V1 ACK',owner=watch.THREAD,at_unix=time.time(),
    shared_library=ref(ROOT/'tools/coordination/shared_budget.py'),scope_branch='api-ground-to-table',
    integration='schema2 registered, offline validated and direct API runtime observed in003/004/005',
    current_hook=ref(OUT/'recovery_budget005.py'),current_batch=ref(ROOT/'artifacts/R021/api-ground-005/batch.json'),
    current_authorization=ref(ROOT/'api-ground-to-table/actor-adapter/authorization-005.json'),
    actual_runtime_receipt=ref(ep/'api_calls/01/receipt.json'),
    library_publication_not_equated_with_runtime=True,actual_fees_unknown_holds_retained=True,
    unknown_requests_never_retried=['api-ground-002-call-55','api-ground-004-call-43'],
    quota_price_queries=0,old_ledger_rows_changed=False)
with (OUT/'BUDGET-ACK-005.json').open('x') as f:f.write(json.dumps(ack,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(episode=public['episode'],completed=public.get('api_calls_completed'),actions=public['actions'],
    physical_s=public.get('physical_s'),actor_pid=reset['pid'],watcher_pid=ws['watcher_pid'],old_changes=0),ensure_ascii=False))
