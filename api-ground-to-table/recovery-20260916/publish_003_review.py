import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));from actor import save
review=OUT/'episode003-review/review.json'
for p in [ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',OUT/'progress.json',ROOT/'api-ground-to-table/status.json']:
    d=json.loads(p.read_text());d.update(recovery_state='review_complete_preparing_independent004',
        current_problem='003安全停止已复盘：倾角15.82°升至25.005°触发原安全线；前一到位动作末段倾角仍上升。',
        next_step='准备004独立重置，检验落脚终点需求与稳定趋势；未掌握步态、未抓持。',
        review_complete=True,review_path=str(review.relative_to(ROOT)),
        current_video_status='sealed_ffprobe_verified_complete',
        review_updated_at_unix=time.time(),updated_at_unix=time.time())
    save(p,d)
p=ROOT/'human-feedback/dashboard-upgrade/owner-acks/ground.json'
shutil.copy2(p,OUT/'episode003-review/previous-ui-engineering-ACK.json')
d=json.loads(p.read_text());d.update(current_video_status='sealed_ffprobe_verified_complete',
    ack='DASHBOARD-20260916 ACK',current_episode='episode-0003',review_path=str(review.relative_to(ROOT)),
    review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),
    video_url='/videos/api-ground-episode-0003.mp4',
    last_physical_update_at_unix=1789551873.6111066,
    physical_verification_of_new_human_answer=False,engineering_ack_only=True,
    at_unix=time.time(),next_natural_boundary='Independent004 actor termination then same auxiliary owner review',
    warning_for_ui_owner='Root user confirmed current owner. Engineering ACK is not a human answer ACK or success.')
save(p,d)
with (OUT/'RECOVERY.md').open('a') as f:f.write('\n## 003复盘与004准备\n003真实safety_stop；公开倾角25.005°越过25°，高度仍0.76562米；前一target_reached末段倾角上升。原result不改，追加episode003-review/REVIEW.md及review.json。完整18.04秒录像已被网页发现。独立004新skill/auth在artifacts/R021/api-ground-004，预算/控制预检通过，执行审批另行；持续监督实现见supervision。\n')
print('003 public review and engineering ACK published; physical timestamps preserved')
