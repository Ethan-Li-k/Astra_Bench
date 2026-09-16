"""Reproduce old-contract recovery rejection without ledger mutation."""
import importlib.util
import json
from pathlib import Path
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=ROOT/'api-ground-to-table/recovery-20260916'
spec=importlib.util.spec_from_file_location('old_budget',ROOT/'tools/coordination/shared_budget.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
state=json.loads((OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json').read_text())
prior=ROOT/'artifacts/R021/api-ground-002/batch.json'
refs=[dict(request_id=k,completion_evidence=v.get('completion_evidence')) for k,v in state['requests'].items() if k.startswith('api-ground-002-call-')]
results={}
for name,fn in [('partial_batch_as_completed',lambda:b.allowed_prior_holds(state,{'prior_completed_batches':[{'batch':{'path':str(prior.relative_to(ROOT)),'sha256':b.sha(prior)},'completed_requests':refs}]})),
                ('unknown55_as_completed',lambda:b.completed_hold(state['requests']['api-ground-002-call-55'],None)),
                ('unknown55_original_plan_integrity',lambda:b.evidence(state['requests']['api-ground-002-call-55']['inputs']['estimate_plan']))]:
    try:fn();results[name]={'rejected':False}
    except b.BudgetError as e:results[name]={'rejected':True,'reason':str(e)}
assert all(x['rejected'] for x in results.values())
(OUT/'boundary-reproduction.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
