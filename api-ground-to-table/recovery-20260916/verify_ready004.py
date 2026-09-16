"""Read-only physical/control/budget preflight. Does not approve execution."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))
import actor
import recovery_budget004 as hook
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
auth,calls,skill=actor.validate_authorization(actor.ROOT/'authorization-004.json','api-ground-004','episode-0004',hook)
assert os.environ.get('CODEX_HOME')==str(ROOT/'codex-account-2/home')
assert os.environ.get('CODEX_THREAD_ID')=='01a0a982-cec5-71c0-b771-091c31df61f2'
assert not (actor.ROOT/'campaign/episode-0004').exists()
manifest=json.loads((actor.FROZEN/'setting_manifest.json').read_text())
for absolute,expected in manifest['episode_runtime_hashes'].items():
    p=actor.FROZEN/Path(absolute).relative_to(actor.FROZEN.parents[2])
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,str(p)
assert hashlib.sha256(Path(manifest['model_path']).read_bytes()).hexdigest()==manifest['model_sha256']
backend=actor.ROOT.parent/'original_backend.py'
assert ref(backend)['sha256']=='27ee524b00217a63de0f285bde9d2cf3ef7ba3e9ed84aea3c4812ab9a4479159'
review=json.loads((OUT/'episode003-review/review.json').read_text())
assert ref(ROOT/review['original_result']['path'])==review['original_result']
text=skill.read_text()+'\n'+actor.INSTRUCTIONS
lengths=dict(words=len(text.split()),characters=len(text),nonwhitespace=len(''.join(text.split())))
assert lengths['words']<=831 and lengths['characters']<=6250 and lengths['nonwhitespace']<=5357
v=dict(ready_offline=True,execution_approval='separate_tool_review_required',at_unix=time.time(),
    owner=os.environ['CODEX_THREAD_ID'],account_home=os.environ['CODEX_HOME'],model='gpt-6-astra',effort='xhigh',
    run='api-ground-004',episode='episode-0004',backend='MuJoCo',max_calls=calls,physics_budget_s=180,
    instruction_lengths=lengths,local_budget=hook.preflight(),quota_queries=0,requests_sent=0,
    pinned=[ref(p) for p in [actor.ROOT/'actor.py',actor.ROOT/'history_bound.py',actor.ROOT/'authorization-004.json',
        OUT/'recovery_budget004.py',OUT/'recovery_guard.py',ROOT/'artifacts/R021/api-ground-004/public-transfer.json',
        backend,skill,ROOT/'tools/coordination/shared_budget.py',OUT/'supervision/watch.py']])
path=OUT/'episode004-preparation'/f'preflight-{time.time_ns()}.json'
path.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(v,ensure_ascii=False))
