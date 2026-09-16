"""Synthetic unit fixtures only. No real success, simulator, model or API call.

Production CLI paths are fixed and cannot use these fixtures. Positive tests
exercise the audit logic with an explicit fake video metadata probe; they are
not physical trials or video-authenticity validation.
"""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

import ikea_gate as g
from budget_test_fixtures import policy_fixture, pricing_fixture


class GateTests(unittest.TestCase):
    def setUp(self):
        fixture_root = g.OUT / "synthetic-tests"
        fixture_root.mkdir(exist_ok=True)
        # Kept on disk: diagnostics are not removed on teardown.
        self.root = Path(tempfile.mkdtemp(prefix="synthetic-", dir=fixture_root))
        self.campaign = self.root/"campaign"
        self.campaign.mkdir()
        self.registry = {"schema": 1, "data_kind": "real_physics", "episodes": []}
        self.api = {"user_confirmed": False}
        self.budget_policy = policy_fixture()
        self.n = 81
        (self.root/"SYNTHETIC_ONLY.json").write_text(json.dumps({
            "synthetic": True, "physical_trials": 0, "model_calls": 0,
            "video_probe": "stub", "production_enrollment_allowed": False}))
        self.proof = self.root/"synthetic-host-proof.txt"
        self.proof.write_text("SYNTHETIC TEST HOST PROVENANCE. NOT A REAL RESET.\n")
        (self.root/"user-authorizations").mkdir()
        self.approval = self.root/"user-authorizations/synthetic-reply.txt"
        self.approval.write_text("SYNTHETIC APPROVAL FIXTURE ONLY. NOT A USER ANSWER.\n")

    def probe(self, path):
        return {"nb_frames": str((self.n+1)//2), "duration": str(((self.n+1)//2)/25),
                "r_frame_rate": "25/1"}

    def make(self, index=1):
        e = self.campaign/f"episode-{index:04d}"
        (e/"video").mkdir(parents=True)
        initial = {"articulate_joint_1": [-math.pi/18],
                   "floating_base_joint": [index*.0001, 0, .76, 1, 0, 0, 0]}
        rows = []
        for i in range(self.n):
            j = copy.deepcopy(initial)
            if i >= 10:
                j["articulate_joint_1"][0] += math.pi/6 + .02
            rows.append({"sim_s": 5+i*.02, "native_outcome": "success" if i == 80 else "in_progress",
                         "status": {"status": "active", "command_id": f"cmd-{index}"},
                         "host_render_state": {"qpos_by_joint": j, "hand_door_contact": i == 5}})
        (e/"video/robot_trace.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
        (e/"video/episode.mp4").write_text(f"SYNTHETIC STUB VIDEO {index}; NOT REAL PHYSICS")
        (e/"SKILL.md").write_text("SYNTHETIC TEST SKILL")
        result = {"success": True, "native_outcome": "success", "episode_id": e.name,
                  "error": None, "skill_updated": True, "stop_reason": "native_success",
                  "model": "gpt-6-astra", "effort": "xhigh", "actions": 1, "codex_turns": 1,
                  "starting_skill_sha256": g.digest(e/"SKILL.md"), "sim_s": 1.6}
        g.atomic_json(e/"result.json", result)
        g.atomic_json(e/"turn_001.json", {"status": "completed"})
        g.atomic_json(e/"video/render_manifest.json", {"actor_access": False, "physics": "MuJoCo",
            "runtime_source_sha256": {"synthetic_controller.py": "fixture"},
            "initial_render_state": {"qpos_by_joint": initial}})
        g.atomic_json(e/"video/scene_setup.json", {"variant": g.VARIANT,
            "pd_profile": "checkpoint", "actor_access": False, "opening_dot_after": .45})
        receipt = {"schema": 1, "data_kind": "real_physics", "synthetic_fixture_only": True,
            "host_reviewer_thread": g.THREAD, "contract": g.CONTRACT,
            "mode": "formal_direct_simulation", "episode": str(e),
            "reset": {"method": "fresh_environment_reset", "reset_id": f"synthetic-reset-{index}",
                "seed": index, "launch": {"boot_id": "synthetic", "pid": 100+index, "start_ticks": index}},
            "provenance_review": dict.fromkeys(("independent_reset", "full_episode", "no_replay",
                "no_diagnostic_initial_state", "single_action_writer", "original_physics"), True),
            "host_evidence": [{"path": str(self.proof.relative_to(g.ROOT)), "sha256": g.digest(self.proof)}],
            "runtime_source_sha256": {"synthetic_controller.py": "fixture"}}
        self.seal(e, receipt)
        return e, receipt

    def seal(self, e, receipt):
        receipt["evidence_sha256"] = {n: g.digest(e/n) for n in (*g.REQUIRED, "turn_001.json") if (e/n).exists()}
        p = self.root/f"{e.name}-receipt.json"
        g.atomic_json(p, receipt)
        entry = {"receipt": p.name, "sha256": g.digest(p)}
        self.registry["episodes"] = [r for r in self.registry["episodes"] if r["receipt"] != p.name]+[entry]

    def evaluate(self):
        return g.evaluate(self.registry, self.api, base=self.root, campaign=self.campaign,
                          probe=self.probe, budget_policy=self.budget_policy)

    def mutate_json(self, e, receipt, name, change):
        value = g.read(e/name)
        change(value)
        g.atomic_json(e/name, value)
        self.seal(e, receipt)

    def mutate_trace(self, e, receipt, change):
        p = e/"video/robot_trace.jsonl"
        rows = [json.loads(s) for s in p.read_text().splitlines()]
        change(rows)
        p.write_text("".join(json.dumps(r)+"\n" for r in rows))
        self.seal(e, receipt)

    def rejected(self):
        state = self.evaluate()
        self.assertEqual(state["audited_independent_successes"], 0, state)
        self.assertFalse(state["physical_gate_passed"])
        self.assertTrue(state["rejected"])

    # Ordered rejection suite runs before any three-positive acceptance test.
    def test_01_failure_self_claim(self):
        e, r = self.make()
        self.mutate_json(e, r, "result.json", lambda x: x.update(native_outcome="failure"))
        self.rejected()

    def test_02_duplicate_episode(self):
        self.make()
        self.registry["episodes"] *= 3
        s = self.evaluate()
        self.assertEqual(s["audited_independent_successes"], 1)
        self.assertFalse(s["physical_gate_passed"])
        self.assertEqual(len(s["rejected"]), 2)

    def test_03_missing_evidence(self):
        e, r = self.make()
        # Preserve the diagnostic file; remove only its hash from the fixture receipt.
        del r["evidence_sha256"]["video/robot_trace.jsonl"]
        p = self.root/f"{e.name}-receipt.json"
        g.atomic_json(p, r)
        self.registry["episodes"][0]["sha256"] = g.digest(p)
        self.rejected()

    def test_04_replay(self):
        e, r = self.make()
        r["mode"] = "replay"
        self.seal(e, r)
        self.rejected()

    def test_05_no_contact(self):
        e, r = self.make()
        self.mutate_trace(e, r, lambda rows: [x["host_render_state"].update(hand_door_contact=False) for x in rows])
        self.rejected()

    def test_06_no_dwell(self):
        e, r = self.make()
        def change(rows):
            for row in rows[10:60]:
                row["host_render_state"]["qpos_by_joint"]["articulate_joint_1"] = [-math.pi/18]
        self.mutate_trace(e, r, change)
        self.rejected()

    def test_07_incomplete_reasoning(self):
        e, r = self.make()
        self.mutate_json(e, r, "turn_001.json", lambda x: x.update(status="in_progress"))
        self.rejected()

    def test_08_changed_evidence(self):
        e, r = self.make()
        (e/"SKILL.md").write_text("CHANGED SYNTHETIC SKILL")
        self.rejected()

    def test_09_fall(self):
        e, r = self.make()
        def change(rows):
            rows[20]["host_render_state"]["qpos_by_joint"]["floating_base_joint"][2] = .2
        self.mutate_trace(e, r, change)
        self.rejected()

    def test_10_duplicate_reset_and_recording(self):
        self.make()
        e, r = self.make(2)
        r["reset"]["reset_id"] = "synthetic-reset-1"
        self.seal(e, r)
        self.assertEqual(self.evaluate()["audited_independent_successes"], 1)
        r["reset"]["reset_id"] = "synthetic-reset-2"
        (e/"video/episode.mp4").write_bytes((self.campaign/"episode-0001/video/episode.mp4").read_bytes())
        self.seal(e, r)
        self.assertEqual(self.evaluate()["audited_independent_successes"], 1)

    def test_11_missing_ticks(self):
        e, r = self.make()
        self.mutate_trace(e, r, lambda rows: rows.pop(22))
        self.rejected()

    def test_12_no_provenance(self):
        e, r = self.make()
        r["host_evidence"] = []
        self.seal(e, r)
        self.rejected()

    def test_13_short_video(self):
        self.make()
        self.probe = lambda _: {"nb_frames": "1", "duration": ".04", "r_frame_rate": "25/1"}
        self.rejected()

    def test_14_production_rejects_fixture_paths(self):
        e, r = self.make()
        with self.assertRaises(g.Rejected):
            g.audit_episode(e, r)

    def test_15_diagnostic(self):
        e, r = self.make()
        r["provenance_review"]["no_diagnostic_initial_state"] = False
        self.seal(e, r)
        self.rejected()

    def test_16_authorized_budget_not_overridden_by_api_config(self):
        self.api = {"schema": 1, "user_confirmed": True, "source": "synthetic_provider",
                    "budget_cap": float("inf"), "currency": "USD",
                    "user_authorization": {"path": self.approval.name, "sha256": g.digest(self.approval)}}
        self.assertFalse(self.evaluate()["api_metadata_confirmed"])
        self.assertTrue(self.evaluate()["budget_authorized"])
        self.assertEqual(self.evaluate()["shared_cap_fen"], 1_000_000)

    def test_17_malformed_host_state(self):
        e, r = self.make()
        self.mutate_trace(e, r, lambda rows: rows[20].update(status=None))
        self.rejected()

    def test_18_duplicate_process_identity(self):
        _, first = self.make()
        e, r = self.make(2)
        r["reset"]["launch"] = first["reset"]["launch"]
        self.seal(e, r)
        state = self.evaluate()
        self.assertEqual(state["audited_independent_successes"], 1)
        self.assertIn("duplicate launch_id", state["rejected"][0]["reason"])

    def test_19_nonfinite_physics(self):
        e, r = self.make()
        self.mutate_trace(e, r, lambda rows: rows[20].update(sim_s=float("nan")))
        self.rejected()

    def test_20_unverified_pricing_cannot_unlock(self):
        self.api = pricing_fixture(self.proof)
        self.api["verification_status"] = "pending"
        self.assertFalse(self.evaluate()["api_metadata_confirmed"])

    def test_90_three_synthetic_positives_wait_api(self):
        for i in range(1, 4):
            self.make(i)
        s = self.evaluate()
        self.assertEqual(s["audited_independent_successes"], 3, s)
        self.assertEqual(s["state"], "waiting_api_configuration")
        self.assertFalse(s["launch_performed"])

    def test_91_synthetic_config_registers_only(self):
        for i in range(1, 4):
            self.make(i)
        self.api = pricing_fixture(self.proof)
        s = self.evaluate()
        self.assertEqual(s["state"], "eligible_registered_only")
        self.assertFalse(s["launch_performed"])
        self.assertEqual(s["model_calls"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
