"""Synthetic tests for the separately labelled, single-batch estimate path."""
import unittest
import shared_budget as b
from budget_test_fixtures import Fixture


class EmpiricalBudgetTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.f.reserve('calibration', 339)
        self.f.book.begin('calibration')
        self.f.book.settle('calibration', self.f.receipt('calibration', 339))
        self.plan = self.f.root/'estimate-plan.json'
        self.payload_hash = 'a'*64
        self.document = {
            'schema': 1, 'mode': 'empirical_estimate', 'synthetic_test_fixture': True,
            'authorization': 'SYNTHETIC user estimation authorization',
            'provider': 'SYNTHETIC-NOT-A-PROVIDER', 'model': 'gpt-6-astra',
            'reasoning_effort': 'xhigh', 'pricing_verified': False, 'hard_cost_bound': False,
            'request_id': 'probe', 'calibration_request_id': 'calibration',
            'scope': {'role': 'engineer', 'environment': 'synthetic', 'branch': 'synthetic'},
            'payload_sha256': self.payload_hash, 'max_payload_bytes': 2000,
            'max_output_tokens': 4096, 'calibration_input_bytes': 2172,
            'calibration_output_tokens': 9129, 'margin_multiplier': 2,
            'max_calls': 1, 'automatic_retries': False,
        }
        self.write_plan()
        p = b.load(self.f.policy)
        p['api_source_status'] = 'not_verified_for_price'
        b.atomic_write(self.f.policy, p)

    def write_plan(self):
        b.atomic_write(self.plan, self.document)
        self.ref = {'path': str(self.plan.relative_to(b.ROOT)), 'sha256': b.sha(self.plan)}

    def reserve(self):
        return self.f.book.reserve_empirical(self.ref)

    def begin(self, digest=None):
        return self.f.book.begin_empirical('probe', digest or self.payload_hash)

    def test_estimate_not_verified_price_and_idempotence(self):
        r = self.reserve()
        self.assertEqual(r['reserved_fen'], 678)
        self.assertFalse(r['pricing_verified'])
        self.assertFalse(r['hard_cost_bound'])
        self.assertFalse(self.reserve()['created'])
        self.assertFalse(self.f.book.status()['pricing_verified'])

    def test_unknown_cost_kept_and_second_batch_blocked(self):
        self.reserve()
        self.assertTrue(self.begin()['transitioned'])
        self.assertFalse(self.begin()['transitioned'])
        with self.assertRaises(b.BudgetError):
            self.f.book.cancel('probe', 'unknown is not zero')
        self.document['request_id'] = 'second'
        self.write_plan()
        with self.assertRaisesRegex(b.BudgetError, 'unsettled'):
            self.reserve()
        self.assertEqual(self.f.book.status()['outstanding_reserved_fen'], 678)

    def test_changed_payload_or_plan_blocks_dispatch(self):
        self.reserve()
        with self.assertRaisesRegex(b.BudgetError, 'payload'):
            self.begin('b'*64)
        self.document['max_output_tokens'] = 4000
        self.write_plan()
        with self.assertRaisesRegex(b.BudgetError, 'evidence'):
            self.begin()

    def test_invalid_limits_and_false_pricing_claims(self):
        for key, value in [('max_calls', 2), ('automatic_retries', True),
                           ('max_payload_bytes', 0), ('max_output_tokens', None),
                           ('margin_multiplier', 1), ('pricing_verified', True),
                           ('hard_cost_bound', True), ('model', 'other')]:
            original = self.document[key]
            self.document[key] = value
            self.write_plan()
            with self.assertRaises(b.BudgetError, msg=key):
                self.reserve()
            self.document[key] = original

    def test_only_known_historical_pause_can_be_cleared(self):
        with self.f.book.transaction() as (state, _):
            state['halted'] = 'historical_calibration_cost_recorded; empirical_reservation_adapter_pending'
        self.reserve()
        self.assertIsNone(self.f.book.status()['halted'])

    def test_other_pause_never_cleared(self):
        with self.f.book.transaction() as (state, _):
            state['halted'] = 'actual_charge_exceeded_reservation; reconcile_adapter_and_billing'
        with self.assertRaisesRegex(b.BudgetError, 'halted'):
            self.reserve()

    def test_estimate_uses_same_shared_cap(self):
        self.document['max_output_tokens'] = 20_000_000
        self.write_plan()
        with self.assertRaisesRegex(b.BudgetError, 'cap exceeded'):
            self.reserve()

    def test_actual_settlement_idempotent_overestimate_halts(self):
        self.reserve()
        self.begin()
        receipt = self.f.receipt('probe', 679)
        self.f.book.settle('probe', receipt)
        self.assertFalse(self.f.book.settle('probe', receipt)['changed'])
        s = self.f.book.status()
        self.assertEqual(s['settled_fen'], 339+679)
        self.assertEqual(s['outstanding_reserved_fen'], 0)
        self.assertIsNotNone(s['halted'])

    def test_estimate_cannot_use_strict_begin(self):
        self.reserve()
        with self.assertRaises(b.BudgetError):
            self.f.book.begin('probe')

    def test_bounded_same_batch_continues_with_all_unknown_costs_held(self):
        path = self.f.root/'batch.json'
        b.atomic_write(path, {'authorization': 'SYNTHETIC batch only', 'model': 'gpt-6-astra',
            'provider': self.document['provider'], 'calibration_request_id': 'calibration',
            'max_calls': 2, 'max_payload_bytes': 2000, 'max_output_tokens': 4096})
        self.document['batch'] = {'path': str(path.relative_to(b.ROOT)), 'sha256': b.sha(path)}
        self.write_plan()
        self.reserve()
        self.begin()
        self.document['request_id'] = 'probe2'
        self.write_plan()
        self.reserve()
        self.assertEqual(self.f.book.status()['outstanding_reserved_fen'], 1356)
        self.document['request_id'] = 'probe3'
        self.write_plan()
        with self.assertRaisesRegex(b.BudgetError, 'batch call limit'):
            self.reserve()


if __name__ == '__main__':
    unittest.main(verbosity=2)
