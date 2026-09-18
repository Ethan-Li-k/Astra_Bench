"""Pinned actor transport dependencies extracted from reviewed continuation-v3.

No management selector/watcher is imported. Existing transport, source pins,
approval verifier and shared budget remain separately hash admitted.
"""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=ROOT/'codex-account-2/continuation'
MODEL,EFFORT='gpt-6-astra','xhigh'
def sha(data):
    return hashlib.sha256(data).hexdigest()

def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))

def load_pinned(name, relative):
    pins = json.loads((OUT / 'api-source-pins.json').read_text())
    path = ROOT / relative
    if sha(path.read_bytes()) != pins[relative]:
        raise ValueError('existing_API_source_drift')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module

def transport_only():
    from rsi.api_use import require_api_enabled
    require_api_enabled()
    for dependency in ('history_bound.py', 'stream_evidence.py'):
        relative = 'api-ground-to-table/actor-adapter/' + dependency
        pins = json.loads((OUT / 'api-source-pins.json').read_text())
        if sha((ROOT / relative).read_bytes()) != pins[relative]:
            raise ValueError('transport_dependency_drift')
    transport = load_pinned('supervisor_existing_responses', 'api-ground-to-table/actor-adapter/actor.py')
    return transport

def modules():
    transport = transport_only()
    budget = load_pinned('supervisor_shared_budget', 'tools/coordination/shared_budget.py')
    registration = load_pinned('supervisor_existing_registration', 'ikea/budget-coordination/register_batch.py')
    return (transport, budget, registration)

class BudgetHook:
    """Named SIMPLE branch adaptation of the existing RegisteredBudget hook."""

    def __init__(self, budget, batch_ref):
        self.b, self.batch_ref = (budget, batch_ref)
        self.batch = budget.reviewed_batch(batch_ref)
        budget.require(self.batch['branch'] == 'simple', 'SIMPLE-only engineering continuation')
        self.path = budget.evidence(batch_ref).parent

    def settle(self, reservation, receipt):
        b = self.b
        request = reservation['request_id']
        b.require(reservation['batch'] == self.batch_ref, 'completion route mismatch')
        public = {key: receipt[key] for key in ('state', 'status', 'http_status', 'response_id', 'provider_request_id', 'usage', 'model', 'returned_model', 'reasoning_effort', 'started_at', 'finished_at', 'error_type') if key in receipt}
        public.update(ledger_request_id=request, actual_cny_fen=None, cost_status='unknown_retained_in_shared_reservation')
        path = self.path / (request + '-completion.json')
        with path.open('x') as stream:
            json.dump(public, stream, indent=2)
        with b.BudgetLedger().transaction() as (state, _):
            row = state['requests'][request]
            b.require(row['state'] == 'inflight' and row['batch'] == self.batch_ref, 'matching inflight required')
            row['completion_evidence'] = ref(path)

def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
