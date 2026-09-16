import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));from actor import save
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
ep=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0004'
reset=json.loads((ep/'reset_provenance.json').read_text())
assert reset['reset_uuid']!='2f13f803-2de9-4e55-bf1b-5307486b2989' and reset['new_model_and_data_instance']
receipt=dict(at_unix=time.time(),actor_execution_tool_review='accepted; require_escalated tmux launch-004.sh returned exit0',
    watcher_execution_tool_review='accepted; require_escalated activate.py and supervisor tmux returned exit0',
    actor_tmux='rsi-api-ground-004-0916',watcher_tmux='rsi-ground-continuation-0916',
    reset=ref(ep/'reset_provenance.json'),authorization=ref(ROOT/'api-ground-to-table/actor-adapter/authorization-004.json'),
    launch_script=ref(OUT/'launch-004.sh'),watcher_script=ref(OUT/'supervision/watch.py'),
    approval_is_not_model_success=True,quota_queries=0,main_account_used=False)
with (OUT/'episode004-preparation/launch-receipt.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
origin=json.loads((OUT/'supervision/active-owner.json').read_text())
save(OUT/'supervision/owner-state.json',dict(status='continue',written_ns=time.time_ns(),
    owner_log=origin['log'],owner='01a0a982-cec5-71c0-b771-091c31df61f2',episode='episode-0004',
    actor_binding='api-ground-to-table/recovery-20260916/supervision/actor-004.json',
    next_boundary='Wait both current owner turn/process and actor natural termination; resume same auxiliary owner for public review and new independent authorized attempt.',
    pause_on='quota/authorization/budget/unknown-request/system ambiguity; no repeated empty boundaries'))
public=json.loads((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_text())
for path in (OUT/'progress.json',ROOT/'api-ground-to-table/status.json'):
    v=json.loads(path.read_text());v.update(public)
    v.update(current_run='api-ground-004',current_episode='episode-0004',
             supervisor='supervision/watch.py',supervisor_status='waiting_owner_natural_exit',
             previous_episode_review='episode003-review/review.json',
             previous_video='http://127.0.0.1:8765/videos/api-ground-episode-0003.mp4',
             reset_uuid=reset['reset_uuid'],state_updated_at_unix=time.time())
    # Clear stale terminal fields from the old administration snapshot.
    for k in ('terminal_kind','stop_reason','blocker'):
        if k not in public:v.pop(k,None)
    save(path,v)
p=ROOT/'human-feedback/dashboard-upgrade/owner-acks/ground.json'
v=json.loads(p.read_text());v.update(current_episode='episode-0004',current_run='api-ground-004',
    current_video=str((ep/'video/episode.mp4').relative_to(ROOT)),current_video_status='recording_not_sealed',
    latest_complete_video_url='/videos/api-ground-episode-0003.mp4',supervisor_alive=True,
    at_unix=time.time());save(p,v)
print(json.dumps(receipt))
