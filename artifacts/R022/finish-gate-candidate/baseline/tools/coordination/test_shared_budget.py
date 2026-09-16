"""Isolated offline accounting tests; all money and receipts are synthetic."""
import multiprocessing as mp
import unittest

import shared_budget as b
from budget_test_fixtures import Fixture


def reserve_worker(ledger, policy, pricing, barrier, queue, index, same_id):
    book = b.BudgetLedger(ledger, policy_path=policy, pricing_path=pricing)
    try:
        barrier.wait(timeout=8)
        result = book.reserve("same" if same_id else f"request-{index}",
            {"role": "shared" if same_id else f"role-{index}", "environment": "isolated-test",
             "branch": "shared" if same_id else f"branch-{index}"}, {"synthetic_units": 200_000})
        queue.put(("ok", result["created"]))
    except b.BudgetError as exc:
        queue.put(("rejected", str(exc)))
    except Exception as exc:
        queue.put(("error", str(exc)))


class SharedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def test_over_cap_rejected(self):
        self.f.reserve(amount=900_000)
        with self.assertRaisesRegex(b.BudgetError, "cap exceeded"):
            self.f.reserve("r2", 100_001)
        self.assertEqual(self.f.book.status()["outstanding_reserved_fen"], 900_000)

    def test_unsettled_and_inflight_remain_committed(self):
        self.f.reserve(amount=600_000)
        self.assertTrue(self.f.book.begin("r1")["transitioned"])
        self.assertFalse(self.f.book.begin("r1")["transitioned"])
        with self.assertRaises(b.BudgetError):
            self.f.book.cancel("r1", "timeout is NOT proof of no charge")
        with self.assertRaises(b.BudgetError):
            self.f.reserve("r2", 400_001)
        with self.assertRaises(b.BudgetError):
            self.f.book.settle("r1", self.f.receipt("r1", 0, final=False))
        reopened = b.BudgetLedger(self.f.ledger, policy_path=self.f.policy, pricing_path=self.f.pricing)
        self.assertEqual(reopened.status()["outstanding_reserved_fen"], 600_000)

    def test_settled_plus_inflight_plus_new_reservation(self):
        self.f.reserve(amount=300_000)
        self.f.book.begin("r1")
        self.f.book.settle("r1", self.f.receipt("r1", 250_000))
        self.f.reserve("r2", 700_000)
        self.f.book.begin("r2")
        with self.assertRaisesRegex(b.BudgetError, "cap exceeded"):
            self.f.reserve("r3", 50_001)
        self.f.reserve("r3", 50_000)
        s = self.f.book.status()
        self.assertEqual(s["settled_fen"]+s["outstanding_reserved_fen"], 1_000_000)

    def test_request_id_is_idempotent_and_conflict_rejected(self):
        self.assertTrue(self.f.reserve()["created"])
        self.assertFalse(self.f.reserve()["created"])
        with self.assertRaises(b.BudgetError):
            self.f.reserve(amount=101)
        self.assertEqual(self.f.book.status()["request_count"], 1)

    def test_settlement_idempotent_and_release_only_unused_amount(self):
        self.f.reserve(amount=400_000)
        self.f.book.begin("r1")
        ref = self.f.receipt("r1", 250_000)
        self.assertTrue(self.f.book.settle("r1", ref)["changed"])
        self.assertFalse(self.f.book.settle("r1", ref)["changed"])
        with self.assertRaises(b.BudgetError):
            self.f.book.settle("r1", self.f.receipt("r1", 240_000))
        with self.assertRaises(b.BudgetError):
            self.f.book.cancel("r1", "already charged")
        s = self.f.book.status()
        self.assertEqual((s["settled_fen"], s["outstanding_reserved_fen"], s["remaining_uncommitted_fen"]),
                         (250_000, 0, 750_000))

    def test_cancellation_only_before_dispatch_and_no_id_reuse(self):
        self.f.reserve(amount=500_000)
        self.assertTrue(self.f.book.cancel("r1", "not sent")["changed"])
        self.assertFalse(self.f.book.cancel("r1", "not sent")["changed"])
        self.assertEqual(self.f.reserve(amount=500_000)["state"], "cancelled")
        with self.assertRaises(b.BudgetError):
            self.f.book.begin("r1")
        self.assertEqual(self.f.book.status()["remaining_uncommitted_fen"], 1_000_000)

    def test_multiple_thresholds_persist_until_real_report_receipt(self):
        self.f.reserve(amount=460_000)
        self.f.book.begin("r1")
        ref = self.f.receipt("r1", 460_000)
        self.f.book.settle("r1", ref)
        self.f.book.settle("r1", ref)
        for _ in range(2):
            self.assertEqual([x["threshold_fen"] for x in self.f.book.status()["pending_reports"]],
                             [150_000, 300_000, 450_000])
        with self.assertRaises(b.BudgetError):
            self.f.book.acknowledge_report(150_000, self.f.report(150_000, False))
        delivered = self.f.report(150_000, True)
        self.f.book.acknowledge_report(150_000, delivered)
        self.f.book.acknowledge_report(150_000, delivered)
        s = self.f.book.status()
        self.assertEqual(len(s["pending_reports"]), 2)
        self.assertEqual(s["remaining_uncommitted_fen"], 540_000)
        self.assertEqual(s["cap_fen"], 1_000_000)

    def test_final_report_at_cap_and_stop(self):
        self.f.reserve(amount=1_000_000)
        self.f.book.begin("r1")
        self.f.book.settle("r1", self.f.receipt("r1", 1_000_000))
        self.assertEqual([r["threshold_fen"] for r in self.f.book.status()["pending_reports"]],
                         [150_000, 300_000, 450_000, 600_000, 750_000, 900_000, 1_000_000])
        with self.assertRaises(b.BudgetError):
            self.f.reserve("r2", 1)

    def test_missing_source_blocks_reservation(self):
        p = b.load(self.f.policy)
        p["api_source_status"] = "not_yet_confirmed"
        b.atomic_write(self.f.policy, p)
        with self.assertRaisesRegex(b.BudgetError, "source is not verified"):
            self.f.reserve()
        self.assertEqual(self.f.book.status()["request_count"], 0)

    def test_missing_prices_fx_or_unbounded_request_blocks(self):
        original = b.load(self.f.pricing)
        for key in ("provider", "rates", "billing_currency", "fx_upper_bound", "bound_enforcement"):
            modified = dict(original)
            modified.pop(key)
            b.atomic_write(self.f.pricing, modified)
            with self.assertRaises((b.BudgetError, KeyError, TypeError)):
                self.f.reserve()
        b.atomic_write(self.f.pricing, original)
        for maxima in ({}, {"synthetic_units": None}, {"synthetic_units": -1}, {"synthetic_units": float("inf")}):
            with self.assertRaises((b.BudgetError, ValueError)):
                self.f.book.reserve("unbounded", {"role": "r", "environment": "e", "branch": "b"}, maxima)
        self.assertEqual(self.f.book.status()["request_count"], 0)

    def test_expired_prices_block_and_changed_prices_block_begin(self):
        self.f.reserve()
        price = b.load(self.f.pricing)
        price["price_version"] = "SYNTHETIC-CHANGED"
        b.atomic_write(self.f.pricing, price)
        with self.assertRaisesRegex(b.BudgetError, "pricing changed"):
            self.f.book.begin("r1")
        price["valid_until"] = "2000-01-01T00:00:00+00:00"
        b.atomic_write(self.f.pricing, price)
        with self.assertRaisesRegex(b.BudgetError, "expired"):
            self.f.reserve("r2")

    def test_integer_conversion_rounds_up(self):
        p = b.load(self.f.pricing)
        p["rates"]["synthetic_units"] = {"minor_per_unit": 1, "units_per_price": 3}
        p["fx_upper_bound"].update(cny_fen_numerator=7, billing_minor_denominator=2)
        self.assertEqual(b.worst_case_fen(p, {"synthetic_units": 1}), 4)
        self.assertEqual(b.worst_case_fen(p, {"synthetic_units": 4}), 7)

    def test_truthful_overbilling_record_freezes_future_reservations(self):
        self.f.reserve(amount=100)
        self.f.book.begin("r1")
        self.f.book.settle("r1", self.f.receipt("r1", 101))
        s = self.f.book.status()
        self.assertEqual(s["settled_fen"], 101)
        self.assertIsNotNone(s["halted"])
        with self.assertRaisesRegex(b.BudgetError, "halted"):
            self.f.reserve("r2")

    def run_parallel(self, same_id):
        ctx = mp.get_context("fork")
        barrier, queue = ctx.Barrier(8), ctx.Queue()
        processes = [ctx.Process(target=reserve_worker, args=(self.f.ledger, self.f.policy,
            self.f.pricing, barrier, queue, i, same_id)) for i in range(8)]
        for p in processes:
            p.start()
        results = [queue.get(timeout=12) for _ in processes]
        for p in processes:
            p.join(timeout=2)
            self.assertEqual(p.exitcode, 0)
        self.assertFalse([r for r in results if r[0] == "error"], results)
        return results

    def test_concurrent_reservations_share_one_cap(self):
        results = self.run_parallel(False)
        self.assertEqual(sum(r[0] == "ok" for r in results), 5, results)
        s = self.f.book.status()
        self.assertEqual(s["outstanding_reserved_fen"], 1_000_000)
        self.assertEqual(s["request_count"], 5)

    def test_concurrent_identical_id_reserves_only_once(self):
        results = self.run_parallel(True)
        self.assertEqual(sum(r == ("ok", True) for r in results), 1, results)
        self.assertEqual(self.f.book.status()["outstanding_reserved_fen"], 200_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
