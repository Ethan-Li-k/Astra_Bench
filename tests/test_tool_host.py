import tempfile
import unittest
from pathlib import Path

import numpy as np

from rsi.four_point import FOUR_POINT_NAMES
from rsi.policy_harness import tool_specs
from rsi.tool_host import LocoManipToolHost


def observation(index=0):
    return {'observation_id': f'obs-{index}', 'four_point_world': {
        name: {'position_world_m': [0., 0., 0.],
               'quaternion_wxyz': [1., 0., 0., 0.]}
        for name in FOUR_POINT_NAMES}, 'images': [{
            'camera': 'head_cam', 'path': '/tmp/fake-head.png',
            'calibration': {
                'width_px': 100, 'height_px': 100, 'fovy_deg': 90.,
                'position_world_m': [0., 0., 1.],
                'rotation_camera_to_world_row_major':
                    np.eye(3).reshape(-1).tolist(),
                'optical_convention': 'x_right_y_up_minus_z_forward'}}]}


def response():
    return {'request_id': 'req', 'mode': 'four_point', 'reason': 'test',
            'trajectory': [{'target': observation()['four_point_world'],
                            'active': {'position': [FOUR_POINT_NAMES[1]],
                                       'orientation': []},
                            'duration_s': .5,
                            'grippers': {'left': 0., 'right': 0.}}]}


def fake_image_capture(_backend):
    def capture(_directory):
        return [{'camera': 'head_cam', 'path': '/tmp/fake-head.png',
                 'calibration': {
                     'width_px': 100, 'height_px': 100, 'fovy_deg': 90.,
                     'position_world_m': [0., 0., 1.],
                     'rotation_camera_to_world_row_major':
                         np.eye(3).reshape(-1).tolist(),
                     'optical_convention': 'x_right_y_up_minus_z_forward'}}]
    return capture


class FakeBackend:
    def __init__(self):
        self.count = 0
        self.state = 'idle'
        self.last_targets = None

    def observe(self):
        self.count += 1
        return observation(self.count)

    def move_four_points(self, observation_id, command_id, targets, duration=1.,
                         position_names=FOUR_POINT_NAMES,
                         orientation_names=FOUR_POINT_NAMES):
        self.state = 'executing'
        self.last_targets = targets
        return {'command_id': command_id, 'status': self.state}

    def set_grippers(self, left, right, duration=0.):
        return {'left': left, 'right': right}

    def tick(self):
        self.state = 'target_reached'

    def status(self):
        return {'status': self.state}


class FakePi05:
    def audit(self):
        return {
            'status': 'ready',
            'policy_role': 'task_trained_humanoid_pi05',
            'task_skill_id': 'grasp_red_cube',
            'observation_contract': 'rgb_plus_named_robot_state',
            'action_contract': 'umi4_se3_plus_bimanual_gripper',
            'vision_inputs': ['head_rgb'],
            'checkpoint_sha256': 'a' * 64,
            'normalizer_sha256': 'b' * 64,
        }

    def infer(self, observation, task):
        proposal = response()
        proposal['request_id'] = 'student'
        proposal['trajectory'][0]['target'][FOUR_POINT_NAMES[1]][
            'position_world_m'] = [.02, 0., 0.]
        return proposal


class ToolHostTests(unittest.TestCase):
    def test_tool_sets_include_audited_geometry_compilers(self):
        direct = {spec['name'] for spec in tool_specs('direct')}
        hybrid = {spec['name'] for spec in tool_specs('pi05_plus_gpt')}
        geometry = {'four_point_translate', 'four_point_rotate',
                    'image_pixel_to_world_plane',
                    'four_point_place_local_point'}
        self.assertEqual(direct, {'loco_start', 'scalebfm_act'} | geometry)
        self.assertEqual(hybrid, {'loco_start', 'pi05_infer', 'loco_execute'} | geometry)

    def test_direct_dispatch_records_one_stateful_episode(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            host = LocoManipToolHost(root, FakeBackend, method='direct')
            started = host.dispatch('loco_start', {
                'task': 'grasp red cube', 'output_dir': str(root/'episode')})
            result = host.dispatch('scalebfm_act', {
                'observation_path': started['observation_path'],
                'response': response(), 'output_dir': str(root/'call-0001')})
            self.assertEqual(result['execution'][0]['status'], 'executing')
            self.assertTrue((root/'call-0001'/'tool_result.json').is_file())
            with self.assertRaises(ValueError):
                host.dispatch('pi05_infer', {
                    'observation_path': result['observation_path'],
                    'output_dir': str(root/'call-0002')})

    def test_hybrid_proposal_uses_same_validator_and_fresh_path(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            host = LocoManipToolHost(
                root, FakeBackend, method='pi05_plus_gpt', pi05=FakePi05())
            started = host.dispatch('loco_start', {
                'task': 'grasp red cube', 'output_dir': str(root/'episode')})
            proposed = host.dispatch('pi05_infer', {
                'observation_path': started['observation_path'],
                'output_dir': str(root/'call-0001')})
            reviewed = response()
            reviewed['request_id'] = 'reviewed'
            executed = host.dispatch('loco_execute', {
                'proposal_path': proposed['proposal_path'],
                'response': reviewed,
                'output_dir': str(root/'call-0002')})
            self.assertEqual(executed['execution'][0]['status'], 'executing')
            self.assertEqual(host.backend.last_targets[FOUR_POINT_NAMES[1]][
                'position_world_m'], [0., 0., 0.])
            with self.assertRaises(ValueError):
                host.dispatch('loco_execute', {
                    'proposal_path': proposed['proposal_path'],
                    'response': reviewed,
                    'output_dir': str(root/'call-replay')})
            with self.assertRaises(ValueError):
                host.dispatch('pi05_infer', {
                    'observation_path': executed['observation_path'],
                    'output_dir': str(root.parent/'escape')})

    def test_hybrid_rejects_unverified_or_nonvisual_pi05(self):
        class HoldSmokePi05:
            def audit(self):
                return {'head_loaded_from_ckpt': True, 'formal': True}

            def infer(self, observation, task):
                return response()

        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            host = LocoManipToolHost(
                root, FakeBackend, method='pi05_plus_gpt', pi05=HoldSmokePi05())
            with self.assertRaisesRegex(ValueError, 'capability'):
                host.dispatch('loco_start', {
                    'task': 'grasp red cube', 'output_dir': str(root/'episode')})

    def test_geometry_tools_compile_without_executing_backend(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            host = LocoManipToolHost(
                root, FakeBackend, method='direct',
                image_capture_factory=fake_image_capture)
            started = host.dispatch('loco_start', {
                'task': 'grasp red cube', 'output_dir': str(root/'episode')})
            count = host.backend.count
            translated = host.dispatch('four_point_translate', {
                'observation_path': started['observation_path'],
                'names': [FOUR_POINT_NAMES[1]],
                'delta_world_m': [.01, -.02, .03],
                'output_dir': str(root/'call-0001')})
            np.testing.assert_allclose(
                translated['target'][FOUR_POINT_NAMES[1]]['position_world_m'],
                [.01, -.02, .03])
            self.assertEqual(translated['active'], {
                'position': [FOUR_POINT_NAMES[1]], 'orientation': []})
            rotated = host.dispatch('four_point_rotate', {
                'observation_path': started['observation_path'],
                'names': [FOUR_POINT_NAMES[1]],
                'rotation_vector_world_rad': [0., 0., .1],
                'pivot_world_m': [0., 0., 0.],
                'output_dir': str(root/'call-0002')})
            self.assertEqual(rotated['active'], {
                'position': [FOUR_POINT_NAMES[1]],
                'orientation': [FOUR_POINT_NAMES[1]]})
            projected = host.dispatch('image_pixel_to_world_plane', {
                'observation_path': started['observation_path'],
                'camera': 'head_cam', 'pixel_xy': [49.5, 49.5],
                'horizontal_plane_z_m': 0.,
                'output_dir': str(root/'call-pixel')})
            np.testing.assert_allclose(projected['point_position_world_m'],
                                       [0., 0., 0.], atol=1e-12)
            placed = host.dispatch('four_point_place_local_point', {
                'observation_path': started['observation_path'],
                'link_name': FOUR_POINT_NAMES[1],
                'point_position_world_m': [1., 2., 3.],
                'point_offset_link_m': [.08, 0., 0.],
                'output_dir': str(root/'call-0003')})
            np.testing.assert_allclose(
                placed['target'][FOUR_POINT_NAMES[1]]['position_world_m'],
                [.92, 2., 3.])
            self.assertEqual(placed['active'], {
                'position': [FOUR_POINT_NAMES[1]], 'orientation': []})
            self.assertEqual(placed['point_offset_link_m'], [.08, 0., 0.])
            np.testing.assert_allclose(placed['required_wrist_delta_world_m'],
                                       [.92, 2., 3.])
            self.assertFalse(placed['within_single_step_limit'])
            self.assertEqual(host.backend.count, count)



if __name__ == '__main__':
    unittest.main()
