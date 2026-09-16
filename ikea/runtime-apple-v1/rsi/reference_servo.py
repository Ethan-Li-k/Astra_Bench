"""Robot-only wrist reference correction, inspired by locomanip GraspRefServo.

This is an extra harness component, not part of the frozen neural tracker.
At 50 Hz the integral gain is 0.08 per tick; each correction is capped at 5 cm.
Requested goals remain separate from corrected tracker references.
"""
import numpy as np


class WristReferenceServo:
    def __init__(self):
        self.correction = np.zeros((2, 3))

    def correct(self, future_xyz, actual_xyz):
        future = np.asarray(future_xyz)
        actual = np.asarray(actual_xyz)
        if (future.ndim != 3 or future.shape[0] == 0 or future.shape[1:] != (2, 3)
                or actual.shape != (2, 3) or not np.isfinite(future).all()
                or not np.isfinite(actual).all()):
            raise ValueError('Expected finite wrist references (N,2,3) and actual positions (2,3)')
        self.correction += .08*(future[0]-actual)
        norm = np.linalg.norm(self.correction, axis=1, keepdims=True)
        self.correction *= np.minimum(1., .05/np.maximum(norm, 1e-12))
        return future + self.correction
