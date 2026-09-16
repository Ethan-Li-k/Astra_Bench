import unittest
import numpy as np
from transfer_locomotion import rebase


def observation(position, quaternion=(1, 0, 0, 0)):
    return {'pelvis_world': {'quaternion_wxyz': list(quaternion)},
            'four_point_world': {'left_ankle_roll_link':
                {'position_world_m': position, 'quaternion_wxyz': list(quaternion)}}}


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.response = {'trajectory': [{'active': {'orientation': []}, 'target':
             {'left_ankle_roll_link': {'position_world_m': [1.2, 0, .14], 'quaternion_wxyz': [1, 0, 0, 0]}}}]}

    def test_name_based_translation_not_world_copy(self):
        r = rebase(self.response, observation([1, 0, 0]), observation([3, 2, 0]))
        np.testing.assert_allclose(r['trajectory'][0]['target']['left_ankle_roll_link']['position_world_m'], [3.2, 2, .14])
        self.assertEqual(self.response['trajectory'][0]['target']['left_ankle_roll_link']['position_world_m'], [1.2, 0, .14])

    def test_heading_transfers_relative_direction(self):
        q = [2**-.5, 0, 0, 2**-.5]
        r = rebase(self.response, observation([1, 0, 0]), observation([3, 2, 0], q))
        t = r['trajectory'][0]['target']['left_ankle_roll_link']
        np.testing.assert_allclose(t['position_world_m'], [3, 2.2, .14])
        self.assertEqual(t['quaternion_wxyz'], q)

    def test_active_orientation_rejected(self):
        self.response['trajectory'][0]['active']['orientation'] = ['left_ankle_roll_link']
        with self.assertRaises(ValueError):
            rebase(self.response, observation([1, 0, 0]), observation([0, 0, 0]))


if __name__ == '__main__':
    unittest.main()
