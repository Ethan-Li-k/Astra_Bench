"""Published schema2 ledger, with a stricter frozen legacy-row integrity check."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
from recovery_guard import validate_frozen_prior
CORE=ROOT/'tools/coordination/shared_budget.py'
if hashlib.sha256(CORE.read_bytes()).hexdigest()!='9008e224d3161ecd952cdc507cf10aa344d5ecd7582be5fd57c19a20efe8551e':
    raise ValueError('Shared budget changed; review required')
spec=importlib.util.spec_from_file_location('ground005_empirical_private',ROOT/'api-ground-to-table/empirical_hook.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
budget=base.budget
reference=base.reference
BATCH=ROOT/'artifacts/R021/api-ground-005/batch.json'
PIN='22d819915958ca765027dc1887ebe058e689cead26800f2af3b4c78cebbb8568'
BATCH_REF={'path':str(BATCH.relative_to(ROOT)),'sha256':PIN}
b=budget.reviewed_batch(BATCH_REF)
SNAPSHOT=budget.load(budget.evidence(b['recovery_ledger_snapshot']))
for key in ('interruption_audit','direct_user_instruction','reviewed_plan','skill'):
    budget.evidence(b[key])
PRIOR004=budget.load(budget.evidence(b['prior_ledger_snapshot']))
INTERRUPTION004=budget.load(budget.evidence(b['interruption004']))
OriginalLedger=budget.BudgetLedger

class RecoveryLedger(OriginalLedger):
    @contextmanager
    def transaction(self,initialize=False):
        with super().transaction(initialize=initialize) as (state,policy):
            subset=dict(state,requests={k:v for k,v in state['requests'].items() if k in SNAPSHOT['requests']})
            try:validate_frozen_prior(subset,SNAPSHOT,ROOT)
            except ValueError as e:raise budget.BudgetError(str(e)) from e
            key='api-ground-004-call-43'
            budget.require(state['requests'].get(key)==PRIOR004['requests'][key], 'Unknown004 request changed; review required')
            result004=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0004/result.json'
            budget.require(reference(result004)==INTERRUPTION004['result'], 'Original004 result changed')
            budget.evidence(PRIOR004['requests'][key]['completion_evidence'])
            approval=budget.parallel_approval(b)
            for key,row in state['requests'].items():
                if key in SNAPSHOT['requests'] or row.get('batch')==BATCH_REF:continue
                budget.require(budget.parallel_pending_allowed(row,b,approval),'Unapproved foreign request')
            yield state,policy

# Private import only; shared file, legacy rows and other processes unchanged.
budget.BudgetLedger=RecoveryLedger
base.REGISTERED={'api-ground-005':BATCH.parent}
route=base.route
reserve=base.reserve
settle=base.settle

def preflight():
    with budget.BudgetLedger().transaction() as (state,_):
        spent,held=budget.totals(state)
        budget.require(spent+held<state['terms']['cap_fen'],'Shared cap exhausted')
    return dict(old_holds_retained=61,spent_fen=spent,held_fen=held,new_requests_sent=0)
