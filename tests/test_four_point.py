import unittest

import numpy as np

from rsi.four_point import FOUR_POINT_NAMES, FourPointPose, interpolate_pose


def pose_mapping():
    return {
        name: {
            'position_world_m': [float(i), 0., 0.],
            'quaternion_wxyz': [1., 0., 0., 0.],
        }
        for i, name in enumerate(FOUR_POINT_NAMES)
    }


class FourPointContractTests(unittest.TestCase):
    def test_named_mapping_has_one_canonical_order(self):
        pose = FourPointPose.from_mapping(dict(reversed(list(pose_mapping().items()))))
        self.assertEqual(tuple(pose.to_mapping()), FOUR_POINT_NAMES)
        np.testing.assert_array_equal(pose.positions[:, 0], np.arange(4))

    def test_missing_extra_and_nonunit_quaternion_rejected(self):
        missing = pose_mapping()
        missing.pop(FOUR_POINT_NAMES[-1])
        extra = pose_mapping() | {'pelvis': pose_mapping()[FOUR_POINT_NAMES[0]]}
        bad_quat = pose_mapping()
        bad_quat[FOUR_POINT_NAMES[0]]['quaternion_wxyz'] = [2., 0., 0., 0.]
        for value in (missing, extra, bad_quat):
            with self.subTest(keys=tuple(value)):
                with self.assertRaises(ValueError):
                    FourPointPose.from_mapping(value)

    def test_translation_only_changes_selected_named_points(self):
        pose = FourPointPose.from_mapping(pose_mapping())
        moved = pose.translated([.01, -.02, .03], names=('right_wrist_yaw_link',))
        delta = moved.positions - pose.positions
        np.testing.assert_allclose(delta[1], [.01, -.02, .03])
        np.testing.assert_array_equal(delta[[0, 2, 3]], 0.)

    def test_world_rotation_updates_position_and_orientation(self):
        pose = FourPointPose.from_mapping(pose_mapping())
        pose.positions[0] = [1., 0., 0.]
        turned = pose.rotated([0., 0., np.pi/2], [0., 0., 0.], names=(FOUR_POINT_NAMES[0],))
        np.testing.assert_allclose(turned.positions[0], [0., 1., 0.], atol=1e-7)
        np.testing.assert_allclose(turned.quaternions[0], [np.sqrt(.5), 0., 0., np.sqrt(.5)], atol=1e-7)
        np.testing.assert_array_equal(turned.positions[1:], pose.positions[1:])

    def test_minimum_jerk_interpolation_keeps_unit_quaternions(self):
        start = FourPointPose.from_mapping(pose_mapping())
        goal = start.translated([.02, 0., 0.], names=FOUR_POINT_NAMES)
        goal = goal.rotated([0., .2, 0.], [0., 0., 0.], names=FOUR_POINT_NAMES)
        positions, quaternions = interpolate_pose(start, goal, np.array([0., .5, 1.]))
        np.testing.assert_allclose(positions[0], start.positions)
        np.testing.assert_allclose(positions[-1], goal.positions)
        np.testing.assert_allclose(quaternions[0], start.quaternions)
        np.testing.assert_allclose(quaternions[-1], goal.quaternions)
        np.testing.assert_allclose(np.linalg.norm(quaternions, axis=-1), 1.)


if __name__ == '__main__':
    unittest.main()
