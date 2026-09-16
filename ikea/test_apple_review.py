"""Negative controls for apple evidence review; no task score or model calls."""
import unittest
from pathlib import Path
from review_apple_episode import physical_audit, review


def fixture():
    return [dict(sim_s=.02 * (n + 1), apple_center=[0., 0., .9], apple_bottom=.86,
                 lift_m=.1, bottom_rise_m=.1, base_z=.75, tilt_rad=.1, stable=True,
                 loaded_opposition=True, external_support=[],
                 contacts=[dict(other_body='left_hand_thumb_2_link', normal_force_n=.2),
                           dict(other_body='left_hand_index_1_link', normal_force_n=.2)])
            for n in range(80)]


class AppleReviewChecks(unittest.TestCase):
    def test_qualified_lift(self):
        self.assertTrue(physical_audit(fixture(), [0., 0., .8], .76, 0.)['passed'])

    def test_summary_flag_does_not_replace_recorded_force(self):
        evidence = fixture()
        evidence[-1]['contacts'] = []
        self.assertFalse(physical_audit(evidence, [0., 0., .8], .76, 0.)['passed'])

    def test_terminal_external_support_rejected(self):
        evidence = fixture()
        evidence[-1]['external_support'] = ['world']
        self.assertFalse(physical_audit(evidence, [0., 0., .8], .76, 0.)['passed'])

    def test_missing_tick_rejected(self):
        evidence = fixture()
        evidence.pop(20)
        self.assertFalse(physical_audit(evidence, [0., 0., .8], .76, 0.)['passed'])

    def test_unsealed_episode_refused(self):
        with self.assertRaisesRegex(ValueError, 'No sealed result'):
            review(Path(__file__).resolve().parent / 'campaign/apple-test-not-created')


if __name__ == '__main__':
    unittest.main()
