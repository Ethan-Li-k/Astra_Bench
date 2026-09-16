import unittest
import numpy as np
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose, interpolate_pose
from rsi.reference_sequence import ReferenceSequence, bounded_sequence
from copy import deepcopy


class ReferenceSequenceTests(unittest.TestCase):
    def chunk(self):
        start = FourPointPose(np.zeros((4,3)), np.tile([1.,0,0,0], (4,1)))
        up = start.copy(); up.positions[2] = [.06,0,.20]
        down = start.copy(); down.positions[2,0] = .12
        rows = [{'target':p, 'duration_s':.5,
                 'active':{'position':list(FOUR_POINT_NAMES), 'orientation':[]},
                 'grippers':{'left':0., 'right':0.}} for p in (up,down)]
        return start, rows

    def test_bounded_chunk_is_continuous_and_inactive_rotation_is_measured(self):
        start, rows = self.chunk()
        rows[0]['target'].quaternions *= -1
        sequence = bounded_sequence(2., start, rows, start.positions, 2.)
        self.assertEqual(sequence.times.tolist(), [2.,2.5,3.])
        self.assertGreater(sequence.sample(2.6)[0][2,0], .06)
        self.assertLess(sequence.sample(2.6)[0][2,2], .20)
        np.testing.assert_array_equal(sequence.poses[-1].quaternions,start.quaternions)

    def test_bad_late_waypoint_or_contract_rejected_without_mutating_inputs(self):
        start, rows = self.chunk()
        baseline = start.positions.copy()
        def invalid(kind):
            bad=deepcopy(rows)
            if kind=='late_translation': bad[-1]['target'].positions[0,0]=.07
            if kind=='total_excursion':
                bad[0]['target'].positions[2,0]=.2
                bad[1]['target'].positions[2,0]=.4
            if kind=='duration': bad[-1]['duration_s']=3.
            if kind=='active': bad[-1]['active']['position']=[]
            if kind=='grippers': bad[-1]['grippers']['right']=.3
            return bad
        for kind in ('late_translation','total_excursion','duration','active','grippers'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                bounded_sequence(0.,start,invalid(kind),start.positions,2.)
        np.testing.assert_array_equal(start.positions,baseline)

    def test_lookahead_crosses_knots_and_preserves_quaternion_sign(self):
        start = FourPointPose(np.zeros((4, 3)), np.tile([1., 0, 0, 0], (4, 1)))
        raised = start.copy(); raised.positions[2, 2] = .06
        landed = start.copy(); landed.positions[2, 0] = .03
        landed.quaternions *= -1
        sequence = ReferenceSequence([5., 5.5, 6.], [start, raised, landed])
        p, q = sequence.sample([4., 5., 5.5, 5.75, 6., 7.])
        np.testing.assert_allclose(p[0], start.positions)
        np.testing.assert_allclose(p[2], raised.positions)
        np.testing.assert_allclose(p[3, 2], [.015, 0., .03])
        np.testing.assert_allclose(p[4], landed.positions)
        np.testing.assert_allclose(p[5], landed.positions)
        np.testing.assert_allclose(np.linalg.norm(q, axis=-1), 1.)
        self.assertGreater(sequence.sample(5.6)[0][2, 0], 0.)

    def test_single_segment_matches_existing_interpolation_exactly(self):
        start = FourPointPose(np.zeros((4, 3)), np.tile([1., 0, 0, 0], (4, 1)))
        end = start.translated([.02, 0, .01])
        t = np.arange(34)*.02
        sequence = ReferenceSequence([0., 1.], [start, end])
        for actual, expected in zip(sequence.sample(t), interpolate_pose(start, end, t)):
            np.testing.assert_array_equal(actual, expected)

    def test_invalid_timing_rejected(self):
        for times in ([0, 0], [1, 0], [0, float('nan')]):
            with self.assertRaises(ValueError): ReferenceSequence(times, [None, None])


if __name__ == '__main__': unittest.main()
