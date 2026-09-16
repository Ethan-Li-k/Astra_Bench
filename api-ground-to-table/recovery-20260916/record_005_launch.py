import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));from actor import save
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
ep=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0005'
reset=json.loads((ep/'reset_provenance.json').read_text())
assert reset['new_model_and_data_instance'] and reset['reset_uuid']!='7f46df1f-83f1-4343-83d3-9488934b2469'
origin=json.loads((OUT/'supervision/active-owner.json').read_text())
state_path=OUT/'supervision/owner-state.json'
with (OUT/'episode005-preparation/previous-owner-state.json').open('x') as f:f.write(state_path.read_text())
save(state_path,dict(status='continue',written_ns=time.time_ns(),owner_log=origin['log'],owner=origin['thread'],
    episode='episode-0005',actor_binding='api-ground-to-table/recovery-20260916/supervision/actor-005.json',
    next_boundary='Current owner natural completion/exit and005 actor natural end; review public evidence before independently authorized next attempt.',
    unknown_requests_never_repeat=['api-ground-002-call-55','api-ground-004-call-43']))
receipt=dict(at_unix=time.time(),execution_review='require_escalated tmux launch005 accepted; returned exit0',
    task_scope='new independent experiment, not unknown request recovery',reset=ref(ep/'reset_provenance.json'),
    authorization=ref(ROOT/'api-ground-to-table/actor-adapter/authorization-005.json'),
    launch=ref(OUT/'launch-005.sh'),backend='MuJoCo',model='gpt-6-astra',effort='xhigh',
    max_calls=120,physical_budget_s=180,actor_tmux='rsi-api-ground-005-0916',
    watcher_tmux='rsi-ground-continuation-0916',new_watcher_spawned=False,main_account_used=False,
    prior_unknown_requests_retained=True,normal_approval_does_not_confirm_old_remote_completion=True)
with (OUT/'episode005-preparation/launch-receipt.json').open('x') as f:f.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
public=json.loads((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_text())
for p in (OUT/'progress.json',ROOT/'api-ground-to-table/status.json'):
    save(p,dict(public,administrative_updated_at_unix=time.time(),
        supervisor_owner=origin['thread'],supervisor_state='resuming_existing_auxiliary_owner',
        previous_episode='episode-0004',previous_episode_review_complete=True,
        previous_episode_review='api-ground-to-table/recovery-20260916/episode004-review/review.json',
        previous_complete_video='/videos/api-ground-episode-0004.mp4',
        infrastructure_history='api-ground-to-table/actor-adapter/recovery-history.json',current_reset_uuid=reset['reset_uuid']))
p=ROOT/'human-feedback/dashboard-upgrade/owner-acks/ground.json'
with (OUT/'episode004-review/previous-ui-ACK.json').open('x') as f:f.write(p.read_text())
d=json.loads(p.read_text());d.update(current_run='api-ground-005',current_episode='episode-0005',
    current_video=str((ep/'video/episode.mp4').relative_to(ROOT)),current_video_status='recording_not_sealed',
    latest_complete_video_url='/videos/api-ground-episode-0004.mp4',
    review_path='api-ground-to-table/recovery-20260916/episode004-review/review.json',
    review_sha256=ref(OUT/'episode004-review/review.json')['sha256'],engineering_ack_only=True,
    physical_verification_of_new_human_answer=False,at_unix=time.time())
save(p,d)
print(json.dumps(dict(reset=reset['reset_uuid'],owner_log=origin['log'],next_episode='episode-0005')))
