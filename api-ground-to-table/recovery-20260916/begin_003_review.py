"""Snapshot branch status and publish an accurate post-episode review state."""
import hashlib
import json
from pathlib import Path
import shutil
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent/'episode003-review'
OUT.mkdir(exist_ok=False)
EP=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0003'
for path in [ROOT/'api-ground-to-table/status.json',ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',OUT.parent/'progress.json']:
    dest=OUT/'before-status'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
r=json.loads((EP/'result.json').read_text())
last=EP/'rollout/episode/observations/0005/observation.json'
p=dict(run_id='api-ground-003',episode='episode-0003',state='ended',terminal_kind='safety_stop',
    recovery_state='reviewing_safety_stop',recovery_note='003已安全停止；正在复盘并准备不同假设的下一独立尝试，当前无物理actor。',
    api_calls_completed=r['api_calls'],api_calls=r['api_calls'],actions=r['actions'],physical_s=r['physical_s'],
    updated_at_unix=time.time(),last_physical_update_at_unix=last.stat().st_mtime,
    physics_paused=None,inference_in_flight=False,actor_alive=False,backend='MuJoCo',
    owner_thread='01a0a982-cec5-71c0-b771-091c31df61f2',
    current_video_status='sealed_ffprobe_review_pending',grasp_verified=False,carry_verified=False,placement_verified=False,
    human_question_eligible=False,result_path=str(EP/'result.json'))
def save(path,v):
    tmp=path.with_suffix('.review.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
save(ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',p)
save(OUT.parent/'progress.json',p)
s_path=ROOT/'api-ground-to-table/status.json';s=json.loads(s_path.read_text());s.update(phase='episode003_safety_stop_review',current_api_session=None,current_api_state=p['recovery_note'],current_progress=p,updated_at_unix=p['updated_at_unix'],blocker=None)
save(s_path,s)
save(OUT/'ACK.json',dict(ack='NO-TRUNCATION-SHARED-SKILLS-20260916 ACK',owner=p['owner_thread'],run_id=p['run_id'],episode=p['episode'],stop_class='safety_stop_not_inference_timeout',inflight_turn_protected='no actor turn remains',original_result_sha256=hashlib.sha256((EP/'result.json').read_bytes()).hexdigest(),review_in_progress=True))
print(json.dumps(p,ensure_ascii=False))
