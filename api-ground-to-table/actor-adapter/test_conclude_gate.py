"""Conclude semantics only: fake host, no simulator/credentials/network."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from actor import Gate
from test_actor import Host, decision


class ConcludeHost(Host):
    def __init__(self, root):
        super().__init__(root)
        self.backend = SimpleNamespace(active=None,reason=None)
        self.native = 'in_progress'
        self.stop_reason = self.runtime_error = self.initialization_error = None
        self.harness.evaluator = SimpleNamespace(outcome=lambda backend:self.native)
        self.harness.latest_path.write_text('{"images":[],"robot_state":"current"}')
        self.actions = 3
    def dispatch(self, name, arguments):
        if name == 'skill_update':
            if not self.finished: raise ValueError('Cannot revise before terminal')
            self.calls.append((name,arguments))
            return {'version':1}
        if self.finished: raise ValueError('Episode ended; no physical retry')
        return super().dispatch(name,arguments)
    def next_call(self):
        return {'tool':'skill_update' if self.finished else 'scalebfm_act',
                'observation_path':str(self.harness.latest_path)}


class ConcludeSemantics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        self.host = ConcludeHost(self.root)
        self.gate = Gate(self.host)
    def tearDown(self): self.temp.cleanup()
    def arguments(self, **changes):
        return dict(reason='Still approaching; task incomplete',next_hypothesis='Adjust visible clearance',
                    revised_skill='',lesson='Need a new test',public_decision=decision()) | changes

    def test_safe_stall_keeps_episode_open_and_next_action_executes(self):
        packet = self.gate.dispatch('conclude',self.arguments())
        self.assertFalse(self.host.finished)  # Original premature-finish regression.
        self.assertFalse(self.gate.concluded)
        self.assertFalse(packet['rollout_finished'])
        self.assertEqual(packet['native_outcome'],'in_progress')
        self.assertIsNone(packet['stop_reason'])
        self.assertEqual(packet['observation']['robot_state'],'current')
        self.assertEqual(packet['observation_path'],str(self.host.harness.latest_path))
        self.assertEqual(packet['next_call']['tool'],'scalebfm_act')
        self.assertEqual(self.host.actions,3)
        self.gate.dispatch('scalebfm_act',{'response':{},'public_decision':decision()})
        self.assertEqual(self.host.actions,4)

    def test_repeated_stalls_append_and_revision_is_deferred(self):
        for hypothesis in ('Adjust clearance','Inspect wrist alignment'):
            packet = self.gate.dispatch('conclude',self.arguments(
                next_hypothesis=hypothesis,revised_skill='A candidate, not a terminal revision'))
            self.assertFalse(self.gate.concluded)
            self.assertTrue(packet['skill_update_deferred'])
        rows = [json.loads(line) for line in (self.root/'policy_stall.jsonl').read_text().splitlines()]
        self.assertEqual([r['next_hypothesis'] for r in rows],['Adjust clearance','Inspect wrist alignment'])
        self.assertEqual(self.host.actions,3)
        self.assertEqual(self.host.calls,[])

    def test_native_safety_and_physical_budget_keep_terminal_stop(self):
        cases = [('success',None,'native_success'),('failure',None,'native_failure'),
                 ('in_progress','diagnostic_stability_stop','native_failure'),
                 ('in_progress',None,'episode_step_budget')]
        for native,reason,stop in cases:
            with self.subTest(stop=stop,reason=reason):
                self.host.native=native; self.host.backend.reason=reason
                self.host.finished=True; self.host.stop_reason=stop
                gate=Gate(self.host)
                packet=gate.dispatch('conclude',self.arguments(revised_skill='terminal candidate'))
                self.assertTrue(gate.concluded)
                self.assertTrue(packet['rollout_finished'])
                self.assertEqual(packet['stop_reason'],stop)
                self.assertEqual(self.host.stop_reason,stop)
                self.assertEqual(self.host.calls[-1][0],'skill_update')
                with self.assertRaises(ValueError):
                    gate.dispatch('scalebfm_act',{'response':{},'public_decision':decision()})

    def test_existing_system_fault_remains_terminal_and_no_retry(self):
        self.host.runtime_error={'retryable':False,'rollout_finished':True}
        self.host.finished=True; self.host.stop_reason='control_transaction_error'
        packet=self.gate.dispatch('conclude',self.arguments())
        self.assertTrue(packet['rollout_finished'])
        self.assertEqual(packet['stop_reason'],'control_transaction_error')
        with self.assertRaises(ValueError):
            self.gate.dispatch('scalebfm_act',{'response':{},'public_decision':decision()})
        self.assertEqual(self.host.actions,3)


if __name__ == '__main__': unittest.main()
