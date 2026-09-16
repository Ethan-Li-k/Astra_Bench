"""Preserve complete episode004 and append public-only trajectory review."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent/'episode004-review'
EP=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0004'
sys.path.insert(0,str(EP.parents[1]));from actor import save
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def create(p,v):
    with p.open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def tilt(s):
    _,x,y,_=s['pelvis_world']['quaternion_wxyz'];return math.degrees(math.acos(max(-1,min(1,1-2*(x*x+y*y)))))
def yaw(p):
    w,x,y,z=p['quaternion_wxyz'];return math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))
observations=[];traces=[]
for p in sorted((EP/'rollout/episode/observations').glob('*/observation.json')):
    d=json.loads(p.read_text());c=d['command_status']
    observations.append(dict(index=p.parent.name,sim_s=d['sim_s'],source=ref(p),
        pelvis_world_m=d['pelvis_world']['position_world_m'],tilt_deg=tilt(d),pelvis_yaw_deg=yaw(d['pelvis_world']),
        foot_yaw_deg={k:yaw(d['four_point_world'][k]) for k in ('left_ankle_roll_link','right_ankle_roll_link')},
        command={k:c.get(k) for k in ('command_id','status','reference_finished','duration_s')},stop_reason=d['stop_reason']))
for p in sorted((EP/'rollout/episode').glob('motion_*/proprioception.json')):
    s=json.loads(p.read_text())['samples'];a=dict(motion=p.parent.name,source=ref(p),samples=len(s),
        duration_s=s[-1]['sim_s']-s[0]['sim_s'],max_tilt_deg=max(map(tilt,s)),
        min_pelvis_height_m=min(x['pelvis_world']['position_world_m'][2] for x in s),
        tilt_tail=[dict(sim_s=x['sim_s'],degrees=tilt(x)) for x in s[-3:]],feet={})
    for k in ('left_ankle_roll_link','right_ankle_roll_link'):
        poses=[x['four_point_world'][k]['position_world_m'] for x in s]
        a['feet'][k]=dict(delta_m=[b-a for a,b in zip(poses[0],poses[-1])],
            max_rise_m=max(x[2] for x in poses)-poses[0][2])
    traces.append(a)
manifest=[dict(**ref(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in sorted(EP.rglob('*')) if p.is_file()]
create(OUT/'original-episode-manifest.json',manifest)
ledger=ROOT/'artifacts/R020/shared-budget-ledger.json';shutil.copy2(ledger,OUT/'ledger-snapshot.json')
rows=json.loads(ledger.read_text())['requests'];calls=[]
for p in sorted((EP/'api_calls').glob('*/receipt.json')):
    d=json.loads(p.read_text());calls.append(dict(call=int(p.parent.name),state=d.get('state'),source=ref(p)))
assert len(calls)==43 and sum(x['state']=='completed' for x in calls)==42
assert calls[-1]['state']=='unknown_no_retry'
unknown={k:rows[k] for k in ('api-ground-002-call-55','api-ground-004-call-43')}
create(OUT/'host-integrity.json',dict(backend='MuJoCo',result=ref(EP/'result.json'),
    reset=ref(EP/'reset_provenance.json'),unknown_request_rows=unknown,
    ledger_snapshot=ref(OUT/'ledger-snapshot.json'),
    original_result_kind='infrastructure_error',physical_failure=False,
    diagnosis='Local HTTPS stream ended without a terminal response event. No recorded deadline; server/network cause and remote completion unknown.',
    runtime_timeout=None,automatic_retries=0,old_simulation_recoverable=False,
    recovery_reason='Actor closed its simulator after exception; no full sim/controller/in-memory Responses history checkpoint exists.'))
video=EP/'video/episode.mp4';probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height','-show_entries','format=duration,size','-of','json',str(video)]))
keyframes=[];(OUT/'keyframes').mkdir(exist_ok=False)
for obs in ('0002','0004','0011','0019'):
    for view in ('head_cam','right_wrist_cam'):
        src=EP/f'rollout/episode/observations/{obs}/{view}.png';dest=OUT/f'keyframes/{obs}-{view}.png';shutil.copy2(src,dest)
        keyframes.append(dict(source=ref(src),copy=ref(dest)))
review=dict(schema=1,episode='episode-0004',reviewed_at_unix=time.time(),owner='01a0a982-cec5-71c0-b771-091c31df61f2',
    backend='MuJoCo',classification='infrastructure_error_missing_terminal_api_response',
    original_result=ref(EP/'result.json'),original_result_modified=False,
    api_requests_started=43,api_calls_completed=42,unknown_request='api-ground-004-call-43',
    actions=19,physical_s=83.04000000001578,review_complete=True,human_question_eligible=False,
    physical_failure_increment=0,human_feedback_used=True,
    facts=['Actions2/3/4 relocated left/right/left ankles by118/101/131mm with measured rises39/44/42mm.',
           'After action4, subsequent15 actions did not establish another foot relocation despite changed posture, yaw, direction, timing and roll cues.',
           'Maximum public pelvis tilt across the episode was below14.4deg; low tilt alone did not permit more steps.',
           'Grounded heading corrections undertracked; no verified grasp/carry/placement occurred.'],
    hypotheses=['Accumulating opposing foot headings and stance-relative wrist demand may contribute to stalled support changes.',
                'Near-table wrist clearance is a visual hypothesis; retraction achieved wrist motion without restoring steps, so proximity alone is not a sufficient explanation.'],
    counterexamples=['Small low arc1 stayed grounded; larger transfer arc2 moved. Amplitude and support transfer were confounded.',
                     'Low tilt and hand withdrawal did not restore foot movement. Do not label posture recovery a recovered gait.'],
    next_distinguishing_test='In a separately authorized fresh reset, test heading preservation/correction during early measured airborne relocation before opposing headings accumulate; monitor wrist demand and actual support movement. Reject this hypothesis if early heading control also prevents clearance or later motion still stalls.',
    transfer_scope='Empty-hand original G1/DEX3/model38000/WristPI/table0 only; no validated carrying or cross-task success.',
    observations=observations,traces=traces,call_receipts=calls,keyframes=keyframes,
    video=dict(source=ref(video),probe=probe,url='/videos/api-ground-episode-0004.mp4',complete_continuous=True,
        policy_evidence=False,note='Continuous recorded physics including external diagnostic view. Policy review uses original actor cameras only.'))
create(OUT/'review.json',review)
for p in (ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',OUT.parent/'progress.json',ROOT/'api-ground-to-table/status.json'):
    snap=OUT/('before-'+p.parent.name+'-'+p.name);shutil.copy2(p,snap)
    d=json.loads(p.read_text());d.update(run_id='api-ground-004',episode='episode-0004',state='ended',terminal_kind='infrastructure_error',
        recovery_state='reviewing_transport_interruption',api_calls_completed=42,api_requests_started=43,
        actions=19,physical_s=83.04000000001578,backend='MuJoCo',actor_alive=False,inference_in_flight=False,
        owner_thread='01a0a982-cec5-71c0-b771-091c31df61f2',
        current_problem='004因API流缺少终态事件结束：42调用完成、1请求结果未知；19动作/83.04秒。后半段脚步停滞，正在复盘。',
        next_step='保留未知请求与费用，核对下一独立尝试的授权及传输诊断；不重发旧请求。',
        last_physical_update_at_unix=1789555182.3122683,updated_at_unix=time.time(),
        current_video_status='sealed_ffprobe_verified_complete',review_path=str((OUT/'review.json').relative_to(ROOT)))
    save(p,d)
create(OUT/'ACK.json',dict(ack='NO-TRUNCATION-SHARED-SKILLS-20260916 ACK',owner=review['owner'],episode='episode-0004',
    true_boundary=review['classification'],old_requests_retried=False,inflight_protected='Old actor exited; current owner resumed only after completed prior owner turn and actor exit.',
    review=ref(OUT/'review.json')))
create(OUT/'IKEA-BUDGET-PARALLEL-V1-ACK.json',dict(ack='IKEA-BUDGET-PARALLEL-V1 ACK',owner=review['owner'],
    shared_library=ref(ROOT/'tools/coordination/shared_budget.py'),integration='Already locally registered and executed schema2 batches003/004; shared source untouched.',
    adapter=ref(ROOT/'api-ground-to-table/actor-adapter/actor.py'),hook=ref(OUT.parent/'recovery_budget004.py'),
    batch=ref(ROOT/'artifacts/R021/api-ground-004/batch.json'),authorization=ref(ROOT/'api-ground-to-table/actor-adapter/authorization-004.json'),
    offline_tests=ref(OUT.parent/'episode004-preparation/batch-tests-v4.log'),
    actual_runtime=dict(completed_calls=42,unknown_call=43,fees_unknown_retained=True),
    no_price_quota_queries=True,no_legacy_receipt_changes=True,library_release_is_not_runtime_verification=True))
print(json.dumps(dict(review=str(OUT/'review.json'),completed_calls=42,unknown=43,actions=19,video_s=probe['format']['duration'],
    first_foot_yaws=[x['foot_yaw_deg'] for x in observations[:5]])))
