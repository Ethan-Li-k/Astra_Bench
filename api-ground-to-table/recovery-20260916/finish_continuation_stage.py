"""Read-only evidence/liveness audit, then truthful branch status publication."""
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))
sys.path.insert(0,str(OUT/'supervision'))
from actor import save
import watch
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))

manifest=json.loads((OUT/'manifest.json').read_text());changed=[]
excluded={'api-ground-to-table/status.json','api-ground-to-table/actor-adapter/auxiliary-progress.json'}
for row in manifest:
    if row['path'] in excluded or row.get('exists') is False:continue
    p=ROOT/row['path']
    if not p.is_file() or sha(p)!=row['sha256']:changed.append(row['path'])
old=json.loads((OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json').read_text())
now=json.loads((ROOT/'artifacts/R020/shared-budget-ledger.json').read_text())
old_changed=[k for k,v in old['requests'].items() if now['requests'].get(k)!=v]
review=json.loads((OUT/'episode003-review/review.json').read_text())
assert ref(ROOT/review['original_result']['path'])==review['original_result']
assert not changed and not old_changed,(changed,old_changed)
assert now['requests']['api-ground-002-call-55']['state']=='inflight'
assert (ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002/api_calls/55/receipt.json').stat().st_size==0
assert (ROOT/'artifacts/R021/api-ground-002/api-ground-002-call-55-plan.json').stat().st_size==0
public=json.loads((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_text())
ep=ROOT/'api-ground-to-table/actor-adapter/campaign'/public['episode']
reset=json.loads((ep/'reset_provenance.json').read_text())
identity=watch.identity(reset['pid'])
actor_alive=watch.process_alive(identity)
ws=json.loads((OUT/'supervision/watch-status.json').read_text())
watcher_alive=watch.process_alive(watch.identity(ws['watcher_pid']))
with (OUT/'supervision/owner.lock').open('a') as lock:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);lock_held=False
    except BlockingIOError:lock_held=True
assert watcher_alive and lock_held,'No unique live watcher'
origin=json.loads((OUT/'supervision/active-owner.json').read_text())
state=json.loads((OUT/'supervision/owner-state.json').read_text())
event=watch.event_status(Path(origin['log']))
owner_alive=any(watch.process_alive(p) for p in origin['processes'])
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
disposition=watch.decision(origin,state,event,owner_alive,watch.actor_is_alive(state,boot),set(),boot)
assert disposition=='waiting_owner_natural_exit',disposition
v=dict(at_unix=time.time(),original002_files_changed=changed,old_ledger_rows_changed=old_changed,
    call55_state='inflight_unknown_never_resent',call55_zero_byte_evidence_preserved=True,
    episode003_result_unchanged=True,episode003_review=ref(OUT/'episode003-review/review.json'),
    current_public_progress=public,current_reset=reset['reset_uuid'],actor_pid=reset['pid'],actor_alive=actor_alive,
    watcher_pid=ws['watcher_pid'],watcher_alive=watcher_alive,owner_lock_held=lock_held,
    owner_thread=watch.THREAD,supervisor_disposition=disposition,supervisor_state=state,
    budget_or_system_blocker=None,watcher_has_resumed_current_inflight_owner=False)
with (OUT/'continuation-live-verification.json').open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
for p in (OUT/'progress.json',ROOT/'api-ground-to-table/status.json'):
    snapshot=OUT/'episode004-preparation'/('before-final-'+p.name)
    if snapshot.exists():snapshot=snapshot.with_name('before-final-branch-'+p.name)
    with snapshot.open('x') as f:f.write(p.read_text())
    # A fresh projection prevents stale 003 actor_alive/review/terminal fields.
    d=dict(public,actor_alive=actor_alive,supervisor_alive=watcher_alive,supervisor_pid=ws['watcher_pid'],
        supervisor_state=disposition,supervisor_owner=watch.THREAD,administrative_updated_at_unix=time.time(),
        previous_episode='episode-0003',previous_episode_review_complete=True,
        previous_episode_review='api-ground-to-table/recovery-20260916/episode003-review/review.json',
        previous_complete_video='/videos/api-ground-episode-0003.mp4',
        infrastructure_history='api-ground-to-table/actor-adapter/recovery-history.json',
        current_reset_uuid=reset['reset_uuid'],blocker=None)
    save(p,d)
save(OUT/'episode003-review/ACK-completed.json',dict(ack='NO-TRUNCATION-SHARED-SKILLS-20260916 ACK',
    owner=watch.THREAD,review_complete=True,original_result_changed=False,
    source=ref(OUT/'episode003-review/review.json'),shared_core_changed=False,
    direct_api_network_patch_imported=False,local_completed_turn_contract_preserved=True))
sources=[ROOT/'ref/ACCOUNT2_ROLE_SKILL_REVIEW.md',ROOT/'GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md']
save(OUT/'episode004-preparation/reference-style-provenance.json',dict(sources=[ref(p) for p in sources],
    use='First GPT-as-Policy short explicit control/observe/act/verify cycle; second existing RoboRSI lifecycle/conditional retrieval review. No new roles/router architecture.',
    no_external_search=True,no_shared_publish=True))
print(json.dumps(dict(episode=public['episode'],actions=public['actions'],physical_s=public.get('physical_s'),
    api_calls_completed=public.get('api_calls_completed'),actor_pid=reset['pid'],actor_alive=actor_alive,
    watcher_pid=ws['watcher_pid'],watcher_alive=watcher_alive,lock_held=lock_held,
    originals_changed=len(changed)+len(old_changed)),ensure_ascii=False))
