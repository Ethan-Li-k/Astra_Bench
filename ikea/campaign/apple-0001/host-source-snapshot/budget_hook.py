"""IKEA new-run registration; all accounting uses the unique shared library/ledger."""
import importlib.util
import json
from pathlib import Path

ROOT=Path('/home/galbot/lizekai/RSI')
spec=importlib.util.spec_from_file_location('ikea_shared_budget',ROOT/'tools/coordination/shared_budget.py')
budget=importlib.util.module_from_spec(spec);spec.loader.exec_module(budget)

def reference(path):
    path=Path(path).resolve()
    return {'path':str(path.relative_to(ROOT)),'sha256':budget.sha(path)}

class RegisteredBudget:
    def __init__(self,registration):
        self.registration=Path(registration).resolve()
        reg=budget.load(self.registration)
        budget.require(reg['status']=='validated_metadata_only','Registration incomplete')
        self.batch_ref=reg['batch'];self.batch=budget.reviewed_batch(self.batch_ref)
        budget.require(self.batch['branch']=='ikea','IKEA branch required')
        self.out=budget.evidence(self.batch_ref).parent
        self.budget=budget
    def reserve(self,meta):
        batch=budget.reviewed_batch(self.batch_ref)
        budget.require(meta['run_id']==batch['batch_id'],'Run does not match registered batch')
        for key in ('provider','model'):budget.require(meta[key]==batch[key],'Mismatch: '+key)
        budget.require(meta['effort']=='xhigh' and batch['new_observation_data_authorized'],'Scope/effort mismatch')
        index=budget.integer(meta['call_index'],'call index',1)
        size=budget.integer(meta['input_bytes'],'input bytes',1);tokens=budget.integer(meta['max_output_tokens'],'output tokens',1)
        budget.require(index<=batch['max_calls'] and size<=batch['max_payload_bytes'] and tokens<=batch['max_output_tokens'],'Batch limit')
        request_id=f"{batch['batch_id']}-call-{index:02d}"
        plan=dict(schema=1,mode='empirical_estimate',authorization=batch['authorization'],provider=meta['provider'],
            model=meta['model'],reasoning_effort='xhigh',pricing_verified=False,hard_cost_bound=False,
            request_id=request_id,calibration_request_id=batch['calibration_request_id'],
            scope=dict(role='planner-actor',environment='isolated-IKEA-MuJoCo-original-apple-convex-018kg-v1',branch='ikea'),
            payload_sha256=meta['request_sha256'],max_payload_bytes=size,max_output_tokens=tokens,
            calibration_input_bytes=batch['calibration_input_bytes'],calibration_output_tokens=batch['calibration_output_tokens'],
            margin_multiplier=batch['margin_multiplier'],max_calls=1,automatic_retries=False,batch=self.batch_ref,call_index=index)
        path=self.out/f'{request_id}-plan.json'
        with path.open('x') as f:json.dump(plan,f,indent=2)
        ledger=budget.BudgetLedger();row=ledger.reserve_empirical(reference(path));begun=ledger.begin_empirical(request_id,meta['request_sha256'])
        budget.require(begun['transitioned'],'Already dispatched or uncertain; no retry')
        return dict(request_id=request_id,run_id=meta['run_id'],batch=self.batch_ref,reserved_fen=row['reserved_fen'],
            basis='empirical_estimate_not_a_hard_cost_bound')
    def settle(self,reservation,receipt):
        request_id=reservation['request_id']
        budget.require(reservation['batch']==self.batch_ref and receipt['run_id']==self.batch['batch_id'],'Completion route mismatch')
        public={k:receipt[k] for k in ('state','status','http_status','response_id','request_id','provider_request_id','usage',
            'model','returned_model','reasoning_effort','started_at','finished_at','error_type') if k in receipt}
        public.update(ledger_request_id=request_id,actual_cny_fen=None,cost_status='unknown_retained_in_shared_reservation_no_quota_query')
        path=self.out/f'{request_id}-completion.json'
        with path.open('x') as f:json.dump(public,f,indent=2)
        with budget.BudgetLedger().transaction() as (state,_):
            row=state['requests'][request_id]
            budget.require(row['state']=='inflight' and row.get('batch')==self.batch_ref,'Matching inflight completion required')
            row['completion_evidence']=reference(path)
        return dict(actual_cny_fen=None,reservation_retained=True)
