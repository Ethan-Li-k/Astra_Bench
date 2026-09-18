#!/usr/bin/env python3
"""Offline shared CNY-fen accounting. No API client, credentials or network.

The only production budget authority is ref/tasks/api-budget.json. The library
must be integrated by EVERY future paid caller; passing these offline tests is
not evidence that any real provider enforces price/usage bounds.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"artifacts/R020"
POLICY = ROOT/"ref/tasks/api-budget.json"
PRICING = OUT/"api-configuration.json"
LEDGER = OUT/"shared-budget-ledger.json"
RUNTIME_VERSION = "shared-budget-cap-60000-v1"
LOADED_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class BudgetError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise BudgetError(message)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name}: integer >= {minimum} required")
    return value


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path, value):
    temporary = path.with_name(path.name+f".{os.getpid()}.tmp")
    with temporary.open("w") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def policy_terms(document):
    require(document["currency"] == "CNY" and bool(document["authorization"]), "missing CNY authorization")
    cap = integer(document["total_cap_cny"], "cap", 1)*100
    interval = integer(document["report_interval_cny"], "report interval", 1)*100
    require(cap in (1_000_000, 6_000_000) and interval == 150_000,
            "unexpected authorized budget terms; review required")
    if cap == 6_000_000:
        override = document.get("latest_user_override", {})
        require(document.get("previous_cap_cny") == 10000
                and override.get("api_use_authorized_now") is True
                and override.get("primary_account_model_calls_allowed") is False
                and override.get("new_policy_file") == "ref/USER_UPDATE_20260916_ISAAC_CONTINUATION_API_AMO.md",
                "60000 cap requires the recorded sixfold user authorization")
    require(document["renew_authorization_on_report"] is False, "reports cannot renew budget")
    thresholds = list(range(interval, cap, interval))
    require(document["report_thresholds_cny"] == [v//100 for v in thresholds], "inconsistent thresholds")
    require(document["final_report_at_cap"] is True, "cap report required")
    return {"cap_fen": cap, "report_interval_fen": interval,
            "thresholds_fen": thresholds+[cap], "currency": "CNY",
            "scope": document["scope"]}



def loaded_runtime(policy_path=None):
    """Local load receipt only. No ledger mutation, provider/price/quota query."""
    policy_path = POLICY if policy_path is None else policy_path
    return {"runtime_version": RUNTIME_VERSION, "loaded_source_sha256": LOADED_SOURCE_SHA256,
            "policy_sha256": sha(policy_path), "terms": policy_terms(load(policy_path)),
            "paid_request_sent": False}


def upgrade_terms(state, policy, policy_sha256):
    """One authorized 10000 -> 60000 migration, called only under the ledger lock.

    Request records, unknown holds, halts and existing report receipts are immutable
    to this operation. Previously pending reports remain pending, including an old
    final-cap event. A genuine old overcharge may require additional pending reports.
    """
    terms = policy_terms(policy)
    if state["terms"] == terms:
        return False
    old = {**terms, "cap_fen": 1_000_000,
           "thresholds_fen": list(range(150_000, 1_000_000, 150_000))+[1_000_000]}
    require(terms["cap_fen"] == 6_000_000 and state["terms"] == old,
            "only the authorized 10000-to-60000 transition is supported")
    spent, held = totals(state)
    require(spent+held <= old["cap_fen"] or state["halted"], "unexplained pre-migration overrun")
    record = {"migration_id": "user-20260916-sixfold-60000", "at": now(),
              "from_terms": state["terms"], "to_terms": terms, "policy_sha256": policy_sha256,
              "requests_sha256": fingerprint(state["requests"]),
              "existing_report_events_sha256": fingerprint(state["report_events"]),
              "request_count": len(state["requests"]), "halt_preserved": state["halted"]}
    require(not any(r.get("migration_id") == record["migration_id"]
                    for r in state.get("policy_migrations", [])), "conflicting duplicate cap migration")
    state.setdefault("policy_migrations", []).append(record)
    state["terms"] = terms
    for threshold in terms["thresholds_fen"]:
        if threshold <= spent and threshold not in old["thresholds_fen"]:
            key = str(threshold)
            if key not in state["report_events"]:
                state["report_events"][key] = {
                    "threshold_fen": threshold, "status": "pending",
                    "settled_fen_at_crossing": spent, "reserved_fen_at_crossing": held,
                    "remaining_uncommitted_fen_at_crossing": terms["cap_fen"]-spent-held,
                    "trigger_request": None, "trigger": record["migration_id"], "created_at": now(),
                    "required_content": ["cumulative_and_remaining_cost", "task_progress",
                                         "independent_success_counts", "failure_findings"]}
    return True


def evidence(ref):
    """Only explicit artifact references; never arbitrary credential paths."""
    path = (ROOT/ref["path"]).resolve()
    require(any(base.resolve() in path.parents for base in (
        ROOT/"artifacts", ROOT/"ikea/budget-coordination/approvals")),
        "evidence must be inside RSI/artifacts or the explicit parallel approval directory")
    require(path.is_file() and sha(path) == ref["sha256"], "missing/changed evidence")
    return path


def validate_pricing(policy, pricing):
    policy_terms(policy)
    require(not pricing.get("synthetic_test_fixture") or policy.get("synthetic_test_fixture") is True,
            "synthetic pricing cannot be used with production authorization")
    require(policy["api_source_status"] == "verified", "API source is not verified")
    require(pricing["schema"] == 2 and pricing["verification_status"] == "verified", "pricing is not verified")
    require(isinstance(pricing["provider"], str) and bool(pricing["provider"].strip()), "provider required")
    require(pricing["model"] == "gpt-6-astra", "required model is gpt-6-astra")
    require(bool(re.fullmatch(r"[A-Z]{3}", pricing["billing_currency"])), "billing currency required")
    integer(pricing["minor_units_per_currency_unit"], "billing minor unit scale", 1)
    require(bool(pricing["price_version"]), "price version required")
    expiry = datetime.fromisoformat(pricing["valid_until"])
    require(expiry.tzinfo is not None and expiry > datetime.now(timezone.utc), "price/FX validity expired")
    evidence(pricing["pricing_evidence"])
    fx = pricing["fx_upper_bound"]
    integer(fx["cny_fen_numerator"], "FX numerator", 1)
    integer(fx["billing_minor_denominator"], "FX denominator", 1)
    evidence(fx["basis_evidence"])
    bound = pricing["bound_enforcement"]
    require(bound["verified"] is True and bound["covers_all_charges"] is True,
            "all billable usage, fees, retries and FX must have enforceable worst-case bounds")
    require(bool(bound["adapter_version"]), "bound enforcement adapter version required")
    evidence(bound["evidence"])
    require(isinstance(pricing["rates"], dict) and bool(pricing["rates"]), "model price rates required")
    for component, rate in pricing["rates"].items():
        require(isinstance(component, str) and component, "invalid price component")
        integer(rate["minor_per_unit"], "component price")
        integer(rate["units_per_price"], "price unit size", 1)
    return pricing


def pricing_status(policy, pricing):
    try:
        validate_pricing(policy, pricing)
        return True, None
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return False, str(exc)


def worst_case_fen(pricing, maxima):
    require(isinstance(maxima, dict) and set(maxima) == set(pricing["rates"]),
            "a finite maximum is required for EVERY billable component")
    fx = pricing["fx_upper_bound"]
    total = 0
    for key, rate in pricing["rates"].items():
        units = integer(maxima[key], "maximum billable units")
        # Round up in provider minor units AND in CNY fen, never floats.
        numerator = units*rate["minor_per_unit"]
        minor = (numerator+rate["units_per_price"]-1)//rate["units_per_price"]
        total += (minor*fx["cny_fen_numerator"]+fx["billing_minor_denominator"]-1)//fx["billing_minor_denominator"]
    return total


def totals(state):
    spent = held = 0
    for request in state["requests"].values():
        amount = integer(request["reserved_fen"], "recorded reservation")
        phase = request["state"]
        require(phase in ("reserved", "inflight", "settled", "cancelled"), "invalid request state")
        if phase in ("reserved", "inflight"):
            held += amount
        if phase == "settled":
            spent += integer(request["actual_fen"], "recorded settlement")
    return spent, held


# This pins the real task authorization, not a fabricated user-approved schema.
PARALLEL_AUTHORITY = {
    "path": "ref/USER_UPDATE_20260916_IKEA_OWNER.md",
    "sha256": "a10b959c745ab5c525096e19eecf0c8333e7b0b8477e2e393af63b4aea08f5ab",
    "desktop_session": "01a0a964-0f61-7cc3-b004-1d59499dd966",
}


def batch_terms_hash(batch):
    # Excluding only the approval ref avoids a circular hash. All limits, scope,
    # data authorization and calibration/skill references remain bound.
    return fingerprint({k: v for k, v in batch.items() if k != 'approval'})


def parallel_approval(batch):
    ref = batch.get('approval')
    if not ref:
        return None
    approval = load(evidence(ref))
    if approval.get('schema') != 2:
        return None
    require(approval.get('kind') == 'explicit_cross_branch_batches'
            and approval.get('provenance') == 'engineering_translation_of_user_task'
            and approval.get('user_approved_this_schema') is False
            and 'user_quote' not in approval, 'parallel approval provenance mismatch')
    require(approval.get('authority') == PARALLEL_AUTHORITY, 'parallel authority mismatch')
    require(sha(ROOT/PARALLEL_AUTHORITY['path']) == PARALLEL_AUTHORITY['sha256'],
            'parallel authority document changed')
    require(approval.get('concurrency_group') == 'rsi-20260916-ikea-parallel-v1',
            'parallel concurrency group mismatch')
    require(approval.get('retain_unknown_holds') is True
            and approval.get('replay_old_requests') is False, 'parallel hold/retry policy')
    members = approval.get('members')
    require(isinstance(members, list) and bool(members), 'explicit batch members required')
    ids, branches = set(), set()
    for member in members:
        require(set(member) == {'batch_id', 'branch', 'batch_terms_sha256'}, 'invalid member fields')
        require(isinstance(member['batch_id'], str)
                and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', member['batch_id'])
                and member['batch_id'] not in ids, 'duplicate/invalid batch member')
        require(member['branch'] in ('ikea', 'api-ground-to-table', 'simple'), 'unapproved branch')
        require(isinstance(member['batch_terms_sha256'], str)
                and re.fullmatch(r'[a-f0-9]{64}', member['batch_terms_sha256']), 'batch hash required')
        ids.add(member['batch_id']); branches.add(member['branch'])
    expected = {'batch_id': batch.get('batch_id'), 'branch': batch.get('branch'),
                'batch_terms_sha256': batch_terms_hash(batch)}
    require(expected in members, 'batch terms/hash not authorized')
    require(batch.get('schema') == 2 and bool(batch.get('authorization'))
            and batch.get('model') == 'gpt-6-astra' and batch.get('reasoning_effort') == 'xhigh',
            'parallel batch model/schema mismatch')
    require(batch.get('new_observation_data_authorized') is True
            and batch.get('data_scope') == 'actor_public_rgb_robot_state_actions_skill'
            and batch.get('automatic_retries') is False
            and batch.get('pricing_verified') is False and batch.get('hard_cost_bound') is False,
            'parallel data authorization/retries/estimate labels')
    require(batch.get('provider') == 'https://llm-gateway.galbot.com'
            and batch.get('destination') == batch['provider']+'/v1/responses', 'parallel destination mismatch')
    for key, limit in [('max_calls', 120), ('max_payload_bytes', 2_000_000), ('max_output_tokens', 16384)]:
        require(integer(batch.get(key), key, 1) <= limit, 'parallel batch limit: '+key)
    for key in ('calibration_input_bytes', 'calibration_output_tokens'):
        integer(batch.get(key), key, 1)
    integer(batch.get('margin_multiplier'), 'margin', 2)
    require(not batch.get('prior_completed_batches'), 'use explicit retained legacy batch references')
    retained = approval.get('retained_legacy_batches')
    require(isinstance(retained, list) and len({fingerprint(r) for r in retained}) == len(retained),
            'duplicate/invalid retained legacy batches')
    for old_ref in retained:
        old = load(evidence(old_ref))
        require(old.get('schema', 1) == 1 and old.get('batch_id') not in ids,
                'retained legacy batches cannot authorize new dispatch')
    return approval


def parallel_pending_allowed(row, batch, approval):
    """Keep all charges held; admission of an old hold NEVER authorizes replay."""
    ref = row.get('batch')
    if ref in approval['retained_legacy_batches']:
        # Unfinished/reboot-interrupted requests remain unknown and fully held.
        reviewed_batch(ref)
        return True
    if not ref:
        return False
    other = reviewed_batch(ref)
    other_approval = parallel_approval(other)
    return (other_approval is not None
            and other_approval['authority'] == approval['authority']
            and other_approval['concurrency_group'] == approval['concurrency_group'])


def reviewed_batch(batch_ref):
    """Legacy batches stay <=6; an explicit hash-pinned approval may allow <=120."""
    batch = load(evidence(batch_ref))
    if parallel_approval(batch) is not None:
        return batch
    count = integer(batch['max_calls'], 'batch calls', 1)
    if count <= 6:
        require(not batch.get('prior_completed_batches'), 'continuation needs explicit approval')
        return batch
    require(count <= 120 and batch.get('approval'), 'batch above six needs explicit approval')
    approval = load(evidence(batch['approval']))
    require(approval.get('approved') is True and approval.get('schema') == 1,
            'missing explicit approval')
    require(approval.get('provenance') == 'coordinator-relayed'
            and approval.get('direct_transcript_verified') is False
            and approval.get('user_quote') == 'API不用审批，超额会暂停，批准计划'
            and approval.get('coordinator_task_id') == '01a0a4fb-3324-7073-b667-4e0e94c54ff2',
            'approval provenance mismatch')
    evidence(approval['reviewed_plan'])
    for key in ('batch_id', 'provider', 'model', 'reasoning_effort', 'max_calls',
                'max_payload_bytes', 'max_output_tokens', 'prior_completed_batches'):
        require(batch.get(key) == approval.get(key), 'approval/batch mismatch: '+key)
    require(approval['destination'] == batch['provider'].rstrip('/')+'/v1/responses'
            and approval['single_independent_episode'] is True
            and batch['automatic_retries'] is False
            and batch['new_observation_data_authorized'] is True,
            'approval scope/destination mismatch')
    require(batch['max_payload_bytes'] <= 2_000_000 and batch['max_output_tokens'] <= 16384
            and batch['reasoning_effort'] == 'xhigh', 'approved payload/model limits')
    return batch


def completed_hold(row, ref):
    """Completion is not settlement: retain the entire unknown-cost reservation."""
    require(isinstance(ref, dict) and row['state'] == 'inflight' and row.get('completion_evidence') == ref,
            'unfinished prior request or completion mismatch')
    receipt = load(evidence(ref))
    require(receipt.get('state') == 'completed' and receipt.get('http_status') == 200
            and receipt.get('ledger_request_id') == row['request_id']
            and receipt.get('returned_model') == 'gpt-6-astra'
            and receipt.get('reasoning_effort') == 'xhigh'
            and bool(receipt.get('response_id')) and receipt.get('actual_cny_fen') is None,
            'invalid completed unknown-cost hold')
    require(isinstance(receipt.get('started_at'), (int, float))
            and isinstance(receipt.get('finished_at'), (int, float))
            and receipt['finished_at'] >= receipt['started_at'], 'invalid completion times')


def allowed_prior_holds(state, batch):
    allowed = set()
    for prior in batch.get('prior_completed_batches', []):
        prior_batch = reviewed_batch(prior['batch'])
        rows = {key: row for key, row in state['requests'].items() if row.get('batch') == prior['batch']}
        refs = prior['completed_requests']
        require(len(rows) == prior_batch['max_calls'] == len(refs)
                and {r['request_id'] for r in refs} == set(rows),
                'prior batch exact completed count mismatch')
        for ref in refs:
            require(ref['request_id'] not in allowed, 'duplicate prior request')
            completed_hold(rows[ref['request_id']], ref['completion_evidence'])
            allowed.add(ref['request_id'])
    return allowed


class BudgetLedger:
    def __init__(self, path=LEDGER, *, policy_path=POLICY, pricing_path=PRICING):
        self.path = Path(path)
        self.policy_path, self.pricing_path = Path(policy_path), Path(pricing_path)

    @contextmanager
    def transaction(self, initialize=False, *, migrate_cap=False):
        # A stable sidecar inode: never lock the JSON inode that gets replaced.
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            policy = load(self.policy_path)
            require(self.path.resolve() != LEDGER.resolve() or not policy.get("synthetic_test_fixture"),
                    "synthetic policy cannot use production ledger")
            terms = policy_terms(policy)
            if self.path.exists():
                state = load(self.path)  # corruption is fatal, NEVER reset costs
                before = fingerprint(state)
                require(state["schema"] == 1, "ledger schema mismatch")
                require(state["data_kind"] == ("production" if self.path.resolve() == LEDGER.resolve()
                        else "synthetic_offline_test"), "ledger data kind mismatch")
                if migrate_cap:
                    upgrade_terms(state, policy, sha(self.policy_path))
                require(state["terms"] == terms, "ledger policy mismatch; explicit cap migration required")
                spent, held = totals(state)
                require(spent+held <= terms["cap_fen"] or state["halted"], "unexplained budget overrun")
            else:
                require(initialize, "ledger missing; explicit init required")
                state = {"schema": 1, "data_kind": "production" if self.path.resolve() == LEDGER.resolve()
                         else "synthetic_offline_test", "terms": terms, "requests": {},
                         "report_events": {}, "halted": None, "created_at": now()}
                before = fingerprint(state)
            require(state["data_kind"] == ("production" if self.path.resolve() == LEDGER.resolve()
                    else "synthetic_offline_test"), "ledger data kind mismatch")
            yield state, policy
            if fingerprint(state) != before or initialize and not self.path.exists():
                state["updated_at"] = now()
                state["policy_sha256"] = sha(self.policy_path)
                atomic_write(self.path, state)

    def migrate_authorized_cap(self):
        with self.transaction(migrate_cap=True) as (state, _):
            receipt = {"terms": state["terms"], "request_count": len(state["requests"]),
                       "requests_sha256": fingerprint(state["requests"]),
                       "policy_migrations": state.get("policy_migrations", [])}
        return receipt

    def initialize(self):
        with self.transaction(initialize=True):
            pass
        return self.status()

    def status(self):
        with self.transaction() as (state, policy):
            spent, held = totals(state)
            ready, reason = pricing_status(policy, load(self.pricing_path))
            return {"currency": "CNY", "cap_fen": state["terms"]["cap_fen"],
                    "settled_fen": spent, "outstanding_reserved_fen": held,
                    "remaining_uncommitted_fen": state["terms"]["cap_fen"]-spent-held,
                    "request_count": len(state["requests"]), "halted": state["halted"],
                    "pricing_verified": ready, "pricing_blocker": reason,
                    "pending_reports": [r for r in state["report_events"].values() if r["status"] == "pending"],
                    "runtime_api_validated": False, "ledger_only": True}

    def reserve(self, request_id, scope, maxima):
        require(isinstance(request_id, str) and bool(request_id.strip()), "unique request ID required")
        require(isinstance(scope, dict) and all(isinstance(scope.get(k), str) and scope[k].strip()
                for k in ("role", "environment", "branch")), "role/environment/branch required")
        inputs = {"scope": scope, "maxima": maxima}
        fingerprint(inputs)  # reject nonfinite JSON before storing
        with self.transaction() as (state, policy):
            old = state["requests"].get(request_id)
            if old is not None:
                require(old["inputs"] == inputs, "request ID reused with different inputs")
                return {"created": False, **old}
            require(state["halted"] is None, "ledger halted for billing reconciliation")
            price = validate_pricing(policy, load(self.pricing_path))
            amount = worst_case_fen(price, maxima)
            spent, held = totals(state)
            require(spent+held+amount <= state["terms"]["cap_fen"], "shared cap exceeded")
            row = {"request_id": request_id, "inputs": inputs, "reserved_fen": amount,
                   "state": "reserved", "pricing": price, "pricing_hash": fingerprint(price),
                   "created_at": now()}
            state["requests"][request_id] = row
            return {"created": True, **row}

    def begin(self, request_id):
        """Durably mark in-flight BEFORE network dispatch. Repeats must not send."""
        with self.transaction() as (state, policy):
            row = state["requests"][request_id]
            if row["state"] == "inflight":
                return {"transitioned": False, **row}
            require(row["state"] == "reserved", "request is no longer reserved")
            require(state["halted"] is None, "ledger halted")
            price = validate_pricing(policy, load(self.pricing_path))
            require(fingerprint(price) == row["pricing_hash"], "pricing changed; do not dispatch old reservation")
            row.update(state="inflight", begun_at=now())
            return {"transitioned": True, **row}

    def reserve_empirical(self, plan_ref):
        """Reviewed batches, estimated reserve, NOT a price/charge guarantee.

        Input byte limits are only a size proxy, not an input-token bound. Keep
        every unknown charge held. Only explicit approved completed-batch references
        permit continuation while earlier charges remain unknown.
        This does not bypass the original verified-pricing reserve/begin path.
        """
        plan = load(evidence(plan_ref))
        require(plan["schema"] == 1 and plan["mode"] == "empirical_estimate", "invalid estimate plan")
        require(self.path.resolve() != LEDGER.resolve() or not plan.get("synthetic_test_fixture"),
                "synthetic plan cannot use production ledger")
        require(bool(plan["authorization"]) and plan["max_calls"] == 1
                and plan["automatic_retries"] is False, "one authorized call without retries required")
        require(plan["pricing_verified"] is False and plan["hard_cost_bound"] is False,
                "estimate cannot claim verified pricing or hard cost bound")
        require(bool(plan["provider"]) and plan["model"] == "gpt-6-astra"
                and plan["reasoning_effort"] == "xhigh", "required provider/model/effort")
        require(bool(re.fullmatch(r"[a-f0-9]{64}", plan["payload_sha256"])), "payload hash required")
        request_id, scope = plan["request_id"], plan["scope"]
        require(isinstance(request_id, str) and request_id.strip(), "request ID required")
        require(all(isinstance(scope.get(k), str) and scope[k].strip()
                for k in ("role", "environment", "branch")), "scope required")
        sizes = [(integer(plan["max_payload_bytes"], "payload bytes", 1),
                  integer(plan["calibration_input_bytes"], "calibration input bytes", 1)),
                 (integer(plan["max_output_tokens"], "output tokens", 1),
                  integer(plan["calibration_output_tokens"], "calibration output", 1))]
        margin = integer(plan["margin_multiplier"], "margin", 2)
        batch_ref = plan.get("batch")
        parallel = None
        if batch_ref:
            batch = reviewed_batch(batch_ref)
            parallel = parallel_approval(batch)
            if parallel:
                require(scope['branch'] == batch['branch'], 'parallel branch mismatch')
                for key in ('calibration_input_bytes', 'calibration_output_tokens', 'margin_multiplier'):
                    require(plan[key] == batch[key], 'parallel calibration/margin mismatch: '+key)
            require(bool(batch["authorization"]) and batch["model"] == plan["model"]
                    and batch["provider"] == plan["provider"]
                    and batch["calibration_request_id"] == plan["calibration_request_id"], "batch mismatch")
            require(plan["max_payload_bytes"] <= batch["max_payload_bytes"]
                    and plan["max_output_tokens"] <= batch["max_output_tokens"], "batch input/output limit")
            if parallel or batch['max_calls'] > 6:
                index = integer(plan.get('call_index'), 'batch call index', 1)
                require(index <= batch['max_calls'] and request_id == f"{batch['batch_id']}-call-{index:02d}",
                        'approved batch call index/ID limit')
        inputs = {"scope": scope, "estimate_plan": plan_ref}
        with self.transaction() as (state, _):
            old = state["requests"].get(request_id)
            if old is not None:
                require(old["inputs"] == inputs, "request ID reused with different estimate plan")
                return {"created": False, **old}
            calibration = state["requests"][plan["calibration_request_id"]]
            require(calibration["state"] == "settled" and calibration["actual_fen"] > 0,
                    "settled calibration required")
            bill = load(evidence(calibration["settlement"]["receipt"]))
            require(bill["provider"] == plan["provider"] and bill["model"] == plan["model"],
                    "calibration provider/model mismatch")
            base = calibration["actual_fen"]*margin
            amount = max([base]+[(base*n+d-1)//d for n, d in sizes])
            spent, held = totals(state)
            pending_rows = [r for r in state["requests"].values() if r["state"] in ("reserved", "inflight")]
            prior_ids = allowed_prior_holds(state, batch) if batch_ref else set()
            require(not pending_rows or batch_ref and all(r.get("batch") == batch_ref
                    or r['request_id'] in prior_ids
                    or parallel and parallel_pending_allowed(r, batch, parallel) for r in pending_rows),
                    "unsettled request: keep hold; only the same reviewed batch may continue")
            if batch_ref:
                if parallel or batch['max_calls'] > 6:
                    for row in pending_rows:
                        if row.get('batch') == batch_ref:
                            completed_hold(row, row.get('completion_evidence'))
                    require(index == 1+sum(r.get('batch') == batch_ref for r in state['requests'].values()),
                            'approved batch requires consecutive call index')
                require(sum(r.get("batch") == batch_ref for r in state["requests"].values()) < batch["max_calls"],
                        "batch call limit exhausted")
            pending = "historical_calibration_cost_recorded; empirical_reservation_adapter_pending"
            require(state["halted"] in (None, pending), "ledger halted for reconciliation")
            require(spent+held+amount <= state["terms"]["cap_fen"], "shared cap exceeded")
            if state["halted"] == pending:
                state["empirical_activation"] = {"previous_halt": pending, "plan": plan_ref, "at": now()}
                state["halted"] = None
            row = {"request_id": request_id, "inputs": inputs, "reserved_fen": amount,
                   "state": "reserved", "reservation_basis": "empirical_estimate_not_hard_bound",
                   "pricing": {"provider": plan["provider"], "model": plan["model"]},
                   "pricing_verified": False, "hard_cost_bound": False, "created_at": now()}
            if batch_ref:
                row["batch"] = batch_ref
            state["requests"][request_id] = row
            return {"created": True, **row}

    def begin_empirical(self, request_id, payload_sha256):
        """Only the one hash-pinned payload may dispatch, once, after reservation."""
        with self.transaction() as (state, _):
            row = state["requests"][request_id]
            require(row.get("reservation_basis") == "empirical_estimate_not_hard_bound", "not empirical")
            plan = load(evidence(row["inputs"]["estimate_plan"]))
            require(plan["payload_sha256"] == payload_sha256, "payload changed")
            if row.get('batch'):
                batch = reviewed_batch(row['batch'])
                parallel = parallel_approval(batch)
                prior_ids = allowed_prior_holds(state, batch)
                if parallel or batch['max_calls'] > 6:
                    for other in state['requests'].values():
                        if other['request_id'] == request_id or other['state'] not in ('reserved', 'inflight'):
                            continue
                        require(other.get('batch') == row['batch'] or other['request_id'] in prior_ids
                                or parallel and parallel_pending_allowed(other, batch, parallel),
                                'foreign unsettled request before dispatch')
                        if other.get('batch') == row['batch']:
                            completed_hold(other, other.get('completion_evidence'))
            if row["state"] == "inflight":
                return {"transitioned": False, **row}
            require(row["state"] == "reserved" and state["halted"] is None, "not dispatchable")
            row.update(state="inflight", begun_at=now())
            return {"transitioned": True, **row}

    def cancel(self, request_id, reason):
        require(isinstance(reason, str) and reason.strip(), "cancellation reason required")
        with self.transaction() as (state, _):
            row = state["requests"][request_id]
            if row["state"] == "cancelled":
                return {"changed": False, **row}
            require(row["state"] == "reserved", "inflight/settled requests cannot be cancelled or silently released")
            row.update(state="cancelled", cancellation_reason=reason, cancelled_at=now())
            return {"changed": True, **row}

    def settle(self, request_id, billing_ref):
        receipt = load(evidence(billing_ref))
        require(self.path.resolve() != LEDGER.resolve() or not receipt.get("synthetic_test_fixture"),
                "synthetic billing receipt cannot settle a production request")
        require(receipt["request_id"] == request_id and receipt["final"] is True,
                "definitive per-request billing receipt required")
        actual = integer(receipt["actual_cny_fen"], "actual CNY fen")
        require(receipt["currency"] == "CNY" and bool(receipt["conversion_basis"]), "settlement conversion basis required")
        require(bool(receipt["billing_event_id"]), "unique billing event required")
        binding = {"receipt": billing_ref, "content_sha256": fingerprint(receipt)}
        with self.transaction() as (state, _):
            row = state["requests"][request_id]
            if row["state"] == "settled":
                require(row["settlement"] == binding, "conflicting repeated settlement")
                return {"changed": False, **row}
            require(row["state"] == "inflight", "only an in-flight request can settle")
            require(receipt["provider"] == row["pricing"]["provider"]
                    and receipt["model"] == row["pricing"]["model"], "billing provider/model mismatch")
            require(not any(r.get("billing_event_id") == receipt["billing_event_id"] for r in state["requests"].values()),
                    "billing event already used")
            prior, _ = totals(state)
            row.update(state="settled", actual_fen=actual, settlement=binding,
                       billing_event_id=receipt["billing_event_id"], settled_at=now())
            if actual > row["reserved_fen"]:
                # Preserve the real amount if a future adapter violates its bound.
                # Halt further calls instead of clamping or hiding incurred cost.
                state["halted"] = "actual_charge_exceeded_reservation; reconcile_adapter_and_billing"
            spent, held = totals(state)
            for threshold in state["terms"]["thresholds_fen"]:
                if prior < threshold <= spent:
                    key = str(threshold)
                    require(key not in state["report_events"], "duplicate reporting event")
                    state["report_events"][key] = {"threshold_fen": threshold, "status": "pending",
                        "settled_fen_at_crossing": spent, "reserved_fen_at_crossing": held,
                        "remaining_uncommitted_fen_at_crossing": state["terms"]["cap_fen"]-spent-held,
                        "trigger_request": request_id, "created_at": now(),
                        "required_content": ["cumulative_and_remaining_cost", "task_progress", "independent_success_counts", "failure_findings"]}
            return {"changed": True, **row}

    def acknowledge_report(self, threshold_fen, delivery_ref):
        integer(threshold_fen, "threshold", 1)
        record = load(evidence(delivery_ref))
        require(self.path.resolve() != LEDGER.resolve() or not record.get("synthetic_test_fixture"),
                "synthetic report receipt cannot acknowledge a production event")
        require(record["delivered"] is True and record["recipient"] == "user"
                and record["threshold_fen"] == threshold_fen and record["delivery_id"],
                "actual user-visible report delivery evidence required")
        require(all(record["content"].get(k) for k in (
            "cumulative_and_remaining_cost", "task_progress", "independent_success_counts", "failure_findings")),
            "report content incomplete")
        with self.transaction() as (state, _):
            event = state["report_events"][str(threshold_fen)]
            if event["status"] == "reported":
                require(event["delivery_ref"] == delivery_ref, "conflicting report acknowledgement")
                return dict(event)
            event.update(status="reported", delivery_ref=delivery_ref, reported_at=now())
            return dict(event)  # never change cap, settled costs or other pending events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Mutations of actual requests are library-only until a provider adapter is validated.
    parser.add_argument("command", choices=("init", "status", "migrate-cap", "load-receipt"))
    args = parser.parse_args()
    book = BudgetLedger()
    result = {"init": book.initialize, "status": book.status,
              "migrate-cap": book.migrate_authorized_cap, "load-receipt": loaded_runtime}[args.command]()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
