"""Bounded old-code reproductions. Synthetic ledger only; no client imports."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'ikea/budget-coordination'
sys.path.insert(0, str(ROOT/'tools/coordination'))
spec = importlib.util.spec_from_file_location('shared_budget', OUT/'before/shared_budget.py')
b = importlib.util.module_from_spec(spec)
sys.modules['shared_budget'] = b
spec.loader.exec_module(b)
# All fixture evidence and ledgers remain in this task's isolated write domain.
b.ROOT = OUT/'tests/old-workspace'
b.OUT = b.ROOT/'artifacts'
b.OUT.mkdir(parents=True, exist_ok=True)
b.POLICY = ROOT/'ref/tasks/api-budget.json'
from test_approved_continuation import ApprovedContinuation


class Reproductions(ApprovedContinuation):
    def test_authorized_foreign_is_still_rejected(self):
        self.prepare(False)
        with self.f.book.transaction() as (state, _):
            state['requests']['ikea-authorized-synthetic'] = {
                'request_id': 'ikea-authorized-synthetic', 'state': 'inflight',
                'reserved_fen': 678, 'authorization_document': {
                    'path': 'ref/USER_UPDATE_20260916_IKEA_OWNER.md',
                    'desktop_session': '01a0a964-0f61-7cc3-b004-1d59499dd966'}}
        with self.assertRaisesRegex(b.BudgetError, 'unsettled') as caught:
            self.reserve()
        print('REPRO1:', str(caught.exception), flush=True)

    def test_loaded_old_module_rejects_new_hold_before_next_dispatch(self):
        # b was loaded once above, exactly like actor->hook->shared_budget.
        self.prepare(False)
        self.reserve()
        with self.f.book.transaction() as (state, _):
            state['requests']['new-foreign'] = {'request_id': 'new-foreign',
                'state': 'reserved', 'reserved_fen': 678}
        with self.assertRaisesRegex(b.BudgetError, 'foreign unsettled') as caught:
            self.f.book.begin_empirical(self.document['request_id'], self.payload_hash)
        self.assertEqual(b.load(self.f.ledger)['requests'][self.document['request_id']]['state'], 'reserved')
        print('REPRO2:', str(caught.exception), flush=True)


if __name__ == '__main__':
    names = ['test_authorized_foreign_is_still_rejected',
             'test_loaded_old_module_rejects_new_hold_before_next_dispatch']
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Reproductions(n) for n in names))
    (OUT/'tests/reproduction-result.json').write_text(json.dumps({
        'tests_run': result.testsRun, 'passed': result.wasSuccessful(),
        'old_code_sha256': b.sha(OUT/'before/shared_budget.py'),
        'synthetic_only': True, 'production_ledger_accessed': False}, indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
