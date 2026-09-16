"""Finish-gate contract tests with fake action receipts; no simulator/model runs."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from rsi.evaluator import SimpleNativeEvaluator
from tools.learn_grasp_skill import LearningHost


class FinishGateTests(unittest.TestCase):
    def make_host(self, directory):
        host = LearningHost(Path(directory), None, 'finish-gate-unit', 0,
                            geometry_provider=None, support_plane_z_m=None,
                            max_episode_steps=100)
        host.backend = SimpleNamespace(
            active=None, reason=None, _native_task_success=False,
            data=SimpleNamespace(time=5.), status=lambda: {'status': 'idle'})
        evaluator = SimpleNativeEvaluator()
        evaluator.reset(host.backend)
        host.harness = SimpleNamespace(evaluator=evaluator)
        for _ in range(3):
            self.action_receipt(host)
        return host

    def action_receipt(self, host):
        # Exercise the real LearningHost dispatch/status/budget path while
        # replacing only the parent physical dispatch with a fake receipt.
        output = host.rollout_root/f'call_{host.calls:04d}'
        output.mkdir()

        def execute(name, arguments):
            self.assertEqual(name, 'scalebfm_act')
            host.backend.data.time += .02
            host.harness.evaluator.update(host.backend)
            host.harness.latest_path = output/'observation.json'
            host.harness.latest_path.write_text('{"source": "unit-test fixture"}')
            return {'observation_path': str(host.harness.latest_path), 'execution': []}

        with patch('rsi.tool_host.LocoManipToolHost.dispatch', side_effect=execute) as physics:
            result = host.dispatch('scalebfm_act', {
                'output_dir': str(output),
                'response': {'trajectory': [{}]}})
            physics.assert_called_once()
        return result

    def stall_arguments(self, host):
        return {
            'reason': 'Three completed actions have not shown visible task progress.',
            'next_hypothesis': 'Adjust approach clearance and test a bounded action now.',
            'evidence_paths': [str(host.rollout_root/'history.jsonl')]}

    def test_stall_keeps_safe_attempt_open_and_next_hypothesis_is_testable(self):
        with tempfile.TemporaryDirectory() as directory:
            host = self.make_host(directory)
            self.assertEqual(host.actions, 3)
            self.assertIsNone(host.backend.reason)
            self.assertIsNone(host.backend.active)
            last = json.loads((host.rollout_root/'call_0002/tool_result.json').read_text())
            self.assertEqual(last['remaining_steps'], 97)
            self.assertFalse(last['rollout_finished'])
            arguments = self.stall_arguments(host)
            before = (host.actions, host.calls, host.backend.data.time)
            with patch('rsi.tool_host.LocoManipToolHost.dispatch') as physics:
                result = host.dispatch('finish_attempt', arguments)
                physics.assert_not_called()
            # This is the original bug: the old host returns True here.
            self.assertFalse(result['rollout_finished'])
            self.assertFalse(host.finished)
            self.assertIsNone(host.stop_reason)
            self.assertIsNone(result['stop_reason'])
            self.assertEqual(result['native_outcome'], 'in_progress')
            self.assertEqual(result['next_call']['tool'], 'scalebfm_act')
            self.assertEqual(result['observation_path'], str(host.harness.latest_path))
            self.assertEqual(result['next_call']['observation_path'], result['observation_path'])
            self.assertEqual(result['next_hypothesis'], arguments['next_hypothesis'])
            self.assertEqual(before, (host.actions, host.calls, host.backend.data.time))
            with self.assertRaisesRegex(ValueError, 'Finish this physical episode'):
                host.dispatch('skill_update', {'markdown': 'candidate', 'lesson': 'stall',
                                               'evidence_paths': arguments['evidence_paths']})

            # Repeated diagnostics preserve earlier evidence and do not consume physics.
            second = host.dispatch('finish_attempt', dict(arguments,
                next_hypothesis='Reobserve the alignment before the next bounded test.'))
            rows = [json.loads(line) for line in
                    (host.rollout_root/'policy_stall.jsonl').read_text().splitlines()]
            self.assertEqual(rows, [result, second])
            self.assertFalse((host.rollout_root/'policy_stop.json').exists())
            self.assertEqual(before, (host.actions, host.calls, host.backend.data.time))
            continued = self.action_receipt(host)
            self.assertEqual(host.actions, 4)
            self.assertEqual(continued['remaining_steps'], 96)
            self.assertFalse(continued['rollout_finished'])

    def test_native_success_and_safety_failure_still_end_after_stall(self):
        for native in ('success', 'failure'):
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                host = self.make_host(directory)
                host.dispatch('finish_attempt', self.stall_arguments(host))
                if native == 'success':
                    host.backend._native_task_success = True
                else:
                    host.backend.reason = 'unsafe_posture'
                result = self.action_receipt(host)
                self.assertTrue(result['rollout_finished'])
                self.assertEqual(result['native_outcome'], native)
                self.assertEqual(result['stop_reason'], 'native_'+native)
                self.assertEqual(result['next_call']['tool'], 'skill_update')
                self.assertIn(str(host.rollout_root/'policy_stall.jsonl'),
                              result['next_call']['suggested_existing_evidence'])
                with patch('rsi.tool_host.LocoManipToolHost.dispatch') as physics:
                    with self.assertRaisesRegex(ValueError, 'Episode ended'):
                        host.dispatch('scalebfm_act', {})
                    physics.assert_not_called()
                host.memory = Mock()
                host.memory.update.return_value = {'native_outcome': native}
                revision = host.dispatch('skill_update', {
                    'markdown': 'unit fixture', 'lesson': 'unit fixture',
                    'evidence_paths': result['next_call']['suggested_existing_evidence']})
                self.assertTrue(host.skill_updated)
                self.assertEqual(revision['native_outcome'], native)
                self.assertEqual(host.memory.update.call_args.kwargs['outcome'], native)

    def test_physical_budget_still_ends_in_progress_attempt_after_stall(self):
        with tempfile.TemporaryDirectory() as directory:
            host = self.make_host(directory)
            host.dispatch('finish_attempt', self.stall_arguments(host))
            host.backend.data.time = host.episode_start_sim_s + 99*.02
            result = self.action_receipt(host)
            self.assertTrue(result['rollout_finished'])
            self.assertEqual(result['native_outcome'], 'in_progress')
            self.assertEqual(result['stop_reason'], 'episode_step_budget')
            self.assertEqual(result['remaining_steps'], 0)
            self.assertEqual(result['next_call']['tool'], 'skill_update')
            saved = json.loads((host.rollout_root/'call_0003/tool_result.json').read_text())
            self.assertEqual(saved, result)

    def test_runtime_fault_after_stall_propagates_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            host = self.make_host(directory)
            host.dispatch('finish_attempt', self.stall_arguments(host))
            with patch('rsi.tool_host.LocoManipToolHost.dispatch',
                       side_effect=RuntimeError('physics transport lost')) as physics:
                with self.assertRaisesRegex(RuntimeError, 'physics transport lost'):
                    host.dispatch('scalebfm_act', {'response': {'trajectory': [{}]}})
                physics.assert_called_once()
            self.assertEqual(host.actions, 3)

    def test_finish_request_during_active_action_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            host = self.make_host(directory)
            host.backend.active = object()
            with self.assertRaisesRegex(ValueError, 'three completed physical actions'):
                host.dispatch('finish_attempt', self.stall_arguments(host))
            self.assertFalse(host.finished)
            self.assertFalse((host.rollout_root/'policy_stall.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
