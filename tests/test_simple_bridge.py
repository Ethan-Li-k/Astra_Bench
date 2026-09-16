import unittest
from types import SimpleNamespace

import numpy as np

from rsi.simple_bridge import SimpleActionBridge
from rsi.simple_live import SimpleLiveSim


class FakeAction:
    def __init__(self, kind, **parameters):
        self.kind = kind
        self.parameters = parameters


class SimpleBridgeTests(unittest.TestCase):
    def test_native_step_preserves_named_order_and_additive_wrist_torque(self):
        sim = SimpleLiveSim.__new__(SimpleLiveSim)
        calls = []
        def native_step(action):
            calls.append(action)
            return {'hidden_object_pose': [1,2,3]}, .6, True, False, {'hidden_contact': True}
        sim.env = SimpleNamespace(step=native_step)
        sim.data = SimpleNamespace(time=0.)
        sim.kp = np.array([10., 20.])
        sim.wrist_pi_tau = np.array([1., 2.])
        sim.fingers = ('left_finger', 'right_finger')
        sim.closed = np.array([1., -1.])
        sim.gripper_command_at = lambda when: {'left': .2, 'right': .45}
        sim.bridge = SimpleActionBridge(('b', 'a'), ('a', 'b'), sim.fingers,
                                        action_factory=FakeAction)
        sim.physics_action_calls = 0
        sim._advance_physics(np.array([1., 2.]))
        self.assertEqual(len(calls), 1)
        command = calls[0].parameters
        np.testing.assert_allclose(command['target_q'], [2.1, 1.1])
        np.testing.assert_allclose(command['left_hand_q'], [.2])
        np.testing.assert_allclose(command['right_hand_q'], [-.45])
        self.assertEqual(sim.physics_action_calls, 1)
        self.assertTrue(sim._native_task_success)
        self.assertEqual(sim._native_task_reward, .6)
        self.assertFalse(hasattr(sim, 'native_observation'))

    def test_q29_and_dex3_are_mapped_by_name(self):
        policy = ('joint_b', 'joint_a')
        simple_body = ('joint_a', 'joint_b')
        fingers = ('left_finger_b', 'left_finger_a',
                   'right_finger_b', 'right_finger_a')
        bridge = SimpleActionBridge(policy, simple_body, fingers,
                                    action_factory=FakeAction)
        action = bridge.compile(
            [20., 10.],
            {'left_finger_a': 1., 'left_finger_b': 2.,
             'right_finger_a': 3., 'right_finger_b': 4.})
        self.assertEqual(action.kind, 'decoupled_wbc')
        np.testing.assert_array_equal(action.parameters['target_q'], [10., 20.])
        np.testing.assert_array_equal(action.parameters['left_hand_q'], [2., 1.])
        np.testing.assert_array_equal(action.parameters['right_hand_q'], [4., 3.])

    def test_missing_or_extra_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'body joint names'):
            SimpleActionBridge(('a', 'b'), ('a', 'c'), ('left_x', 'right_x'),
                               action_factory=FakeAction)
        bridge = SimpleActionBridge(('a',), ('a',), ('left_x', 'right_x'),
                                    action_factory=FakeAction)
        with self.assertRaisesRegex(ValueError, 'finger targets'):
            bridge.compile([0.], {'left_x': 0.})


if __name__ == '__main__':
    unittest.main()
