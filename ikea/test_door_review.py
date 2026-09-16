"""Synthetic negative controls for the independent reviewer, not task scores."""
import copy
import unittest
from pathlib import Path
from review_door_episode import physical_audit, review


def fixture():
    return [dict(sim_s=.02 * (n + 1), door_open_rad=min(.6, .02 * n),
                 hand_contact=n < 40, base_z=.75, tilt_rad=.1,
                 stable=True, outcome='success') for n in range(100)]


class ReviewTests(unittest.TestCase):
    def test_qualified_terminal_hold(self):
        self.assertTrue(physical_audit(fixture(), 0.)['passed'])

    def test_sticky_native_success_cannot_hide_final_closure(self):
        evidence = fixture()
        evidence[-1]['door_open_rad'] = .2
        report = physical_audit(evidence, 0.)
        self.assertGreater(report['longest_qualified_hold_s'], 1.)
        self.assertFalse(report['passed'])

    def test_missing_tick_not_continuous(self):
        evidence = fixture()
        evidence.pop(50)
        self.assertFalse(physical_audit(evidence, 0.)['passed'])

    def test_contact_without_driving_motion_not_sufficient(self):
        evidence = fixture()
        for row in evidence:
            row['hand_contact'] = row['sim_s'] > 1.
        self.assertFalse(physical_audit(evidence, 0.)['passed'])

    def test_unstable_before_final_hold_rejected(self):
        evidence = fixture()
        evidence[0]['base_z'] = .4
        self.assertFalse(physical_audit(evidence, 0.)['passed'])

    def test_unsealed_incomplete_episode_refused(self):
        # The preserved first episode ended with a host logging error and has no sealed result.
        with self.assertRaisesRegex(ValueError, 'No sealed result'):
            review(Path(__file__).resolve().parent / 'campaign/door-0001')


if __name__ == '__main__':
    unittest.main()
