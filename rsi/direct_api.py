"""Direct authorized API requests with identity receipts, without billing gates."""
import hashlib
import json
import time
from pathlib import Path
from rsi.actor_transport import ROOT, MODEL, EFFORT, atomic, transport_only


def retain_live_scene(adapter, output, error, *, wait=time.sleep):
    """Service interruption is a paused original scene, never a task failure."""
    host=adapter.host;backend=host.backend;reset=adapter._reset_id()
    if (backend is None or not reset or host.finished or host.execution_error or host.stop_reason
            or host.initialization_error or getattr(backend,'active',None)
            or getattr(backend,'reason',None)):
        return
    output=Path(output)
    dispatched=list((output/'api-continuation').glob('**/receipt.json'))
    if not dispatched:
        atomic(output/'api-pre-dispatch-error.json',dict(status='local_validation_failed_before_request',
            error_type=type(error).__name__,error=str(error),reset_id=reset,actions=host.actions,
            no_request_sent=True,complete_attempt=False))
        return
    path=output/'api-service-paused.json'
    atomic(path,dict(status='service_paused_live_scene_retained',error_type=type(error).__name__,
        error=str(error),request_boundary='inspect persisted API request receipts; never automatic retry',
        reset_id=reset,actions=host.actions,model=MODEL,effort=EFFORT,
        native_failure=False,automatic_POST_retry=False,inference_deadline=None,
        next_step='Resolve the exact recorded service/request boundary before resuming; other environments continue.'))
    # Background requests already recover their original handles automatically.
    # Here no recoverable handle was returned to the caller. Retain the original
    # owner and physics; never synthesize a failed physical episode or replay it.
    while True:
        if host.backend is not backend or adapter._reset_id()!=reset:
            raise RuntimeError('Retained scene identity changed')
        wait(5)


class DirectSession:
    def __init__(self, output, registration, send, run_id, *, max_calls=6):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=False)
        self.send,self.run_id=send,run_id
        self.count,self.completed_count,self.stopped=0,0,False
        self.max_calls=max_calls

    def call(self,payload):
        from rsi.api_use import require_api_enabled
        require_api_enabled()
        if self.stopped or self.count>=self.max_calls:raise ValueError('Closed request sequence')
        if (payload.get('model')!=MODEL or payload.get('reasoning')!={'effort':EFFORT}
                or payload.get('store') is not False or payload.get('stream') is not True
                or 'max_output_tokens' in payload):
            raise ValueError('Direct Astra/xhigh must not impose a local output-token cutoff')
        transport=transport_only();body=transport.encoded(payload)
        self.count+=1;folder=self.output/f'{self.count:02d}';folder.mkdir(exist_ok=False)
        receipt=dict(run_id=self.run_id,call_index=self.count,request_sha256=hashlib.sha256(body).hexdigest(),
            input_bytes=len(body),model=MODEL,effort=EFFORT,state='dispatched',started_at_unix=time.time(),
            inference_deadline=None,local_output_token_cutoff=None,automatic_POST_retries=0,
            financial_gating=False,private_reasoning_exported=False)
        atomic(folder/'receipt.json',receipt)
        try:
            response=self.send(payload)
            receipt.update(response_id=response.get('id'),usage=response.get('usage'),
                returned_model=response.get('model'),returned_reasoning=response.get('reasoning'),
                state=response.get('status','unknown'),transport=response.get('_transport',{}))
            receipt.update(response.get('_transport',{}))
            atomic(folder/'public_output.json',transport.public_response(response))
            if (response.get('status')!='completed' or response.get('model')!=MODEL
                    or response.get('reasoning',{}).get('effort')!=EFFORT):
                raise RuntimeError('Response not complete or model changed; no partial action')
            self.completed_count+=1
            return response
        except BaseException as error:
            self.stopped=True
            if receipt['state']=='dispatched':receipt['state']='unknown_no_retry'
            receipt['error_type']=type(error).__name__
            raise
        finally:
            receipt['finished_at_unix']=time.time()
            receipt.update(started_at=receipt['started_at_unix'],finished_at=receipt['finished_at_unix'],reasoning_effort=EFFORT)
            atomic(folder/'receipt.json',receipt)


class DirectActorBatches:
    session_type=DirectSession
    direct_requests=True
    def __init__(self,binding):
        self.binding=binding
        if binding.get('user_authorization'):
            verify_direct_binding(binding)
        else:
            from goal_guard import TASKS
            if binding.get('env_id') not in TASKS or binding.get('direct_api') is not True:
                raise ValueError('Registered direct API binding required')

    def __call__(self,reset,output):
        from rsi.actor_inputs import read_evidence
        binding=self.binding
        if reset!=binding['reset_id']:raise ValueError('Cannot change live reset')
        if binding.get('user_authorization'):
            verify_direct_binding(binding)
        else:
            from operation_review import verify_execution_review
            verify_execution_review(read_evidence(binding['execution_approval']),
                {k:v for k,v in binding.items() if k!='execution_approval'})
        for source in binding['sources']:read_evidence(source,json_document=False)
        run='api-simple-actor-'+str(time.time_ns());folder=Path(output)/run;folder.mkdir(exist_ok=False)
        self.batch=dict(batch_id=run,branch='simple',model=MODEL,reasoning_effort=EFFORT,max_calls=120,
            contract='direct-api-no-billing-gates-v1',reset_id=reset,financial_gating=False)
        atomic(folder/'registration.json',self.batch)
        return run,folder,self


def require_direct_policy():
    from rsi.api_use import require_api_enabled
    require_api_enabled()
    policy=json.loads((ROOT/'ref/tasks/account-policy.json').read_text())
    if (policy.get('api_enabled') is not True or policy.get('auxiliary_accounts_allowed') is not False
            or policy.get('model') != MODEL or policy.get('effort') != EFFORT):
        raise ValueError('Latest user policy does not authorize this API route')
    return policy


def authorize_direct_binding(required):
    """User-authorized run; bind reset/input before one POST, no per-reset watcher."""
    require_direct_policy()
    plan=ROOT/'artifacts/six-transfer-20260917/execution/run-plan.json'
    authority={'path':str(plan.relative_to(ROOT)),'sha256':hashlib.sha256(plan.read_bytes()).hexdigest()}
    binding=dict(required,user_authorization=authority)
    verify_direct_binding(binding)
    return binding


def verify_direct_binding(binding):
    require_direct_policy()
    from rsi.actor_inputs import read_evidence
    plan=read_evidence(binding['user_authorization'])
    from rsi.training_gate import require_training
    require_training(binding.get('env_id'))
    registered={r['id'] for r in json.loads((ROOT/'artifacts/R019/task-inventory.json').read_text())['entries']}
    if (not plan or binding.get('env_id') not in registered or binding.get('direct_api') is not True
            or binding.get('model') != MODEL or binding.get('effort') != EFFORT
            or not binding.get('reset_id') or not binding.get('instruction_sha256')
            or binding.get('owner')!=plan.get('id')):
        raise ValueError('Direct API requires the authorized plan and exact registered live inputs')
