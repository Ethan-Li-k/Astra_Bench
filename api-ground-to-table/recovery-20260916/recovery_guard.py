"""Validate frozen old holds. No network, no ledger writes, no completion synthesis."""
import hashlib
import json
from pathlib import Path
import re

UNKNOWN='api-ground-002-call-55'
EMPTY_SHA=hashlib.sha256(b'').hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def evidence(root,ref):
    require(isinstance(ref,dict) and set(ref)>={'path','sha256'},'missing evidence reference')
    p=Path(root)/ref['path']
    require(p.resolve().is_relative_to(Path(root).resolve()) and p.is_file(),'invalid evidence path')
    raw=p.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==ref['sha256'],'changed evidence')
    return raw

def validate_frozen_prior(state,snapshot,root,*,new_batch_ref=None):
    rows=snapshot['requests'];current=state['requests']
    expected={'api-ground-001-call-%02d'%i for i in range(1,7)}|{'api-ground-002-call-%02d'%i for i in range(1,56)}
    pending={k for k,v in rows.items() if v['state'] in ('inflight','reserved')}
    require(pending==expected,'snapshot must contain exact 61 old holds')
    for key,row in rows.items():
        require(current.get(key)==row,'old ledger row changed or missing: '+key)
    for key,row in current.items():
        if key in rows:continue
        require(new_batch_ref is not None and row.get('batch')==new_batch_ref and
                re.fullmatch(r'api-ground-003-call-(?:0[1-9]|[1-9][0-9]|1[01][0-9]|120)',key),
                'foreign request is not authorized by this recovery')
    for key in sorted(expected):
        row=rows[key]
        require(row['request_id']==key and row['state']=='inflight' and row['reserved_fen']==1217,
                'invalid frozen reservation')
        evidence(root,row['batch'])
        if key==UNKNOWN:
            require('completion_evidence' not in row,'unknown must never become a fake completion')
            p=Path(root)/row['inputs']['estimate_plan']['path']
            require(row['inputs']['estimate_plan']['sha256']=='e90d79a7e7d6ca63c0142ad0db5b0a52d747837ce62c24b47124b9695de8e8d8'
                    and p.read_bytes()==b'','unexpected interrupted plan; re-audit required')
            receipt=Path(root)/'api-ground-to-table/actor-adapter/campaign/episode-0002/api_calls/55/receipt.json'
            require(receipt.read_bytes()==b'','unknown receipt changed; re-audit required')
            continue
        evidence(root,row['inputs']['estimate_plan'])
        v=json.loads(evidence(root,row.get('completion_evidence')))
        require(v.get('state')=='completed' and v.get('http_status')==200
            and v.get('ledger_request_id')==key and v.get('returned_model')=='gpt-6-astra'
            and v.get('reasoning_effort')=='xhigh' and v.get('response_id')
            and v.get('actual_cny_fen') is None,'invalid completed unknown-cost receipt')
        require(type(v.get('started_at')) in (float,int) and type(v.get('finished_at')) in (float,int)
            and v['finished_at']>=v['started_at'],'invalid receipt timing')
    return expected
