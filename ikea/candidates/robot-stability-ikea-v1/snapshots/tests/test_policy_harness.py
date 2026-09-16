import tempfile
import unittest
import json
from pathlib import Path

import numpy as np

from rsi.four_point import FOUR_POINT_NAMES
from rsi.policy_harness import (LocalFourPointHarness, direct_response_schema,
                                pixel_to_horizontal_plane, rotate_target,
                                tool_specs, translate_target,
                                validate_response, wrist_pose_for_local_point)


def observation():
    return {'observation_id': 'obs', 'four_point_world': {
        name: {'position_world_m': [float(i), 0., 0.],
               'quaternion_wxyz': [1., 0., 0., 0.]}
        for i, name in enumerate(FOUR_POINT_NAMES)}}


def response(target=None):
    target = target or observation()['four_point_world']
    return {'request_id': 'req', 'mode': 'four_point', 'reason': 'test',
            'trajectory': [{'target': target, 'duration_s': .5,
                            'active': {'position': list(FOUR_POINT_NAMES),
                                       'orientation': list(FOUR_POINT_NAMES)},
                            'grippers': {'left': 0., 'right': 0.}}]}


class FakeBackend:
    def __init__(self):
        self.count = 0
        self.state = 'idle'

    def observe(self):
        self.count += 1
        return observation() | {'observation_id': f'obs-{self.count}'}

    def move_four_points(self, observation_id, command_id, targets, duration=1.,
                         position_names=FOUR_POINT_NAMES,
                         orientation_names=FOUR_POINT_NAMES):
        self.state = 'executing'
        return {'command_id': command_id, 'status': 'executing', '_four_indices': [0, 1, 2, 3]}

    def set_grippers(self, left, right, duration=0.):
        return {'left': left, 'right': right}

    def tick(self):
        self.state = 'target_reached'

    def status(self):
        return {'status': self.state}


class FakeEvaluator:
    def __init__(self):
        self.ticks = 0

    def reset(self, backend):
        self.ticks = 0

    def update(self, backend):
        self.ticks += 1

    def outcome(self, backend):
        return 'success' if self.ticks else 'in_progress'


class HarnessTests(unittest.TestCase):
    def test_continuous_backend_receives_whole_chunk_once(self):
        class ContinuousBackend(FakeBackend):
            continuous_chunks_enabled=True
            def observe(self):
                return super().observe() | {'joint_position_rad':[.1]*29,
                    'commanded_joint_target_rad':[.2]*29,
                    'joint_names':[f'robot_joint_{i}' for i in range(29)],
                    'hidden_contact_truth':'must never reach motion trace'}
            def move_four_points(self,*args,**kwargs):
                raise AssertionError('Continuous chunk was split into separate commands')
            def move_four_point_sequence(self,observation_id,command_id,waypoints):
                self.received=waypoints;self.state='executing'
                return {'command_id':command_id,'status':'executing',
                        'duration_s':sum(w['duration_s'] for w in waypoints)}
        with tempfile.TemporaryDirectory() as root:
            backend=ContinuousBackend()
            harness=LocalFourPointHarness(backend,Path(root)/'episode')
            start=harness.start('interface test')
            action=response();action['trajectory']*=2
            result=harness.scalebfm_act(start['observation_path'],action)
            self.assertEqual(len(backend.received),2)
            self.assertEqual(len(result['execution']),1)
            self.assertEqual(result['execution'][0]['duration_s'],1.)
            summary=result['execution'][0]['robot_motion_summary']
            self.assertEqual(summary['samples'],2)
            samples=[json.loads(s) for s in Path(summary['trace_path']).read_text().splitlines()]
            self.assertEqual(set(samples[0]),{'sim_s','positions_world_m','quaternions_wxyz',
                                             'joint_position_rad','commanded_joint_target_rad'})
            self.assertEqual(len(summary['joint_names']),29)
            self.assertEqual(samples[0]['commanded_joint_target_rad'],[.2]*29)

    def test_dynamic_tool_sets_match_direct_and_hybrid_workflows(self):
        self.assertEqual([x['name'] for x in tool_specs('direct')],
                         ['loco_start', 'four_point_translate',
                          'four_point_rotate', 'image_pixel_to_world_plane',
                          'four_point_place_local_point',
                          'scalebfm_act'])
        self.assertEqual([x['name'] for x in tool_specs('pi05_plus_gpt')],
                         ['loco_start', 'four_point_translate',
                          'four_point_rotate', 'image_pixel_to_world_plane',
                          'four_point_place_local_point',
                          'pi05_infer', 'loco_execute'])
        execute = tool_specs('pi05_plus_gpt')[-1]['inputSchema']
        self.assertEqual(set(execute['required']),
                         {'proposal_path', 'response', 'output_dir'})
        schema = direct_response_schema()
        self.assertFalse(schema['additionalProperties'])
        target = schema['properties']['trajectory']['items']['properties']['target']
        self.assertEqual(tuple(target['required']), FOUR_POINT_NAMES)
        active = schema['properties']['trajectory']['items']['properties']['active']
        self.assertEqual(set(active['required']), {'position', 'orientation'})

    def test_response_is_strict_and_bounded(self):
        self.assertEqual(validate_response(response())['mode'], 'four_point')
        for bad in (response() | {'extra': 1},
                    response() | {'mode': 'joint'},
                    response() | {'trajectory': []},
                    response() | {'trajectory': response()['trajectory'] * 6}):
            with self.assertRaises(ValueError):
                validate_response(bad)
        gripper_only = response()
        gripper_only['trajectory'][0]['active'] = {'position': [], 'orientation': []}
        gripper_only['trajectory'][0]['grippers']['right'] = .6
        self.assertEqual(validate_response(gripper_only)['trajectory'][0]['active'],
                         {'position': (), 'orientation': ()})
        duplicate = response()
        duplicate['trajectory'][0]['active']['position'].append(FOUR_POINT_NAMES[0])
        with self.assertRaisesRegex(ValueError, 'unique'):
            validate_response(duplicate)

    def test_translation_and_rotation_compile_from_named_observation(self):
        moved = translate_target(observation(), [.01, 0., 0.], names=('right_wrist_yaw_link',))
        np.testing.assert_allclose(moved['right_wrist_yaw_link']['position_world_m'], [1.01, 0., 0.])
        turned = rotate_target(observation(), [0., 0., np.pi/2], [0., 0., 0.],
                               names=('right_wrist_yaw_link',))
        np.testing.assert_allclose(turned['right_wrist_yaw_link']['position_world_m'], [0., 1., 0.], atol=1e-7)

    def test_local_point_target_compiles_to_wrist_pose(self):
        half = np.sqrt(.5)
        wrist = wrist_pose_for_local_point(
            [1., 2., 3.], [half, 0., 0., half], [.08, 0., 0.])
        np.testing.assert_allclose(wrist['position_world_m'], [1., 1.92, 3.], atol=1e-8)
        np.testing.assert_allclose(wrist['quaternion_wxyz'], [half, 0., 0., half])

    def test_pixel_ray_intersects_declared_horizontal_plane(self):
        calibration = {
            'width_px': 100, 'height_px': 100, 'fovy_deg': 90.,
            'position_world_m': [0., 0., 1.],
            'rotation_camera_to_world_row_major': np.eye(3).reshape(-1).tolist(),
            'optical_convention': 'x_right_y_up_minus_z_forward'}
        np.testing.assert_allclose(
            pixel_to_horizontal_plane(calibration, [49.5, 49.5], 0.),
            [0., 0., 0.], atol=1e-12)
        np.testing.assert_allclose(
            pixel_to_horizontal_plane(calibration, [74.5, 49.5], 0.),
            [.5, 0., 0.], atol=1e-12)
        with self.assertRaisesRegex(ValueError, 'parallel'):
            turned = calibration | {
                'rotation_camera_to_world_row_major':
                    [1., 0., 0., 0., 0., -1., 0., 1., 0.]}
            pixel_to_horizontal_plane(turned, [49.5, 49.5], 0.)

    def test_direct_round_trip_is_recorded_and_stale_path_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            harness = LocalFourPointHarness(FakeBackend(), Path(root)/'episode')
            start = harness.start('grasp red cube')
            with self.assertRaises(ValueError):
                harness.scalebfm_act(Path(root)/'wrong.json', response())
            result = harness.scalebfm_act(start['observation_path'], response())
            self.assertEqual(result['execution'][0]['status'], 'executing')
            self.assertTrue((Path(root)/'episode'/'execution_0001.json').is_file())

    def test_pi05_without_checkpoint_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as root:
            harness = LocalFourPointHarness(FakeBackend(), Path(root)/'episode')
            start = harness.start('grasp red cube')
            with self.assertRaisesRegex(RuntimeError, 'No task-trained humanoid pi0.5'):
                harness.pi05_infer(start['observation_path'])

    def test_evaluator_returns_only_native_outcome_to_actor(self):
        with tempfile.TemporaryDirectory() as root:
            evaluator = FakeEvaluator()
            harness = LocalFourPointHarness(
                FakeBackend(), Path(root)/'episode', evaluator=evaluator)
            start = harness.start('grasp red cube')
            self.assertEqual(start['native_outcome'], 'in_progress')
            result = harness.scalebfm_act(start['observation_path'], response())
            self.assertEqual(result['native_outcome'], 'success')
            self.assertNotIn('evaluator', result)
            self.assertNotIn('object_pose', result['observation'])


if __name__ == '__main__':
    unittest.main()
