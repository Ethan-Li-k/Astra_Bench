"""Post-launch originals/old charges check; new run evidence separately recorded."""
import hashlib
import json
from pathlib import Path
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
manifest=json.loads((OUT/'manifest.json').read_text());changed=[]
excluded=['api-ground-to-table/status.json','api-ground-to-table/actor-adapter/auxiliary-progress.json']
for row in manifest:
    if row['path'] in excluded or row.get('exists') is False:continue
    p=ROOT/row['path']
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:changed.append(row['path'])
old=json.loads((OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json').read_text())
now=json.loads((ROOT/'artifacts/R020/shared-budget-ledger.json').read_text())
old_changed=[k for k,v in old['requests'].items() if now['requests'].get(k)!=v]
progress=json.loads((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_text())
v=dict(at_unix=time.time(),original_episode_batch_evidence_changed=changed,old_ledger_rows_changed=old_changed,
    mutable_status_excluded=excluded,old_call55=now['requests']['api-ground-002-call-55'],
    new_physical_progress=progress,old_receipt55_bytes=(ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002/api_calls/55/receipt.json').stat().st_size,
    old_result_still_absent=not (ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002/result.json').exists())
(OUT/'preservation-after-launch.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
assert not changed and not old_changed
print(json.dumps(dict(original_files_changed=len(changed),old_rows_changed=len(old_changed),new_physical_progress=progress),ensure_ascii=False))
