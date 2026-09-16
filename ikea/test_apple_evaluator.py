"""Synthetic semantic tests only; these are not physical task attempts."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import time
import unittest
import numpy as np
from apple_backend import AppleEvaluator

ROOT = Path(__file__).resolve().parent / 'diagnostics/apple-evaluator-tests' / str(time.time_ns())


class AppleChecks(unittest.TestCase):
    def scenario(self, opposition=True, external=False, final_drop=False, base=.75):
        path = ROOT / self._testMethodName
        e = AppleEvaluator(path)
        b = SimpleNamespace(model=SimpleNamespace(body=lambda name: SimpleNamespace(id=0)),
                            data=SimpleNamespace(qpos=np.array([0., 0., base]), xmat=np.eye(3)[None], time=0.), reason=None)
        geometry = dict(center=np.array([0., 0., .8]), bottom=.76)
        contacts = dict(loaded_opposition=opposition, external_support=['world'] if external else [],
                        fingers={'left': ['thumb', 'index'] if opposition else [], 'right': []}, contacts=[])
        with patch('apple_backend.apple_geometry', return_value=geometry), patch('apple_backend.apple_contacts', return_value=contacts):
            e.reset(b)
            for n in range(65):
                b.data.time = .02 * (n + 1)
                geometry['center'] = np.array([0., 0., .9])
                geometry['bottom'] = .86
                if final_drop and n == 64:
                    geometry['center'][2] = .8
                    geometry['bottom'] = .76
                e.update(b)
            e.close()
        report = json.loads((path / 'summary.json').read_text())
        return report

    def test_retained_opposed_lift_passes(self):
        self.assertEqual(self.scenario()['outcome'], 'success')

    def test_airborne_without_opposition_rejected(self):
        self.assertEqual(self.scenario(opposition=False)['outcome'], 'in_progress')

    def test_external_support_rejected(self):
        self.assertEqual(self.scenario(external=True)['outcome'], 'in_progress')

    def test_terminal_drop_clears_transient_success(self):
        self.assertEqual(self.scenario(final_drop=True)['outcome'], 'in_progress')

    def test_robot_low_pose_not_success(self):
        self.assertEqual(self.scenario(base=.4)['outcome'], 'in_progress')


if __name__ == '__main__':
    unittest.main()
