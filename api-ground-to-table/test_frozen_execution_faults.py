"""Frozen host error semantics: fake physics only, no API or credentials."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent
FROZEN = ROOT.parent/'codex-account-2/workspace/ground-to-table/provenance/episodes/episode-0007'
sys.path[:0] = [str(FROZEN), str(FROZEN.parents[2]), '/home/galbot/lizekai/Loco_manip/locomanip/src']
from tools.learn_grasp_skill import LearningHost


class FrozenFaultTests(unittest.TestCase):
    def test_faults_remain_terminal_nonretryable(self):
        for advances, pending in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(advances=advances, pending=pending), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                host = LearningHost(Path(directory), None, 'frozen-fault-test', 0,
                                    geometry_provider=None, support_plane_z_m=None)
                backend = SimpleNamespace(active=None, data=SimpleNamespace(time=5.), reason=None,
                                          continuous_chunks_enabled=True)
                cancellations = []
                def cancel():
                    cancellations.append(True)
                    backend.active = None
                backend.cancel = cancel
                def execute(*args):
                    backend.data.time += .02 if advances else 0
                    backend.active = 'test-command' if pending else None
                    raise RuntimeError('synthetic backend fault')
                host.backend = backend
                host.harness = SimpleNamespace(scalebfm_act=execute,
                    evaluator=SimpleNamespace(outcome=lambda b: 'in_progress'))
                arguments = {'observation_path': str(host.rollout_root/'fake.json'),
                    'response': {'trajectory': [{}]}, 'output_dir': str(host.rollout_root/'fault')}
                result = host.dispatch('scalebfm_act', arguments)
                self.assertTrue(host.finished)
                self.assertEqual(host.stop_reason, 'control_transaction_error')
                self.assertFalse(result['retryable'])
                self.assertEqual(result['no_execution'], not advances)
                self.assertEqual(host.actions, int(advances))
                self.assertEqual(len(cancellations), int(pending))
                self.assertTrue((host.rollout_root/'fault/tool_failure.json').exists())
                with self.assertRaisesRegex(ValueError, 'Episode ended'):
                    host.dispatch('scalebfm_act', arguments)


if __name__ == '__main__':
    unittest.main(verbosity=2)
