"""Production schema2 actor batch factory; registration itself sends no request."""
import json,time
from pathlib import Path
from rsi.actor_transport import BudgetHook,modules,ref,ROOT,MODEL,EFFORT
from rsi.actor_transport import atomic
from goal_guard import read_evidence,TASKS

class ActorBudget(BudgetHook):
    def reserve(self,meta):
        b=self.b;batch=b.reviewed_batch(self.batch_ref)
        b.require(meta['run_id']==batch['batch_id'] and meta['model']==MODEL and meta['effort']==EFFORT,'actor run/model/effort')
        b.require(meta['provider']==batch['provider'] and batch['new_observation_data_authorized'],'actor provider/public scope')
        index=b.integer(meta['call_index'],'call_index',1);size=b.integer(meta['input_bytes'],'input_bytes',1)
        tokens=b.integer(meta['max_output_tokens'],'max_output_tokens',1)
        b.require(index<=batch['max_calls'] and size<=batch['max_payload_bytes'] and tokens<=batch['max_output_tokens'],'actor batch bounds')
        request=f"{batch['batch_id']}-call-{index:02d}"
        plan=dict(schema=1,mode='empirical_estimate',authorization=batch['authorization'],provider=meta['provider'],model=MODEL,
            reasoning_effort=EFFORT,pricing_verified=False,hard_cost_bound=False,request_id=request,
            calibration_request_id=batch['calibration_request_id'],scope=dict(role='planner-actor',environment=batch['actor_env_id'],branch='simple'),
            payload_sha256=meta['request_sha256'],max_payload_bytes=size,max_output_tokens=tokens,
            calibration_input_bytes=batch['calibration_input_bytes'],calibration_output_tokens=batch['calibration_output_tokens'],
            margin_multiplier=batch['margin_multiplier'],max_calls=1,automatic_retries=False,batch=self.batch_ref,call_index=index)
        path=self.path/(request+'-plan.json')
        with path.open('x') as stream:json.dump(plan,stream,indent=2)
        row=b.BudgetLedger().reserve_empirical(ref(path));begun=b.BudgetLedger().begin_empirical(request,meta['request_sha256'])
        b.require(begun['transitioned'],'unknown actor request never retried')
        return dict(request_id=request,batch=self.batch_ref,reserved_fen=row['reserved_fen'])

class RegisteredActorBatches:
    def __init__(self,binding):
        self.binding=binding
        if binding.get('env_id') not in TASKS:raise ValueError('exact_six_task_actor_scope_required')
        _,self.budget,self.registration=modules()

    def __call__(self,reset,output):
        binding=self.binding
        if reset!=binding['reset_id']:raise ValueError('batch_cannot_change_reset')
        from rsi.same_reset_api import digest
        approved=read_evidence(binding['execution_approval'])
        from operation_review import verify_execution_review
        verify_execution_review(approved,{k:v for k,v in binding.items() if k!='execution_approval'})
        for source in binding['sources']:read_evidence(source,json_document=False)
        run='api-simple-actor-'+str(time.time_ns());path=Path(output)/run;path.mkdir(exist_ok=False)
        terms=json.loads((ROOT/'ikea/budget-coordination/batch-terms.example.json').read_text());terms.pop('example_only')
        terms.update(batch_id=run,branch='simple',purpose='Reviewed SIMPLE actor transport within the preregistered live reset',
            actor_env_id=binding['env_id'],actor_reset_id=reset,actor_binding_sha256=digest(binding),
            latest_user_authority=ref(ROOT/'ref/USER_UPDATE_20260916_PSI0_GOAL_API_FALLBACK.md'),
            authorization='Existing explicit RSI continuation authority; schema review is distinct from normal tool approval')
        retained=[ref(ROOT/f'artifacts/R021/api-ground-00{i}/batch.json') for i in (1,2)]
        atomic(path/'approval.json',self.registration.bind(terms,retained))
        terms['approval']=ref(path/'approval.json');atomic(path/'batch.json',terms)
        reference=ref(path/'batch.json');self.budget.reviewed_batch(reference)
        atomic(path/'registration.json',dict(status='validated_metadata_only',batch=reference,ledger_mutated=False,dispatched=False))
        return run,path,ActorBudget(self.budget,reference)
