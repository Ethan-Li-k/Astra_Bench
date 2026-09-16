"""Offline adversarial inputs for a single explicitly frozen interruption."""
import copy
import json
from pathlib import Path
import unittest
import recovery_guard as guard
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=Path(__file__).resolve().parent

class HoldTests(unittest.TestCase):
    def setUp(self):
        self.state=json.loads((OUT/'original-snapshot/artifacts/R020/shared-budget-ledger.json').read_text())
        self.snapshot=copy.deepcopy(self.state)
    def check(self):
        return guard.validate_frozen_prior(self.state,self.snapshot,ROOT)
    def test_exact_recovery_preserves_every_hold(self):
        before=copy.deepcopy(self.state)
        ids=self.check()
        self.assertEqual(len(ids),61)
        self.assertIn('api-ground-002-call-55',ids)
        self.assertEqual(before,self.state)
    def test_all_old_row_changes_rejected(self):
        key='api-ground-002-call-55'
        for field,val in [('state','completed'),('reserved_fen',0),('completion_evidence',{}),('begun_at','changed')]:
            with self.subTest(field=field):
                self.state=copy.deepcopy(self.snapshot);self.state['requests'][key][field]=val
                with self.assertRaises(ValueError):self.check()
    def test_missing_unknown_or_completed_rejected(self):
        for key in ['api-ground-002-call-55','api-ground-002-call-54','api-ground-001-call-01']:
            self.state=copy.deepcopy(self.snapshot);del self.state['requests'][key]
            with self.assertRaises(ValueError):self.check()
    def test_foreign_pending_rejected(self):
        self.state['requests']['other-task-call-1']=dict(self.snapshot['requests']['api-ground-002-call-55'],request_id='other-task-call-1')
        with self.assertRaises(ValueError):self.check()
    def test_second_unknown_in_snapshot_rejected(self):
        self.snapshot['requests']['api-ground-002-call-54'].pop('completion_evidence')
        self.state=copy.deepcopy(self.snapshot)
        with self.assertRaises(ValueError):self.check()
    def test_bad_completion_and_plan_refs_rejected(self):
        for field in ['completion_evidence','inputs']:
            self.snapshot['requests']['api-ground-002-call-54'][field]={}
            self.state=copy.deepcopy(self.snapshot)
            with self.assertRaises((ValueError,KeyError)):self.check()
    def test_no_arbitrary_new_batch_pending(self):
        self.state['requests']['api-ground-004-call-01']=dict(self.snapshot['requests']['api-ground-002-call-55'],request_id='api-ground-004-call-01')
        with self.assertRaises(ValueError):self.check()

if __name__=='__main__':unittest.main(verbosity=2)
