import tempfile
import unittest
from pathlib import Path

from test_tool_host import FakeBackend, response
from tools.codex_direct_sim import EvaluationHost
from rsi.live import tabletop_model


class DirectPilotTests(unittest.TestCase):
    def test_table_clearance_change_preserves_cube_position(self):
        a, b = tabletop_model(), tabletop_model(table_only_offset_x=.05)
        self.assertEqual(tuple(a.body('diagnostic_cube').pos), tuple(b.body('diagnostic_cube').pos))
        self.assertAlmostEqual(b.geom('diagnostic_table').pos[0]-a.geom('diagnostic_table').pos[0], .05)
        self.assertAlmostEqual(b.geom('table_leg_0').pos[0]-a.geom('table_leg_0').pos[0], .05)

    def test_multi_waypoint_rejection_does_not_execute(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'run'
            host = EvaluationHost(root, FakeBackend)
            packet = host.dispatch('loco_start', {'task': 'test', 'output_dir': str(root/'episode')})
            before = host.backend.count
            action = response()
            action['trajectory'] *= 2
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                host.dispatch('scalebfm_act', {'observation_path': packet['observation_path'],
                    'response': action, 'output_dir': str(root/'rejected')})
            self.assertEqual(host.backend.count, before)
            self.assertEqual(host.action_count, 0)

    def test_three_tracking_timeouts_finish_without_native_success(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'run'
            host = EvaluationHost(root, FakeBackend)
            packet = host.dispatch('loco_start', {'task': 'test', 'output_dir': str(root/'episode')})
            host.backend.tick = lambda: setattr(host.backend, 'state', 'timed_out')
            for i in range(3):
                packet = host.dispatch('scalebfm_act', {'observation_path': packet['observation_path'],
                    'response': response(), 'output_dir': str(root/f'action-{i}')})
            self.assertTrue(packet['rollout_finished'])
            self.assertEqual(packet['stop_reason'], 'three_consecutive_tracking_timeouts')
            self.assertNotEqual(packet['native_outcome'], 'success')
            with self.assertRaisesRegex(ValueError, 'finished'):
                host.dispatch('scalebfm_act', {})
