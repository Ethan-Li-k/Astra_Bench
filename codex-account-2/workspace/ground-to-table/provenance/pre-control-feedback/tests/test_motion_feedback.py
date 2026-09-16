import json
import tempfile
import unittest
from pathlib import Path
from ground_task import create_backend
from rsi.policy_harness import LocalFourPointHarness

class MotionFeedbackTests(unittest.TestCase):
    def test_continuous_motion_exposes_time_resolved_robot_state_only(self):
        backend=create_backend(continuous=True)
        with tempfile.TemporaryDirectory() as tmp:
            host=LocalFourPointHarness(backend,Path(tmp)/'episode')
            first=host.start('Interface validation, no task success credit')
            pose=first['observation']['four_point_world']
            row={'target':pose,'active':{'position':[],'orientation':[]},
                 'duration_s':.5,'grippers':{'left':0.,'right':0.}}
            result=host.scalebfm_act(first['observation_path'],{'request_id':'trace-test',
                'mode':'four_point','trajectory':[row,row],'reason':'Sensor trace validation'})
            trace=json.loads(Path(result['motion_evidence']['proprioception_path']).read_text())
            self.assertGreaterEqual(len(trace['samples']),50)
            self.assertEqual(len(trace['joint_names']),29)
            self.assertEqual(trace['samples'][0]['sim_s'],first['observation']['sim_s'])
            self.assertEqual(trace['samples'][-1]['sim_s'],result['observation']['sim_s'])
            allowed={'sim_s','four_point_world','pelvis_world','joint_position_rad','gripper_commanded_closure'}
            for sample in trace['samples']:self.assertEqual(set(sample),allowed)
            for left,right in zip(trace['samples'],trace['samples'][1:]):
                self.assertAlmostEqual(right['sim_s']-left['sim_s'],.02)
            self.assertFalse(any('cube' in name for name in trace['joint_names']))

if __name__=='__main__':unittest.main()
