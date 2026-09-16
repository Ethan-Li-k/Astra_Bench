"""Local accounting for registered 001/002 batches; never queries quota."""
import importlib.util
import json
from pathlib import Path

ROOT = Path('/home/galbot/lizekai/RSI')
REGISTERED = {name: ROOT/'artifacts/R021'/name for name in ('api-ground-001', 'api-ground-002')}
spec = importlib.util.spec_from_file_location('rsi_shared_api_budget', ROOT/'tools/coordination/shared_budget.py')
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


def reference(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': budget.sha(path)}


def route(run_id):
    budget.require(run_id in REGISTERED, 'Unregistered batch')
    return REGISTERED[run_id]


def reserve(meta):
    out = route(meta['run_id'])
    batch_path = out/'batch.json'
    batch = budget.reviewed_batch(reference(batch_path))
    budget.require(batch['new_observation_data_authorized'] is True,
                   'New simulation-data transfer authorization not yet recorded; no dispatch')
    budget.require(meta['run_id'] == batch['batch_id'], 'Wrong batch')
    for key in ('provider', 'model'):
        budget.require(meta[key] == batch[key], 'Provider/model mismatch')
    budget.require(meta['effort'] == 'xhigh', 'Astra/xhigh only')
    index = budget.integer(meta['call_index'], 'one-based call index', 1)
    budget.require(index <= batch['max_calls'], 'Batch call limit')
    size = budget.integer(meta['input_bytes'], 'request bytes', 1)
    output = budget.integer(meta['max_output_tokens'], 'output tokens', 1)
    budget.require(size <= batch['max_payload_bytes'] and output <= batch['max_output_tokens'],
                   'Input/output size limit')
    request_id = f"{batch['batch_id']}-call-{index:02d}"
    path = out/f'{request_id}-plan.json'
    plan = dict(schema=1, mode='empirical_estimate', authorization=batch['authorization'],
        provider=meta['provider'], model=meta['model'], reasoning_effort='xhigh',
        pricing_verified=False, hard_cost_bound=False, request_id=request_id,
        calibration_request_id=batch['calibration_request_id'],
        scope={'role': 'planner-actor', 'environment': 'isolated-original-table-MuJoCo',
               'branch': 'api-ground-to-table'}, payload_sha256=meta['request_sha256'],
        max_payload_bytes=size, max_output_tokens=output,
        calibration_input_bytes=batch['calibration_input_bytes'],
        calibration_output_tokens=batch['calibration_output_tokens'],
        margin_multiplier=batch['margin_multiplier'], max_calls=1, automatic_retries=False,
        batch=reference(batch_path))
    if batch['max_calls'] > 6:
        plan['call_index'] = index
    # Exclusive per-slot plan: a changed payload cannot reuse an uncertain call.
    try:
        with path.open('x') as stream:
            json.dump(plan, stream, indent=2)
    except FileExistsError:
        budget.require(budget.load(path) == plan, 'Conflicting request in used batch slot')
    book = budget.BudgetLedger()
    row = book.reserve_empirical(reference(path))
    begin = book.begin_empirical(request_id, meta['request_sha256'])
    budget.require(begin['transitioned'], 'Already dispatched or uncertain: NO retry')
    return {'request_id': request_id, 'run_id': meta['run_id'], 'batch': reference(batch_path),
            'reserved_fen': row['reserved_fen'],
            'basis': 'empirical_estimate_not_a_hard_cost_bound'}


def settle(reservation, receipt):
    """Save completion evidence; usage alone is NOT an actual billing receipt."""
    request_id = reservation['request_id']
    out = route(reservation['run_id'])
    batch_ref = reference(out/'batch.json')
    batch = budget.reviewed_batch(batch_ref)
    budget.require(reservation['batch'] == batch_ref and receipt['run_id'] == reservation['run_id']
        and request_id == f"{reservation['run_id']}-call-{receipt['call_index']:02d}"
        and 1 <= receipt['call_index'] <= batch['max_calls'], 'Completion route mismatch')
    public = {key: receipt[key] for key in (
        'state', 'status', 'http_status', 'response_id', 'request_id', 'provider_request_id',
        'usage', 'model', 'returned_model', 'reasoning_effort', 'started_at', 'finished_at',
        'error', 'incomplete_details') if key in receipt}
    public.update(ledger_request_id=request_id, actual_cny_fen=None,
                  cost_status='unknown_retained_in_shared_reservation_no_quota_query')
    path = out/f'{request_id}-completion.json'
    budget.require(not path.exists(), 'Completion evidence already exists; no overwrite')
    budget.atomic_write(path, public)
    with budget.BudgetLedger().transaction() as (state, _):
        row = state['requests'][request_id]
        budget.require(row['state'] == 'inflight' and row.get('batch') == batch_ref,
                       'Only matching inflight completion')
        row['completion_evidence'] = reference(path)
    return {'actual_cny_fen': None, 'reservation_retained': True}
