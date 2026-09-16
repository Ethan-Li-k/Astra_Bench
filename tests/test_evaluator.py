import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from rsi.evaluator import LiftEvaluator, GraspLiftEvaluator, DoorPushEvaluator, SimpleNativeEvaluator


class FakeModel:
    def body(self, name):
        if name != 'diagnostic_cube':
            raise KeyError(name)
        return SimpleNamespace(id=2)


class FakeBackend:
    def __init__(self, z=.656):
        self.model = FakeModel()
        self.data = SimpleNamespace(xpos=np.array([[0., 0., 0.], [0., 0., 0.],
                                                   [.33, -.22, z]]))
        self.reason = None


class EvaluatorTests(unittest.TestCase):
    def test_native_evaluator_rejects_initial_success_and_checks_fall(self):
        backend = SimpleNamespace(_native_task_success=True, reason=None)
        evaluator = SimpleNativeEvaluator()
        with self.assertRaisesRegex(ValueError, 'already successful'):
            evaluator.reset(backend)
        backend._native_task_success = False
        evaluator.reset(backend); evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        backend._native_task_success = True
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'success')
        backend.reason = 'diagnostic_stability_stop'
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'failure')

    def door_fixture(self):
        model = SimpleNamespace(nbody=5, body_parentid=[0, 0, 1, 0, 0],
            jnt_bodyid=[1], joint=lambda name: SimpleNamespace(id=0, qposadr=[0]),
            body=lambda name: SimpleNamespace(id=3 if name.startswith('left') else 4))
        backend = SimpleNamespace(model=model, reason=None,
            data=SimpleNamespace(time=0., qpos=np.array([0.])))
        evaluator = DoorPushEvaluator()
        evaluator.reset(backend)
        evaluator._hand_contact = lambda b: True
        return backend, evaluator

    def test_door_dwell_uses_physics_time_not_number_of_reward_calls(self):
        backend, evaluator = self.door_fixture()
        backend.data.qpos[0] = .6
        for _ in range(100): evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        backend.data.time = .99; evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        backend.data.time = 1.; evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'success')

    def test_passive_door_motion_and_robot_fall_do_not_count(self):
        backend, evaluator = self.door_fixture()
        evaluator._hand_contact = lambda b: False
        backend.data.qpos[0] = .6
        for t in range(4):
            backend.data.time = t; evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        backend.reason = 'diagnostic_stability_stop'
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'failure')

    def test_door_reclosing_resets_hold(self):
        backend, evaluator = self.door_fixture()
        backend.data.qpos[0] = .6; evaluator.update(backend)
        backend.data.time = .9; backend.data.qpos[0] = .1; evaluator.update(backend)
        backend.data.time = 1.; backend.data.qpos[0] = .6; evaluator.update(backend)
        backend.data.time = 1.5; evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        backend.data.time = 2.; evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'success')

    def test_door_contact_requires_force_between_hand_and_door_subtrees(self):
        backend, evaluator = self.door_fixture()
        del evaluator._hand_contact
        backend.model.geom_bodyid = [2, 3, 0]
        backend.data.ncon = 1
        backend.data.contact = [SimpleNamespace(geom1=0, geom2=1)]
        def force(model, data, index, out): out[0] = .2
        with patch('mujoco.mj_contactForce', side_effect=force):
            self.assertTrue(evaluator._hand_contact(backend))
            backend.data.contact[0].geom2 = 2
            self.assertFalse(evaluator._hand_contact(backend))
        backend.data.contact[0].geom2 = 1
        with patch('mujoco.mj_contactForce'):
            self.assertFalse(evaluator._hand_contact(backend))

    def test_lift_without_grasp_contact_cannot_count(self):
        backend = FakeBackend()
        evaluator = GraspLiftEvaluator()
        evaluator._grasped = lambda b: False
        evaluator.reset(backend)
        backend.data.xpos[2, 2] += .08
        for _ in range(30): evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')

    def test_contact_lift_requires_sustained_hold(self):
        backend = FakeBackend()
        evaluator = GraspLiftEvaluator()
        evaluator._grasped = lambda b: True
        evaluator.reset(backend)
        backend.data.xpos[2, 2] += .08
        for _ in range(24): evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'success')

    def test_cube_must_stay_lifted_for_required_ticks(self):
        backend = FakeBackend()
        evaluator = LiftEvaluator(min_lift_m=.05, sustain_ticks=3)
        evaluator.reset(backend)
        backend.data.xpos[2, 2] += .051
        for _ in range(2):
            evaluator.update(backend)
            self.assertEqual(evaluator.outcome(backend), 'in_progress')
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'success')

    def test_drop_resets_dwell_and_stability_stop_fails(self):
        backend = FakeBackend()
        evaluator = LiftEvaluator(min_lift_m=.05, sustain_ticks=2)
        evaluator.reset(backend)
        backend.data.xpos[2, 2] += .06
        evaluator.update(backend)
        backend.data.xpos[2, 2] -= .06
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'in_progress')
        backend.reason = 'diagnostic_stability_stop'
        evaluator.update(backend)
        self.assertEqual(evaluator.outcome(backend), 'failure')


if __name__ == '__main__':
    unittest.main()
