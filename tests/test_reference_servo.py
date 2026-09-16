import unittest
import numpy as np
from rsi.reference_servo import WristReferenceServo


class ReferenceServoTests(unittest.TestCase):
    def test_invalid_observation_does_not_poison_state(self):
        s = WristReferenceServo()
        future = np.zeros((6, 2, 3))
        for actual in (np.full((2, 3), np.nan), np.zeros((3,)), np.full((2, 3), np.inf)):
            with self.assertRaises(ValueError):
                s.correct(future, actual)
            np.testing.assert_array_equal(s.correction, 0.)

    def test_correction_is_bounded_without_mutating_goal_or_future(self):
        s = WristReferenceServo()
        future = np.zeros((6, 2, 3))
        future[:, :, 0] = np.arange(6)[:, None] * .001
        original = future.copy()
        actual = np.full((2, 3), -.2)
        for _ in range(100):
            corrected = s.correct(future, actual)
        np.testing.assert_array_equal(future, original)
        np.testing.assert_allclose(np.linalg.norm(s.correction, axis=1), .05)
        np.testing.assert_allclose(corrected-future, np.tile(s.correction, (6, 1, 1)))
        np.testing.assert_allclose(np.diff(corrected, axis=0), np.diff(future, axis=0))

    def test_fresh_session_has_no_previous_correction(self):
        s = WristReferenceServo()
        s.correct(np.ones((6, 2, 3)), np.zeros((2, 3)))
        fresh = WristReferenceServo()
        np.testing.assert_array_equal(fresh.correction, 0.)


if __name__ == '__main__':
    unittest.main()
