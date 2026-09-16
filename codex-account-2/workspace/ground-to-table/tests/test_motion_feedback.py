import json
import tempfile
import unittest
import numpy as np
import mujoco
from pathlib import Path
from ground_task import create_backend
from rsi.policy_harness import LocalFourPointHarness
from rsi.robot_kinematics import upper_body_world,upper_body_conventions,UPPER_BODY_LINKS

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
            allowed={'sim_s','four_point_world','pelvis_world','robot_com_model','robot_upper_body_world','joint_position_rad','gripper_commanded_closure','robot_control_feedback'}
            for sample in trace['samples']:self.assertEqual(set(sample),allowed)
            for sample in trace['samples']:
                self.assertEqual(set(sample['robot_upper_body_world']),set(UPPER_BODY_LINKS))
                for side in ('left','right'):
                    name=side+'_wrist_yaw_link'
                    for field in ('position_world_m','quaternion_wxyz'):
                        np.testing.assert_allclose(sample['robot_upper_body_world'][name][field],
                            sample['four_point_world'][name][field],atol=1e-12,rtol=0)
                feedback=sample['robot_control_feedback']
                self.assertAlmostEqual(feedback['interval_end_sim_s'],sample['sim_s'])
                self.assertEqual(len(feedback['joint_target_before_wrist_pi_rad']),29)
                self.assertEqual(len(feedback['wrist_pi_additive_torque_nm']),29)
                self.assertEqual(feedback['future_offsets_ticks'],[0,1,2,3,4,25])
                self.assertEqual(len(feedback['reference_positions_world_m']),6)
                self.assertEqual(len(feedback['reference_positions_world_m'][0]),4)
            for foot in trace['foot_geometry'].values():
                self.assertEqual(len(foot['collision_capsules_ankle']),7)
            for left,right in zip(trace['samples'],trace['samples'][1:]):
                self.assertAlmostEqual(right['sim_s']-left['sim_s'],.02)
            self.assertFalse(any('cube' in name for name in trace['joint_names']))

    def test_com_is_independent_of_cube_and_follows_robot_translation(self):
        backend=create_backend();m=backend.model
        observed=np.array(backend.observe()['robot_com_model']['position_world_m'])
        scratch=mujoco.MjData(m);scratch.qpos[:]=backend.data.qpos
        cube=int(m.joint('diagnostic_cube_free').qposadr[0])
        scratch.qpos[cube:cube+3]+=[10.,-3.,7.]
        mujoco.mj_forward(m,scratch)
        actual=np.average(scratch.xipos[backend.robot_com_bodies],axis=0,weights=backend.robot_com_masses)
        np.testing.assert_allclose(actual,observed,atol=1e-12)
        scratch.qpos[:2]+=[.3,-.2];mujoco.mj_forward(m,scratch)
        moved=np.average(scratch.xipos[backend.robot_com_bodies],axis=0,weights=backend.robot_com_masses)
        np.testing.assert_allclose(moved-observed,[.3,-.2,0.],atol=1e-12)
        self.assertNotIn(m.body('diagnostic_cube').id,backend.robot_com_bodies)

    def test_upper_body_fk_and_conventions_exclude_environment(self):
        backend=create_backend();m=backend.model
        baseline=upper_body_world(m,backend.data)
        scratch=mujoco.MjData(m);scratch.qpos[:]=backend.data.qpos
        cube=int(m.joint('diagnostic_cube_free').qposadr[0]);scratch.qpos[cube:cube+3]+=[10.,-3.,7.]
        mujoco.mj_forward(m,scratch)
        self.assertEqual(upper_body_world(m,scratch),baseline)
        scratch.qpos[:2]+=[.3,-.2];mujoco.mj_forward(m,scratch)
        moved=upper_body_world(m,scratch)
        for name in UPPER_BODY_LINKS:
            np.testing.assert_allclose(np.array(moved[name]['position_world_m'])-baseline[name]['position_world_m'],[.3,-.2,0.],atol=1e-12)
            np.testing.assert_allclose(moved[name]['quaternion_wxyz'],baseline[name]['quaternion_wxyz'],atol=1e-12)
        conventions=upper_body_conventions(m)
        self.assertFalse(any('diagnostic' in row['name'] or row['name']=='world' for row in conventions['bodies']))
        self.assertTrue(all(m.body(row['name']).id in backend.robot_com_bodies for row in conventions['bodies']))

if __name__=='__main__':unittest.main()
