"""Append episode005 public review; preserve original results and all requests."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path('/home/galbot/lizekai/RSI')
OUT=Path(__file__).resolve().parent/'episode005-review'
EP=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0005'
sys.path.insert(0,str(EP.parents[1]))
from actor import save

def ref(p):
    return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def create(p,v):
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def tilt(s):
    _,x,y,_=s['pelvis_world']['quaternion_wxyz']
    return math.degrees(math.acos(max(-1,min(1,1-2*(x*x+y*y)))))
def yaw(p):
    w,x,y,z=p['quaternion_wxyz']
    return math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))

result=json.loads((EP/'result.json').read_text())
assert result['terminal_kind']=='infrastructure_error' and result['actions']==4
assert result['api_calls_completed']==9 and result['api_requests_started']==10
assert result['native_outcome']=='in_progress' and not result['physical_failure']
create(OUT/'original-episode-manifest.json',[
    dict(**ref(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)
    for p in sorted(EP.rglob('*')) if p.is_file()])
ledger=ROOT/'artifacts/R020/shared-budget-ledger.json'
shutil.copy2(ledger,OUT/'ledger-snapshot.json')
rows=json.loads((OUT/'ledger-snapshot.json').read_text())['requests']
unknown=[f'api-ground-{batch}-call-{call}' for batch,call in [('002',55),('004',43),('005',10)]]
for key in unknown:
    assert rows[key]['state']=='inflight' and rows[key]['reserved_fen']==1217
calls=[]
for p in sorted((EP/'api_calls').glob('*/receipt.json')):
    d=json.loads(p.read_text());calls.append(dict(call=int(p.parent.name),state=d['state'],source=ref(p)))
assert len(calls)==10 and sum(x['state']=='completed' for x in calls)==9
assert calls[-1]['state']=='unknown_no_retry'
log=OUT.parent/'run-005.log'
assert 'RuntimeError: HTTP 429; no retry; expense unknown' in log.read_text()
create(OUT/'host-integrity.json',dict(result=ref(EP/'result.json'),reset=ref(EP/'reset_provenance.json'),
    runtime_log=ref(log),ledger_snapshot=ref(OUT/'ledger-snapshot.json'),
    unknown_request_rows={k:rows[k] for k in unknown},http_status_evidence=429,
    response_body_recorded=False,quota_or_rate_cause='unknown',automatic_retries=0,
    old_simulation_recoverable=False,reason='Actor closed simulator; no complete controller/simulator/in-memory history checkpoint.',
    privileged_object_or_contact_data_used=False))
observations=[];traces=[];actions=[]
for p in sorted((EP/'rollout/episode/observations').glob('*/observation.json')):
    d=json.loads(p.read_text());c=d['command_status']
    observations.append(dict(index=p.parent.name,sim_s=d['sim_s'],source=ref(p),
        pelvis_world_m=d['pelvis_world']['position_world_m'],tilt_deg=tilt(d),
        foot_yaw_deg={k:yaw(d['four_point_world'][k]) for k in ('left_ankle_roll_link','right_ankle_roll_link')},
        command={k:c.get(k) for k in ('command_id','status','reference_finished')},stop_reason=d['stop_reason']))
for p in sorted((EP/'rollout/episode').glob('motion_*/proprioception.json')):
    s=json.loads(p.read_text())['samples']
    a=dict(motion=p.parent.name,source=ref(p),samples=len(s),duration_s=s[-1]['sim_s']-s[0]['sim_s'],
        max_tilt_deg=max(map(tilt,s)),min_pelvis_height_m=min(x['pelvis_world']['position_world_m'][2] for x in s),
        tilt_tail=[dict(sim_s=x['sim_s'],degrees=tilt(x)) for x in s[-3:]],feet={})
    for k in ('left_ankle_roll_link','right_ankle_roll_link'):
        poses=[x['four_point_world'][k]['position_world_m'] for x in s]
        a['feet'][k]=dict(delta_m=[b-a for a,b in zip(poses[0],poses[-1])],max_rise_m=max(x[2] for x in poses)-poses[0][2])
    traces.append(a)
for p in sorted((EP/'rollout/episode').glob('execution_*.json')):
    d=json.loads(p.read_text());ack=d['final_status']
    actions.append(dict(source=ref(p),response_reason=d['response'].get('reason'),
        command_id=ack['command_id'],status=ack['status'],reference_finished=ack['reference_finished'],
        target=ack['approved_target'],position_error_m=ack['actual_position_error_m_by_link'],
        rotation_error_rad=ack['actual_rotation_error_rad_by_link']))
video=EP/'video/episode.mp4'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height',
    '-show_entries','format=duration,size','-of','json',str(video)]))
keyframes=[];(OUT/'keyframes').mkdir()
for obs in ('0000','0002','0003','0004'):
    for view in ('head_cam','right_wrist_cam'):
        src=EP/f'rollout/episode/observations/{obs}/{view}.png';dst=OUT/f'keyframes/{obs}-{view}.png'
        shutil.copy2(src,dst);keyframes.append(dict(source=ref(src),copy=ref(dst)))
review=dict(schema=1,episode='episode-0005',reviewed_at_unix=time.time(),owner='01a0a982-cec5-71c0-b771-091c31df61f2',
    backend='MuJoCo',classification='infrastructure_error_http429_no_automatic_retry',
    original_result=ref(EP/'result.json'),original_result_modified=False,review_complete=True,
    api_requests_started=10,api_calls_completed=9,unknown_request='api-ground-005-call-10',
    actions=4,physical_s=result['physical_s'],human_question_eligible=False,physical_failure_increment=0,
    human_feedback_used=result['human_feedback_used'],new_human_feedback_physical_validation=False,
    facts=['The first heading-constrained arc moved the left ankle only1.4mm, with3.8mm peak rise.',
           'Actions2/3/4 relocated left/right/left ankles165/152/140mm, with24/44/27mm peak rises.',
           'During action4 the nominal right support ankle moved32mm backward and21mm sideways; support stationarity is not established.',
           'All four ACKs timed_out with reference_finished=true; reference completion is not target arrival or stable gait.',
           'Final left/right ankle yaw was approximately-12.1/+1.1deg; left target yaw correction undertracked.',
           'Maximum public pelvis tilt was13.345deg; original safety stop did not trigger.',
           'Original head RGB still shows the red cube on the floor; grasp/carry/placement has not been established.'],
    hypotheses=['Early heading management may limit opposing yaw accumulation, but this truncated rollout cannot establish that it prevents later stalls.',
                'Forward arc geometry/support transfer and wrist demand affect relocation; heading alone is not isolated.'],
    counterexamples=['The first attempt to preserve heading did not produce useful clearance.',
                     'Smaller final yaw than004 coincided with different wrist and arc commands; cross-episode outcome is not a controlled causal test.',
                     'Low endpoint tilt and swing-foot advance coexisted with support retreat and wrist tracking error.'],
    next_distinguishing_test='Only after the gateway restriction is verifiably resolved and a fresh reset is authorized: test whether early heading preservation remains compatible with measured clearance and stationary support over additional alternating transfers, comparing measured support displacement and settling tilt tails. Change one justified planning condition; do not replay unknown calls/actions.',
    test_status='not executed; real gateway blocker; no episode006',
    transfer_scope='Conditional empty-hand original G1/DEX3/model38000/WristPI/table0 evidence; no learned gait or carrying claim.',
    observations=observations,traces=traces,action_acks=actions,call_receipts=calls,keyframes=keyframes,
    video=dict(source=ref(video),probe=probe,url='/videos/api-ground-episode-0005.mp4',complete_continuous=True,
        policy_evidence=False,note='Real continuous physics recording includes diagnostic view; public policy review uses original actor cameras and named robot state only.'))
create(OUT/'review.json',review)
create(OUT/'experience-v005.json',dict(id='ground005-heading-and-support-retreat-v1',status='conditional_candidate',
    source=ref(OUT/'review.json'),skill_used=ref(EP/'SKILL.md'),public_transfer_used=ref(EP/'public-transfer.json'),
    hypotheses=review['hypotheses'],counterexamples=review['counterexamples'],next_test=review['next_distinguishing_test'],
    limits=review['transfer_scope'],promotion=False,new_skill_published=False))
create(OUT/'ACK.json',dict(ack='NO-TRUNCATION-SHARED-SKILLS-20260916 ACK',owner=review['owner'],
    run='api-ground-005',episode='episode-0005',true_boundary=review['classification'],
    review=ref(OUT/'review.json'),inflight_actor=False,new_requests_authorized=False,unknown_requests_never_repeat=unknown))
for p in (ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',OUT.parent/'progress.json',ROOT/'api-ground-to-table/status.json'):
    d=json.loads(p.read_text());d.update(review_path=str((OUT/'review.json').relative_to(ROOT)),
        review_complete=True,review_original_result_unchanged=True,review_document=str((OUT/'REVIEW.md').relative_to(ROOT)),
        current_video_url=review['video']['url'],recovery_note='005第10请求HTTP429，远端结果/费用未知；自动接续暂停，未创建006。',
        supervisor_state='owner_review_active_then_blocked_no_automatic_resume',updated_at_unix=time.time())
    save(p,d)
ackp=ROOT/'human-feedback/dashboard-upgrade/owner-acks/ground.json'
shutil.copy2(ackp,OUT/'previous-ui-engineering-ACK.json')
ack=json.loads(ackp.read_text());ack.update(current_video_status='sealed_ffprobe_verified_complete',
    current_episode='episode-0005',video_url=review['video']['url'],latest_complete_video_url=review['video']['url'],
    review_path=str((OUT/'review.json').relative_to(ROOT)),review_sha256=ref(OUT/'review.json')['sha256'],
    last_physical_update_at_unix=d['last_physical_update_at_unix'],at_unix=time.time(),inflight_protected=False,
    inflight_note='Actor exited; unknown request receipts retained, never retried.',
    next_natural_boundary='005 ended; owner reports blocked HTTP429. Existing watcher waits current engineering exit then blocks automatic resume.',
    blocker='gateway_http_429',engineering_ack_only=True,physical_verification_of_new_human_answer=False)
save(ackp,ack)
print(json.dumps(dict(review=str(OUT/'review.json'),actions=4,completed=9,video_s=probe['format']['duration'],blocker='gateway_http_429')))
