import time
import unittest
import numpy as np
import mujoco
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose
from rsi.live import LiveSim


class LiveInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = LiveSim()

    def setUp(self):
        self.sim.cancel()
        self.sim.commands.clear()
        self.sim.reason = None

    def test_physical_scene_and_robot_joint_mapping(self):
        m = self.sim.model
        self.assertEqual(m.joint('diagnostic_cube_free').type[0], mujoco.mjtJoint.mjJNT_FREE)
        self.assertGreater(m.npair, 0)
        self.assertEqual(len(self.sim.adapter._policy_qpos_adr), 29)
        self.assertNotIn(m.joint('diagnostic_cube_free').qposadr[0], self.sim.adapter._policy_qpos_adr)

    def test_physics_step_must_divide_tracker_period(self):
        s = LiveSim(physics_dt=.005)
        before = s.data.time
        s.tick()
        self.assertAlmostEqual(s.data.time-before, .02)
        with self.assertRaises(ValueError):
            LiveSim(physics_dt=.003)

    def test_external_scene_state_is_preserved_when_attaching_controller(self):
        original = LiveSim()
        original.data.qpos[0] += 1.2
        original.data.qpos[1] -= .4
        original.data.time = 3.
        before = original.data.qpos.copy()
        attached = LiveSim(model=original.model, data=original.data, workspace_radius_m=2.)
        self.assertIs(attached.model, original.model)
        self.assertIs(attached.data, original.data)
        np.testing.assert_array_equal(attached.data.qpos, before)
        self.assertEqual(attached.last_sim_time, 3.)
        self.assertEqual(attached.workspace_radius_m, 2.)

    def test_hand_force_compensation_is_explicit_and_runnable(self):
        self.assertIsNone(LiveSim().hand_comp)
        assisted = LiveSim(hand_force_comp=True)
        self.assertIsNotNone(assisted.hand_comp)
        assisted.tick()
        self.assertIsNone(assisted.reason)

    def test_wrist_pi_is_explicit_mutually_exclusive_and_finite(self):
        self.assertIsNone(LiveSim().wrist_pi)
        with self.assertRaises(ValueError):
            LiveSim(wrist_pi=True, hand_force_comp=True)
        with self.assertRaises(ValueError):
            LiveSim(wrist_pi=True, reference_servo=True)
        assisted = LiveSim(wrist_pi=True)
        obs = assisted.observe()
        target = FourPointPose.from_mapping(obs['four_point_world']).translated(
            [.02, 0., 0.], names=('right_wrist_yaw_link',))
        assisted.move_four_points(
            obs['observation_id'], 'wrist-pi', target.to_mapping(), duration=1.5,
            position_names=('right_wrist_yaw_link',), orientation_names=())
        for _ in range(50):
            assisted.tick()
        self.assertEqual(assisted.wrist_pi_tau.shape, (29,))
        self.assertTrue(np.isfinite(assisted.wrist_pi_tau).all())
        self.assertGreater(np.linalg.norm(assisted.wrist_pi_tau), 0.)
        names = assisted.adapter.metadata['joint_names']
        left_arm = [i for i, name in enumerate(names)
                    if name.startswith('left_')
                    and any(part in name for part in ('shoulder', 'elbow', 'wrist'))]
        np.testing.assert_allclose(assisted.wrist_pi_tau[left_arm], 0., atol=1e-12)
        np.testing.assert_allclose(assisted.wrist_pi.e_int[0], 0., atol=1e-12)
        np.testing.assert_allclose(assisted.wrist_pi.e_int[1, 3:], 0., atol=1e-12)

    def test_frozen_anchor_and_duplicate_request(self):
        s = self.sim
        obs = s.observe()
        first = s.move_wrist(obs['observation_id'], 'a', [.01, 0, 0])
        goal = s.goal.copy()
        again = s.move_wrist(obs['observation_id'], 'a', [.01, 0, 0])
        self.assertIs(first, again)
        np.testing.assert_array_equal(s.goal, goal)
        with self.assertRaises(ValueError):
            s.move_wrist(obs['observation_id'], 'a', [.02, 0, 0])
        with self.assertRaises(ValueError):
            s.move_wrist(obs['observation_id'], 'b', [.01, 0, 0])
        s.cancel()
        self.assertEqual(s.commands['a']['status'], 'cancelled')
        np.testing.assert_array_equal(s.reference_at(s.data.time+5), s.reference_at(s.data.time))

    def test_expiry_and_invalid_delta(self):
        s = self.sim
        obs = s.observe()
        obs['captured_monotonic_s'] = time.monotonic()-2
        with self.assertRaises(ValueError):
            s.move_wrist(obs['observation_id'], 'c', [.01, 0, 0])
        for delta in ([float('nan'), 0, 0], [.1, 0, 0], [0, 0]):
            with self.assertRaises(ValueError):
                s.move_wrist('missing', 'd', delta)

    def test_observation_has_no_object_state(self):
        obs = self.sim.observe()
        self.assertNotIn('qpos', obs)
        self.assertEqual(len(obs['joint_position_rad']), 29)
        self.assertTrue(all('diagnostic_cube' not in n for n in obs['joint_names']))
        self.assertNotIn('object_pose', obs)
        self.assertIn('localization_source', obs)
        self.assertEqual(tuple(obs['four_point_world']), FOUR_POINT_NAMES)
        for point in obs['four_point_world'].values():
            self.assertEqual(len(point['position_world_m']), 3)
            self.assertEqual(len(point['quaternion_wxyz']), 4)

    def test_named_four_point_target_and_receipt(self):
        s = self.sim
        obs = s.observe()
        target = {name: dict(value) for name, value in obs['four_point_world'].items()}
        target['right_wrist_yaw_link']['position_world_m'] = (
            np.asarray(target['right_wrist_yaw_link']['position_world_m']) + [.01, 0., 0.]
        ).tolist()
        receipt = s.move_four_points(obs['observation_id'], 'four', target, duration=1.)
        self.assertEqual(receipt['mode'], 'UMI-4')
        self.assertEqual(tuple(receipt['controlled_links']), FOUR_POINT_NAMES)
        self.assertEqual(receipt['status'], 'executing')
        np.testing.assert_allclose(s.goal, target['right_wrist_yaw_link']['position_world_m'])

    def test_foot_diagnostic_limit_does_not_relax_wrist_or_default(self):
        s = LiveSim()
        foot = 'left_ankle_roll_link'
        wrist = 'left_wrist_yaw_link'
        obs = s.observe()
        target = FourPointPose.from_mapping(obs['four_point_world']).translated(
            [0., 0., .06], names=(foot,))
        with self.assertRaises(ValueError):
            s.move_four_points(obs['observation_id'], 'foot-default', target.to_mapping(),
                               position_names=(foot,), orientation_names=())
        s.translation_limit_m_by_link[foot] = .08
        obs = s.observe()
        self.assertEqual(obs['translation_limit_m_by_link'][wrist], .03)
        s.move_four_points(obs['observation_id'], 'foot-diagnostic', target.to_mapping(),
                           position_names=(foot,), orientation_names=())
        s.cancel()
        obs = s.observe()
        target = FourPointPose.from_mapping(obs['four_point_world']).translated(
            [0., 0., .06], names=(wrist,))
        with self.assertRaises(ValueError):
            s.move_four_points(obs['observation_id'], 'wrist-rejected', target.to_mapping(),
                               position_names=(wrist,), orientation_names=())

    def test_gripper_only_command_ramps_and_reports_duration_not_grasp(self):
        s = LiveSim()
        obs = s.observe()
        receipt = s.move_four_points(
            obs['observation_id'], 'gripper-only', obs['four_point_world'],
            duration=1., position_names=(), orientation_names=())
        s.set_grippers(left=0., right=.6, duration=1.)
        self.assertEqual(receipt['command_kind'], 'gripper_only')
        self.assertEqual(s.observe()['gripper_commanded_closure']['right'], 0.)
        for _ in range(25):
            s.tick()
        halfway = s.observe()['gripper_commanded_closure']['right']
        self.assertGreater(halfway, 0.)
        self.assertLess(halfway, .6)
        for _ in range(35):
            s.tick()
        self.assertEqual(s.status()['status'], 'gripper_duration_elapsed')
        self.assertAlmostEqual(s.observe()['gripper_commanded_closure']['right'], .6)
        self.assertNotIn('grasped', s.status())

    def test_inactive_orientation_keeps_reference_and_is_not_a_success_gate(self):
        s = LiveSim()
        obs = s.observe()
        requested = FourPointPose.from_mapping(obs['four_point_world'])
        reference = FourPointPose.from_mapping(obs['four_point_reference_world'])
        requested.quaternions[1] = FourPointPose.from_mapping(
            obs['four_point_world']).rotated(
                [0., 0., .1], requested.positions[1],
                names=('right_wrist_yaw_link',)).quaternions[1]
        receipt = s.move_four_points(
            obs['observation_id'], 'position-only', requested.to_mapping(), duration=.5,
            position_names=('right_wrist_yaw_link',), orientation_names=())
        np.testing.assert_allclose(
            receipt['approved_target']['right_wrist_yaw_link']['quaternion_wxyz'],
            reference.quaternions[1])
        self.assertEqual(receipt['active_position_links'], ['right_wrist_yaw_link'])
        self.assertEqual(receipt['active_orientation_links'], [])

    def test_four_point_receipt_measures_rotation_before_success(self):
        s = LiveSim()
        obs = s.observe()
        pose = FourPointPose.from_mapping(obs['four_point_world'])
        pivot = pose.positions[1].copy()
        target = pose.rotated([0., 0., .1], pivot,
                              names=('right_wrist_yaw_link',))
        s.move_four_points(obs['observation_id'], 'rotate', target.to_mapping(), duration=.5)
        s.tick()
        receipt = s.status()
        self.assertIn('actual_rotation_error_rad_by_link', receipt)
        self.assertGreater(receipt['actual_rotation_error_rad_by_link']['right_wrist_yaw_link'], .05)
        self.assertEqual(receipt['status'], 'executing')

    def test_receipt_distinguishes_measured_and_reference_anchors(self):
        s = self.sim
        obs = s.observe()
        measured = np.asarray(obs['wrist_world_m'])
        s.start = s.goal = measured + [.0, -.02, .0]
        obs = s.observe()
        np.testing.assert_allclose(obs['wrist_tracking_error_world_m'], [0, .02, 0], atol=1e-8)
        receipt = s.move_wrist(obs['observation_id'], 'anchors', [.01, 0, 0])
        self.assertEqual(receipt['frame'], 'world')
        np.testing.assert_allclose(receipt['observation_anchor_world_m'], measured)
        np.testing.assert_allclose(receipt['reference_delta_world_m'], [.01, .02, 0], atol=1e-8)
        np.testing.assert_allclose(receipt['requested_delta_world_m'], [.01, 0, 0])

    def test_external_reset_stops_before_next_policy_call(self):
        from unittest.mock import patch
        s = LiveSim()
        s.tick()
        obs = s.observe()
        s.move_wrist(obs['observation_id'], 'before_reset', [.01, 0, 0])
        s.data.time = 0.
        with patch.object(s.adapter, 'infer', wraps=s.adapter.infer) as infer:
            s.tick()
            infer.assert_not_called()
        self.assertEqual(s.reason, 'external_sim_time_change')
        self.assertEqual(s.status()['status'], 'aborted')


if __name__ == '__main__':
    unittest.main()
