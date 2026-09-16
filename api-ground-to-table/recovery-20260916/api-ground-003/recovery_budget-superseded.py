"""One new reviewed batch; original shared implementation and old rows unchanged."""
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
if hashlib.sha256(CORE.read_bytes()).hexdigest()!='69eca474738b9bf749570e5f265f02077552ced7f28e806232e6283b1745fa4c':
    raise ValueError('Shared budget changed; review required')
spec=importlib.util.spec_from_file_location('ground003_empirical_private',ROOT/'api-ground-to-table/empirical_hook.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
budget=base.budget
reference=base.reference
OLD_REVIEW=budget.reviewed_batch
OLD_PRIOR=budget.allowed_prior_holds
BATCH=OUT/'api-ground-003/batch.json'
PIN='b0b30c2d69de55b534aaba638fb2f0b0598509fefe13c33fd98a389b54b50d24'
BATCH_REF={'path':str(BATCH.relative_to(ROOT)),'sha256':PIN}

def reviewed_batch(ref):
    if ref!=BATCH_REF:return OLD_REVIEW(ref)
    b=budget.load(budget.evidence(ref))
    a=budget.load(budget.evidence(b['approval']))
    budget.evidence(a['direct_user_instruction_file']);budget.evidence(a['reviewed_plan'])
    budget.evidence(b['skill']);budget.evidence(b['recovery_ledger_snapshot'])
    audit=budget.load(budget.evidence(b['interruption_audit']))
    budget.require(a['approved'] is True and a['approval_kind']=='current_user_task_scope'
        and a['prior_episode_approval_reused'] is False and a['single_independent_episode'] is True,
        'Fresh independent task authorization required')
    for k,v in b.items():
        if k!='approval':budget.require(a.get(k)==v,'New approval mismatch: '+k)
    budget.require(b['batch_id']=='api-ground-003' and b['episode']=='episode-0003'
        and b['max_calls']==120 and b['max_episode_steps']==9000 and b['physical_budget_s']==180
        and b['provider']=='https://llm-gateway.galbot.com' and b['model']=='gpt-6-astra'
        and b['reasoning_effort']=='xhigh' and b['automatic_retries'] is False
        and b['max_payload_bytes']==2_000_000 and b['max_output_tokens']==16384,
        'Recovery scope changed')
    budget.require(audit['stop_reason']=='host_reboot_infrastructure_interruption'
        and audit['same_episode_restorable'] is False and audit['interrupted_unknown_request']['replay_allowed'] is False,
        'Missing interruption evidence')
    return b

def allowed_prior_holds(state,batch):
    if batch.get('batch_id')!='api-ground-003':return OLD_PRIOR(state,batch)
    budget.require(batch==reviewed_batch(BATCH_REF),'Unpinned recovery batch')
    snapshot=budget.load(budget.evidence(batch['recovery_ledger_snapshot']))
    try:return validate_frozen_prior(state,snapshot,ROOT,new_batch_ref=BATCH_REF)
    except ValueError as e:raise budget.BudgetError(str(e)) from e

# Private imported module only. Shared file and other processes remain unchanged.
budget.reviewed_batch=reviewed_batch
budget.allowed_prior_holds=allowed_prior_holds
base.REGISTERED={'api-ground-003':BATCH.parent}
route=base.route
reserve=base.reserve
settle=base.settle

def preflight():
    b=reviewed_batch(BATCH_REF)
    with budget.BudgetLedger().transaction() as (state,_):
        ids=allowed_prior_holds(state,b)
        spent,held=budget.totals(state)
        budget.require(spent+held<state['terms']['cap_fen'],'Shared cap exhausted')
    return dict(old_holds_retained=len(ids),spent_fen=spent,held_fen=held,new_requests_sent=0)
