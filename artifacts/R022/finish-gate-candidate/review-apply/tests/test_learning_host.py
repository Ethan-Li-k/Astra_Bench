import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.learn_grasp_skill import LearningHost


class LearningHostTests(unittest.TestCase):
    def test_partial_start_capture_failure_is_terminal_not_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            factory = unittest.mock.Mock(return_value=SimpleNamespace())
            capture = unittest.mock.Mock(side_effect=ValueError('renderer initialization failed'))
            host = LearningHost(Path(directory), None, 'capture-failure', 0,
                                backend_factory=factory,image_capture_factory=capture)
            result = host.dispatch('loco_start', {'task':'test',
                'output_dir':str(host.rollout_root/'episode')})
            self.assertFalse(result['retryable'])
            self.assertTrue(result['rollout_finished'])
            self.assertIsNotNone(host.backend)
            self.assertIsNone(host.harness)
            self.assertEqual(result['next_call']['tool'],'skill_update')
            self.assertEqual(factory.call_count,1)
            self.assertEqual(host.actions,0)

    def test_initialization_failure_ends_without_retry_and_allows_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            from rsi.skill_learning import SkillMemory
            root = Path(directory)
            skill = root/'SKILL.md'
            skill.write_text('---\nname: loco-manip-direct\ndescription: Test.\n---\nObserve then act.\n')
            memory = SkillMemory(root/'memory', skill)
            factory = unittest.mock.Mock(side_effect=ValueError('duplicate mesh'))
            host = LearningHost(root/'episode', memory, 'init-test', 0,
                                backend_factory=factory)
            arguments = {'task':'test', 'output_dir':str(host.rollout_root/'episode')}
            result = host.dispatch('loco_start', arguments)
            self.assertFalse(result['retryable'])
            self.assertTrue(result['rollout_finished'])
            self.assertEqual(result['native_outcome'], 'not_started')
            self.assertEqual(result['next_call']['tool'], 'skill_update')
            with self.assertRaisesRegex(ValueError, 'Episode ended'):
                host.dispatch('loco_start', arguments)
            self.assertEqual(factory.call_count, 1)
            revision = host.dispatch('skill_update', {'markdown':skill.read_text(),
                'lesson':'Initialization failed before observations; no policy evidence.',
                'evidence_paths':result['next_call']['suggested_existing_evidence']})
            self.assertEqual(revision['native_outcome'], 'not_started')
            self.assertTrue(host.skill_updated)
            self.assertEqual(host.actions, 0)

    def test_finished_attempt_lists_existing_public_evidence_for_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LearningHost(Path(directory), None, 'evidence-test', 0)
            host.harness = SimpleNamespace()
            host.finished = True
            evidence = host.rollout_root/'history.jsonl';evidence.write_text('{}\n')
            outside = Path(directory)/'agent';outside.mkdir()
            (outside/'rpc_result.json').write_text('{}')
            next_call = host.next_call()
            self.assertEqual(next_call['suggested_existing_evidence'], [str(evidence)])
            self.assertEqual(next_call['evidence_root'], str(host.rollout_root))

    def test_transfer_selection_is_required_and_preserved_before_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LearningHost(Path(directory), None, 'transfer-test', 0, require_selection=True)
            host.skill_sources = {'grasp_v14': {'path':'/public/grasp.md','scope':'prior self-experience'}}
            with patch('rsi.tool_host.LocoManipToolHost.dispatch') as physics:
                with self.assertRaisesRegex(ValueError, 'experience_select'):
                    host.dispatch('scalebfm_act', {'response':{'trajectory':[{}]}})
                physics.assert_not_called()
            request = {'selected_ids':['unknown'], 'rationale':'relevant',
                       'adaptation':'verify new scene', 'not_reused':'old coordinates'}
            with self.assertRaises(ValueError):host.dispatch('experience_select',request)
            request['selected_ids']=['grasp_v14']
            result=host.dispatch('experience_select',request)
            self.assertEqual(result['selected_sources']['grasp_v14']['path'],'/public/grasp.md')
            row=json.loads((host.rollout_root/'skill_selection.jsonl').read_text())
            self.assertEqual(row['adaptation'],'verify new scene')
            self.assertTrue(host.selection_recorded)

    def test_evidenced_stall_records_diagnostic_without_ending_or_physics(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LearningHost(Path(directory), None, 'stall-test', 0)
            with self.assertRaises(ValueError):
                host.dispatch('finish_attempt', {'reason':'not started',
                    'next_hypothesis':'test', 'evidence_paths':[]})
            host.actions = 3
            host.backend = SimpleNamespace(active=None)
            host.harness = SimpleNamespace(latest_path=host.rollout_root/'observation.json',
                evaluator=SimpleNamespace(outcome=lambda b:'in_progress'))
            evidence = host.rollout_root/'receipt.json'; evidence.write_text('{}')
            arguments = {'reason':'three distinct motions did not advance the task',
                'next_hypothesis':'adjust approach clearance and test again in this episode',
                'evidence_paths':[str(evidence)]}
            outside = Path(directory)/'unrelated.json'; outside.write_text('{}')
            with self.assertRaises(ValueError):
                host.dispatch('finish_attempt', dict(arguments,evidence_paths=[str(outside)]))
            with patch('rsi.tool_host.LocoManipToolHost.dispatch') as physics:
                result = host.dispatch('finish_attempt', arguments)
                physics.assert_not_called()
            self.assertFalse(result['rollout_finished'])
            self.assertFalse(host.finished)
            self.assertEqual(result['native_outcome'], 'in_progress')
            self.assertIsNone(result['stop_reason'])
            self.assertEqual(result['next_call']['tool'], 'scalebfm_act')
            self.assertTrue((host.rollout_root/'policy_stall.jsonl').is_file())
            self.assertFalse((host.rollout_root/'policy_stop.json').exists())

    def test_task_specific_physics_budget_is_reported_and_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LearningHost(Path(directory), None, 'door-test', 0,
                                max_episode_steps=12000)
            host.backend = SimpleNamespace(data=SimpleNamespace(time=245.),
                status=lambda: {'status':'idle'})
            host.harness = SimpleNamespace(latest_path=Path(directory)/'observation.json',
                evaluator=SimpleNamespace(outcome=lambda backend: 'in_progress'))
            output = host.rollout_root/'call_0000'; output.mkdir()
            with patch('rsi.tool_host.LocoManipToolHost.dispatch', return_value={}):
                returned = host.dispatch('scalebfm_act', {'output_dir':str(output),
                    'response':{'trajectory':[{}]}})
            self.assertEqual(returned['max_episode_steps'], 12000)
            self.assertTrue(returned['rollout_finished'])
            self.assertEqual(returned['stop_reason'], 'episode_step_budget')

    def test_task_prompt_and_clock_are_not_fixed_to_grasping(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LearningHost(Path(directory), None, 'door-test', 0,
                                task='Push the door open 30 degrees.', support_plane_z_m=None,
                                geometry_provider=None)
            self.assertIn('30 degrees', host.next_call()['task'])
            host.backend = SimpleNamespace(data=SimpleNamespace(time=17.5),
                status=lambda: {'status': 'idle', 'actual_error_m': None})
            host.harness = SimpleNamespace(latest_path=Path(directory)/'observation.json',
                evaluator=SimpleNamespace(outcome=lambda backend: 'in_progress'))
            output = host.rollout_root/'episode'; output.mkdir()
            packet = {'observation': {}, 'observation_path': str(host.harness.latest_path)}
            with patch('rsi.tool_host.LocoManipToolHost.dispatch', return_value=packet), \
                 patch('tools.learn_grasp_skill.finger_geometry', return_value={}):
                returned = host.dispatch('loco_start', {'output_dir': str(output)})
            self.assertEqual(returned['step_id'], 0)
            self.assertNotIn('workspace_calibration', returned)
            self.assertNotIn('finger_geometry', returned['observation'])

    def test_saved_receipt_matches_returned_episode_status(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LearningHost(Path(directory), None, 'episode-test', 0)
            host.backend = SimpleNamespace(data=SimpleNamespace(time=5.02),
                status=lambda: {'status': 'target_reached', 'actual_error_m': 0.})
            host.harness = SimpleNamespace(latest_path=Path(directory)/'observation.json',
                evaluator=SimpleNamespace(outcome=lambda backend: 'in_progress'))
            output = host.rollout_root/'call_0000'
            output.mkdir()
            packet = {'execution': [], 'observation_path': str(host.harness.latest_path)}
            (output/'tool_result.json').write_text(json.dumps(packet))
            with patch('rsi.tool_host.LocoManipToolHost.dispatch', return_value=packet):
                returned = host.dispatch('scalebfm_act', {
                    'output_dir': str(output), 'response': {'trajectory': [{}]}})
            saved = json.loads((output/'tool_result.json').read_text())
            self.assertEqual(saved, returned)
            self.assertEqual(saved['native_outcome'], 'in_progress')
            self.assertFalse(saved['rollout_finished'])
            self.assertEqual(saved['next_call']['tool'], 'scalebfm_act')


if __name__ == '__main__':
    unittest.main()
