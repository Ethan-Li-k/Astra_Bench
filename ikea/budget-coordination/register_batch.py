#!/usr/bin/env python3
"""Bind an owner's new batch to task authorization. NO ledger/API operations."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path('/home/galbot/lizekai/RSI')
spec = importlib.util.spec_from_file_location('budget', ROOT/'tools/coordination/shared_budget.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)


def reference(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': b.sha(path)}


def bind(batch, retained):
    b.require('approval' not in batch, 'Only new batch terms; never rewrite an old approval')
    return dict(schema=2, kind='explicit_cross_branch_batches',
        provenance='engineering_translation_of_user_task', user_approved_this_schema=False,
        authority=b.PARALLEL_AUTHORITY, concurrency_group='rsi-20260916-ikea-parallel-v1',
        retain_unknown_holds=True, replay_old_requests=False,
        members=[dict(batch_id=batch['batch_id'], branch=batch['branch'],
                      batch_terms_sha256=b.batch_terms_hash(batch))],
        retained_legacy_batches=retained)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--terms', required=True, type=Path)
    p.add_argument('--retain-legacy', action='append', default=[], type=Path)
    p.add_argument('--name', required=True)
    args = p.parse_args()
    b.require(bool(b.re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', args.name)), 'safe new directory name required')
    source = args.terms.resolve()
    b.require(any(base.resolve() in source.parents for base in (ROOT/'ikea', ROOT/'artifacts')),
              'terms must be an explicit IKEA/artifacts file')
    # No arbitrary credential files or non-JSON inputs.
    b.require(source.suffix == '.json' and source.name not in ('api.json', 'auth.json'), 'batch terms JSON only')
    retained = []
    for path in args.retain_legacy:
        ref = reference(path.resolve()); old = b.reviewed_batch(ref)
        b.require(old.get('schema', 1) == 1, 'retained batch must be legacy schema1')
        retained.append(ref)
    batch = b.load(source)
    approval = bind(batch, retained)
    out = ROOT/'ikea/budget-coordination/approvals'/args.name
    out.mkdir(parents=True, exist_ok=False)
    # Immutable new files; existing runs, receipts and ledger are never touched.
    for name, document in [('approval.json', approval)]:
        with (out/name).open('x') as stream: json.dump(document, stream, indent=2, ensure_ascii=False)
    batch = dict(batch, approval=reference(out/'approval.json'))
    with (out/'batch.json').open('x') as stream: json.dump(batch, stream, indent=2, ensure_ascii=False)
    ref = reference(out/'batch.json')
    b.reviewed_batch(ref)  # Fail closed; invalid output is not an enrollment.
    for path in out.iterdir(): path.chmod(0o444)
    receipt = dict(batch=ref, approval=batch['approval'], ledger_mutated=False,
                   dispatched=False, user_approved_this_schema=False, status='validated_metadata_only')
    with (out/'registration.json').open('x') as stream: json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__': main()
