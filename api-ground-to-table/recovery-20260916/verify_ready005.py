"""Local-only integrity preflight; execution approval is separate."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));import actor
import recovery_budget005 as hook
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
auth,calls,skill=actor.validate_authorization(actor.ROOT/'authorization-005.json','api-ground-005','episode-0005',hook)
assert os.environ.get('CODEX_HOME')==str(ROOT/'codex-account-2/home')
assert os.environ.get('CODEX_THREAD_ID')=='01a0a982-cec5-71c0-b771-091c31df61f2'
assert not (actor.ROOT/'campaign/episode-0005').exists()
manifest=json.loads((actor.FROZEN/'setting_manifest.json').read_text())
for absolute,expected in manifest['episode_runtime_hashes'].items():
    p=actor.FROZEN/Path(absolute).relative_to(actor.FROZEN.parents[2])
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,str(p)
assert hashlib.sha256(Path(manifest['model_path']).read_bytes()).hexdigest()==manifest['model_sha256']
backend=actor.ROOT.parent/'original_backend.py'
assert ref(backend)['sha256']=='27ee524b00217a63de0f285bde9d2cf3ef7ba3e9ed84aea3c4812ab9a4479159'
review=json.loads((OUT/'episode004-review/review.json').read_text())
assert ref(ROOT/review['original_result']['path'])==review['original_result']
text=skill.read_text()+'\n'+actor.INSTRUCTIONS
lengths=dict(words=len(text.split()),characters=len(text),nonwhitespace=len(''.join(text.split())))
assert lengths['words']<=831 and lengths['characters']<=6250 and lengths['nonwhitespace']<=5357
local=hook.preflight()
with hook.budget.BudgetLedger().transaction() as (state,_):
    assert state['halted'] is None
    unknown={k:state['requests'][k] for k in ('api-ground-002-call-55','api-ground-004-call-43')}
    assert all(v['state']=='inflight' and v['reserved_fen']==1217 for v in unknown.values())
v=dict(ready_offline=True,execution_approval='normal_tool_review_required',at_unix=time.time(),
    owner=os.environ['CODEX_THREAD_ID'],model='gpt-6-astra',effort='xhigh',run='api-ground-005',episode='episode-0005',
    new_experiment_not_unknown_request_recovery=True,old_unknown_rows=unknown,
    backend='MuJoCo',max_calls=calls,physics_budget_s=180,instruction_lengths=lengths,local_budget=local,
    model_requests_sent=0,quota_price_queries=0,provider_status_queried=False,
    pinned=[ref(p) for p in [actor.ROOT/'actor.py',actor.ROOT/'history_bound.py',actor.ROOT/'stream_evidence.py',
        actor.ROOT/'authorization-005.json',OUT/'recovery_budget005.py',OUT/'recovery_guard.py',
        ROOT/'artifacts/R021/api-ground-005/public-transfer.json',backend,skill,ROOT/'tools/coordination/shared_budget.py',
        OUT/'supervision/watch.py']])
(OUT/'episode005-preparation'/f'preflight-{time.time_ns()}.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(ready_offline=True,execution_approval=v['execution_approval'],lengths=lengths,
    old_unknown_hold_fen={k:r['reserved_fen'] for k,r in unknown.items()},new_requests_sent=0)))
