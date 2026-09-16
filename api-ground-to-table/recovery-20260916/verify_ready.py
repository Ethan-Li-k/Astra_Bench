"""Pre-launch integrity, no model requests or simulator initialization."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))
import actor
import recovery_budget
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
auth,calls,skill=actor.validate_authorization(actor.ROOT/'authorization-003.json','api-ground-003','episode-0003',recovery_budget)
account=os.environ.get('CODEX_HOME')
assert account==str(ROOT/'codex-account-2/home')
assert os.environ.get('CODEX_THREAD_ID')=='01a0a982-cec5-71c0-b771-091c31df61f2'
assert not (actor.ROOT/'campaign/episode-0003').exists()
frozen=actor.FROZEN
manifest=json.loads((frozen/'setting_manifest.json').read_text())
for absolute,expected in manifest['episode_runtime_hashes'].items():
    p=frozen/Path(absolute).relative_to(frozen.parents[2])
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,str(p)
assert hashlib.sha256(Path(manifest['model_path']).read_bytes()).hexdigest()==manifest['model_sha256']
source=actor.ROOT.parent/'original_backend.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='27ee524b00217a63de0f285bde9d2cf3ef7ba3e9ed84aea3c4812ab9a4479159'
text=skill.read_text()+'\n'+actor.INSTRUCTIONS
result=dict(ready_offline=True,execution_approval='pending',at_unix=time.time(),owner=os.environ['CODEX_THREAD_ID'],
    account_home=account,model='gpt-6-astra',reasoning_effort='xhigh',new_episode=True,
    backend='MuJoCo',same_old_episode_restored=False,physical_budget_s=180,max_calls=calls,
    instruction_lengths=dict(words=len(text.split()),characters=len(text),nonwhitespace=len(''.join(text.split()))),
    local_budget=recovery_budget.preflight(),
    pinned=[ref(p) for p in [actor.ROOT/'actor.py',actor.ROOT/'history_bound.py',actor.ROOT/'authorization-003.json',
        OUT/'recovery_budget.py',OUT/'recovery_guard.py',OUT/'public-transfer.json',source,skill,ROOT/'tools/coordination/shared_budget.py']],
    baseline_ledger_sha256=hashlib.sha256((ROOT/'artifacts/R020/shared-budget-ledger.json').read_bytes()).hexdigest(),
    paid_requests_sent=0,quota_queries=0,credentials_read_by_review=False)
(OUT/'ready-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
