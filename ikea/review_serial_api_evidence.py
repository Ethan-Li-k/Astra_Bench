"""Read-only integrity audit of completed serial API batches; no billing query."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path):return [json.loads(s) for s in Path(path).read_text().splitlines()]


def check_series(series,receipts,runs,batches,transitions):
    """Pure structural check; file/approval integrity is checked separately."""
    seen=[];counts={};sequential=True
    for index,(row,receipt) in enumerate(zip(series,receipts),1):
        run=row['run_id']
        if run not in counts:seen.append(run);counts[run]=0
        counts[run]+=1
        sequential &= (row['global_call']==index and row['batch_call']==counts[run]
            and receipt['run_id']==run and receipt['call_index']==counts[run]
            and run==seen[-1])
    complete=all(r.get('state')=='completed' and r.get('http_status')==200
        and r.get('returned_model')=='gpt-6-astra'
        and r.get('returned_reasoning',{}).get('effort')=='xhigh'
        and r.get('finished_at_unix') is not None for r in receipts)
    allowance=all(0<counts.get(run,0)<=batches[run]['max_calls'] for run in runs)
    before_exhausted=all(counts.get(run)==batches[run]['max_calls'] for run in runs[:-1])
    bridges=len(transitions)==max(0,len(runs)-1)
    for index,item in enumerate(transitions):
        if index+1>=len(runs):bridges=False;break
        old,new=runs[index:index+2]
        bridges &= (item['previous_run']==old and item['new_run']==new
            and item['previous_call']==counts.get(old) and item['same_reset'] is True
            and item['physics_advanced'] is False and item['request_sent'] is False
            and item['old_unknown_fees_retained'] is True)
    return dict(serial_global_index=sequential and len(series)==len(receipts),
        ordered_unique_batches=seen==runs and len(runs)==len(set(runs)),
        complete_model_calls=complete and bool(receipts),
        exact_batch_allowances=allowance and before_exhausted,
        verified_same_reset_transitions=bridges)


def audit(ep,result):
    ep=Path(ep).resolve();runs=result['api_runs']
    series=rows(ep/'api-call-series.jsonl')
    transitions=rows(ep/'serial-batch-transitions.jsonl') if (ep/'serial-batch-transitions.jsonl').exists() else []
    receipts=[];batches={};file_binding=True;scope_binding=True;paths=[]
    # Reuse the authoritative registration validator read-only, never instantiate a ledger.
    spec=importlib.util.spec_from_file_location('review_only_shared_budget',ROOT.parent/'tools/coordination/shared_budget.py')
    budget=importlib.util.module_from_spec(spec);spec.loader.exec_module(budget)
    for run in runs:
        folder=ep/'api-batches'/run
        terms=read(folder/'batch-terms.json')
        registration=ROOT/'budget-coordination/approvals'/run/'registration.json'
        reg=read(registration);batch=budget.reviewed_batch(reg['batch']);batches[run]=batch
        scope_binding &= (reg['status']=='validated_metadata_only' and batch['batch_id']==run
            and batch['episode']==ep.name and Path(batch['episode_output']).resolve()==ep
            and all(batch.get(key)==value for key,value in terms.items())
            and batch['skill_sha256']==sha(ep/'SKILL.md')
            and batch['entrypoint_sha256']==sha(ep/'host-source-snapshot/run_api_policy.py')
            and batch['scene_sha256']==read(ep/'provenance.json')['scene_sha256'])
        paths.extend([registration,folder/'batch-terms.json'])
    for row in series:
        expected=ep/'api-batches'/row['run_id']/'calls'/f"{row['batch_call']:02d}"
        flat=ep/'api-calls'/f"{row['global_call']:02d}"
        file_binding &= Path(row['source']).resolve()==expected and flat.resolve()==expected
        receipts.append(read(expected/'receipt.json'));paths.append(expected/'receipt.json')
    actual_receipts={p.resolve() for p in (ep/'api-batches').glob('*/calls/*/receipt.json')}
    listed_receipts={Path(row['source']).resolve()/'receipt.json' for row in series}
    file_binding &= actual_receipts==listed_receipts
    for index,item in enumerate(transitions):
        old=ep/'api-batches'/item['previous_run']/'calls'/f"{item['previous_call']:02d}"/'receipt.json'
        previous=read(old)
        file_binding &= (Path(item['previous_receipt']).resolve()==old
            and item['previous_receipt_sha256']==sha(old)
            and item['previous_response_id']==previous['response_id'])
        new_terms=read(ep/'api-batches'/item['new_run']/'batch-terms.json')
        prior=new_terms['previous_completed_batch']
        scope_binding &= all(item.get(key)==value for key,value in prior.items())
    checks=check_series(series,receipts,runs,batches,transitions)
    checks.update(serial_files_bound=file_binding,all_batch_scopes_valid=scope_binding,
        result_call_total=result['api_calls']==len(series),one_episode=result['same_episode_serial_batches'] is True)
    return dict(checks=checks,passed=all(checks.values()),
        evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        private_reasoning_read=False,ledger_mutated=False)
