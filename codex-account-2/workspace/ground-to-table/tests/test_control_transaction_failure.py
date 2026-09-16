"""A control commit error must terminate cleanly, never create an empty retry loop."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from tools.learn_grasp_skill import LearningHost


class ControlFailureTests(unittest.TestCase):
    def test_pending_reference_error_is_terminal_and_does_not_count_an_action(self):
        with tempfile.TemporaryDirectory() as directory:
            host=LearningHost(Path(directory),None,'test',0)
            backend=SimpleNamespace(data=SimpleNamespace(time=5.),active=None)
            backend.cancel=lambda:setattr(backend,'active',None)
            def fail_after_commit(*args):
                backend.active='partially-committed'
                raise ValueError('deliberate gripper stage failure')
            host.backend=backend
            host.harness=SimpleNamespace(scalebfm_act=fail_after_commit,
                evaluator=SimpleNamespace(outcome=lambda b:'in_progress'))
            packet=host.dispatch('scalebfm_act',{'observation_path':'unused',
                'response':{'trajectory':[{}]},'output_dir':str(host.rollout_root/'failed_call')})
            self.assertFalse(packet['retryable'])
            self.assertTrue(packet['no_execution'])
            self.assertTrue(packet['rollout_finished'])
            self.assertTrue(host.finished)
            self.assertEqual(host.actions,0)
            self.assertIsNone(backend.active)
            self.assertEqual(packet['next_call']['tool'],'skill_update')
            self.assertEqual(backend.data.time,5.)

if __name__=='__main__':unittest.main()
