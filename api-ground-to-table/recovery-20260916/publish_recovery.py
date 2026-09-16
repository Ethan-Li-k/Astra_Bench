"""Update only branch-owned public progress; original episode remains untouched."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'api-ground-to-table/recovery-20260916'
owner = '01a0a982-cec5-71c0-b771-091c31df61f2'
now = time.time()
ledger = ROOT/'artifacts/R020/shared-budget-ledger.json'
dest = OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json'
dest.parent.mkdir(parents=True,exist_ok=True)
if dest.exists():
    raise SystemExit('Snapshot already exists; never overwrite')
shutil.copy2(ledger,dest)
raw = dest.read_bytes()
(OUT/'ledger-snapshot-reference.json').write_text(json.dumps({'path':str(ledger.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'snapshot':str(dest.relative_to(ROOT))},indent=2)+'\n')
progress_path = ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json'
p = json.loads(progress_path.read_text())
last = p['updated_at_unix']
p.update(state='infrastructure_error', recovery_state='recovery', updated_at_unix=now,
    last_physical_update_at_unix=last, last_progress_at_unix=last,
    inference_in_flight=False, physics_paused=None, backend='MuJoCo',
    stop_reason='host_reboot_infrastructure_interruption', recovery_owner_thread=owner,
    owner_thread=owner, previous_owner_thread='01a0a948-10bb-7d03-8f1d-b1eeda7cb93c',
    recovery_note='主机已重启，原执行进程不存在。54次完成调用、23动作/108.98物理秒为重启前最后公开记录；最新动作证据部分损坏，尚无终态。正在保全证据并核验新回合授权与费用预留；调用55结果未知，绝不重发。',
    progress_timestamp_semantics='updated_at_unix is recovery administration; last_physical_update_at_unix is the unchanged last physical progress timestamp',
    grasp_verified=False, carry_verified=False, placement_verified=False,
    current_video_status='unsealed_ffprobe_failed_moov_atom_missing',
    recovery_record='api-ground-to-table/recovery-20260916/RECOVERY.md')
def atomic(path, data):
    temp=path.with_suffix('.recovery.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    os.replace(temp,path)
atomic(progress_path,p)
s_path=ROOT/'api-ground-to-table/status.json'
s=json.loads(s_path.read_text())
s.update(phase='infrastructure_error_recovery', current_api_episode=str(ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002'),
    current_api_session=None, current_api_state=p['recovery_note'], recovery_owner_thread=owner,
    updated_at_unix=now,last_physical_update_at_unix=last,
    blocker='Recovery audit in progress; new independent episode requires fresh checked approval and shared ledger integrity',
    current_run_id='api-ground-002',current_progress=p)
atomic(s_path,s)
atomic(OUT/'progress.json',p)
print(json.dumps({'state':p['state'],'owner':owner,'last_physical_update_at_unix':last,'updated_at_unix':now,'ledger_snapshot_bytes':len(raw)},indent=2))
