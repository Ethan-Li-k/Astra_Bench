"""Geometry counterexamples and named interface checks; no policy inference."""
import unittest
from types import SimpleNamespace
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from locomanip.bfm.scaletrack import BODY_NAMES, ScaleTrackInferFn
from rsi.four_point import FOUR_POINT_NAMES
from rsi.scalebfm import Model38000, SCENE


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = mujoco.MjModel.from_xml_path(str(SCENE))

    def setUp(self):
        self.adapter = Model38000(self.model, load_policy=False)

    def task(self, adapter, axis, angle):
        rotation = Rotation.from_rotvec(np.eye(3)[axis] * np.deg2rad(angle))
        xyzw = rotation.as_quat()
        quat = xyzw[[3, 0, 1, 2]].astype(np.float32)
        pos = np.tile(np.array([.5, .1, .2], np.float32), (40, 14, 1))
        q = np.tile(np.array([1, 0, 0, 0], np.float32), (40, 14, 1))
        motion = SimpleNamespace(num_frames=40, body_pos_w=pos, body_quat_w=q)
        task = adapter._build_policy_task(np.zeros(3), quat, pos[0], q[0], motion, 0)
        return task, rotation.inv(), pos[0, 0]

    def test_legacy_pitch_counterexample_remains_reproducible(self):
        old = ScaleTrackInferFn(None, self.model, mode_name='VR-5')
        task, inv, point = self.task(old, 1, 10)
        self.assertGreater(np.linalg.norm(task[0, :3] - inv.apply(point)), .08)

    def test_full_anchor_against_independent_rotation_math(self):
        for axis in range(3):
            for angle in (-10, 0, 10):
                with self.subTest(axis=axis, angle=angle):
                    task, inv, point = self.task(self.adapter, axis, angle)
                    np.testing.assert_allclose(task[0, :3], inv.apply(point), atol=1e-6)
                    matrix = inv.as_matrix()
                    np.testing.assert_allclose(task[0, 84:90], np.r_[matrix[:, 0], matrix[:, 2]], atol=1e-6)

    def test_named_mapping_and_sparse_mask(self):
        a = self.adapter
        self.assertEqual(len(a._policy_qpos_adr), 29)
        for name, address in zip(a.metadata['joint_names'], a._policy_qpos_adr):
            self.assertEqual(address, self.model.joint(name).qposadr[0])
        active = {BODY_NAMES[i] for i in np.flatnonzero(a.mode[0])}
        self.assertEqual(active, set(FOUR_POINT_NAMES))
        self.assertEqual(a.mode_mapping[0, -1], 1)
        self.assertEqual(int(a.mode_mapping.sum()), 4 * 18 + 1)

    def test_bad_mode_and_time_rejected(self):
        for kw in ({'mode': 'VR-5'}, {'mode': 'UMI4'}, {'far_offset': -1}, {'far_offset': 33}, {'far_offset': 34}, {'far_offset': 5.5}):
            with self.assertRaises(ValueError):
                Model38000(self.model, load_policy=False, **kw)

    def test_scale_and_proprio_history(self):
        a = self.adapter
        np.testing.assert_allclose(a._action_scale_p, a.metadata['action_scale'])
        d = mujoco.MjData(self.model)
        d.qpos[a._policy_qpos_adr] = a._default_qpos_p
        mujoco.mj_forward(self.model, d)
        a.warm_start(d)
        np.testing.assert_allclose(a.policy_history[0, :, :3], [[0, 0, -1]] * 3)
        np.testing.assert_allclose(a.policy_history[0, :, 6:35], 0, atol=1e-7)
        np.testing.assert_allclose(a.action_history, 0, atol=1e-7)
        obs = a._build_policy_obs(np.array([1, 0, 0, 0]), np.zeros(3), a._default_qpos_p, np.ones(29))
        np.testing.assert_allclose(obs[-29:], .05)

    def test_histories_roll_across_actual_infer_calls(self):
        a = self.adapter
        d = mujoco.MjData(self.model)
        d.qpos[a._policy_qpos_adr] = a._default_qpos_p
        mujoco.mj_forward(self.model, d)
        a.warm_start(d)
        motion = SimpleNamespace(num_frames=40,
            body_pos_w=np.tile(d.xpos[a.body_ids], (40, 1, 1)),
            body_quat_w=np.tile(d.xquat[a.body_ids], (40, 1, 1)))
        # Mock only the neural output: exercise the real rolling implementation.
        for value in (.01, .02, .03, .04):
            d.qpos[a._policy_qpos_adr[0]] = a._default_qpos_p[0] + value
            mujoco.mj_forward(self.model, d)
            a._run_policy = lambda task, v=value: np.full(29, v, np.float32)
            a.infer(d, motion, 0)
        np.testing.assert_allclose(a.policy_history[0, :, 6], [.02, .03, .04], atol=1e-7)
        np.testing.assert_allclose(a.action_history[0, :, 0], [.02, .03, .04], atol=1e-7)

    def test_future_slots_sample_distinct_physical_times(self):
        a = self.adapter
        pos = np.zeros((50, 14, 3), np.float32)
        pos[:, :, 0] = np.arange(50)[:, None] * .001
        quat = np.tile([1., 0, 0, 0], (50, 14, 1)).astype(np.float32)
        motion = SimpleNamespace(num_frames=50, body_pos_w=pos, body_quat_w=quat)
        task = a._build_policy_task(np.zeros(3), np.array([1., 0, 0, 0]), pos[0], quat[0], motion, 3)
        np.testing.assert_allclose(task[:, 0], (3 + np.array(a.future_idx)) * .001, atol=1e-7)
        np.testing.assert_array_equal(task[:, -1], a.future_idx)


if __name__ == '__main__':
    unittest.main()
