"""Explicit synthetic fixtures, never real prices, spend or billing evidence."""
import json
from pathlib import Path
import tempfile

import shared_budget as b


def pricing_fixture(proof):
    ref = {"path": str(proof.relative_to(b.ROOT)), "sha256": b.sha(proof)}
    return {"schema": 2, "synthetic_test_fixture": True,
            "verification_status": "verified", "provider": "SYNTHETIC-NOT-A-PROVIDER",
            "model": "gpt-6-astra", "billing_currency": "CNY",
            "minor_units_per_currency_unit": 100, "price_version": "SYNTHETIC-TEST-RATE",
            "valid_until": "2099-01-01T00:00:00+00:00", "pricing_evidence": ref,
            "rates": {"synthetic_units": {"minor_per_unit": 1, "units_per_price": 1}},
            "fx_upper_bound": {"cny_fen_numerator": 1, "billing_minor_denominator": 1, "basis_evidence": ref},
            "bound_enforcement": {"verified": True, "covers_all_charges": True,
                                  "adapter_version": "synthetic-stub", "evidence": ref}}


def policy_fixture():
    document = b.load(b.POLICY)
    document.update(api_source_status="verified", synthetic_test_fixture=True,
                    authorization="SYNTHETIC UNIT TEST; NOT A NEW USER AUTHORIZATION")
    return document


class Fixture:
    def __init__(self):
        parent = b.OUT/"synthetic-tests"
        parent.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="synthetic-budget-", dir=parent))
        self.proof = self.root/"SYNTHETIC-NOT-REAL-EVIDENCE.txt"
        self.proof.write_text("SYNTHETIC: no real provider, prices, usage, reports or money.\n")
        self.policy = self.root/"policy.json"
        self.pricing = self.root/"pricing.json"
        self.ledger = self.root/"ledger.json"
        b.atomic_write(self.policy, policy_fixture())
        b.atomic_write(self.pricing, pricing_fixture(self.proof))
        self.book = b.BudgetLedger(self.ledger, policy_path=self.policy, pricing_path=self.pricing)
        self.book.initialize()

    def reserve(self, request="r1", amount=100):
        return self.book.reserve(request, {"role": "synthetic-role", "environment": "synthetic-env",
                                "branch": "synthetic-branch"}, {"synthetic_units": amount})

    def receipt(self, request, amount, final=True):
        path = self.root/f"SYNTHETIC-billing-{request}-{amount}-{final}.json"
        b.atomic_write(path, {"synthetic_test_fixture": True, "request_id": request,
            "actual_cny_fen": amount, "currency": "CNY", "final": final,
            "conversion_basis": "SYNTHETIC CNY minor-unit fixture; not real conversion",
            "billing_event_id": "synthetic-"+request, "provider": "SYNTHETIC-NOT-A-PROVIDER",
            "model": "gpt-6-astra"})
        return {"path": str(path.relative_to(b.ROOT)), "sha256": b.sha(path)}

    def report(self, threshold, delivered):
        path = self.root/f"SYNTHETIC-report-{threshold}-{delivered}.json"
        b.atomic_write(path, {"synthetic_test_fixture": True, "threshold_fen": threshold,
            "delivered": delivered, "recipient": "user", "delivery_id": "synthetic-report-"+str(threshold),
            "content": {"cumulative_and_remaining_cost": "synthetic costs only",
                        "task_progress": "synthetic", "independent_success_counts": "0 real",
                        "failure_findings": "synthetic unit test"}})
        return {"path": str(path.relative_to(b.ROOT)), "sha256": b.sha(path)}
