"""Named UMI-4 end-effector poses and small world-frame transforms."""
from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation


FOUR_POINT_NAMES = (
    'left_wrist_yaw_link',
    'right_wrist_yaw_link',
    'left_ankle_roll_link',
    'right_ankle_roll_link',
)


def _indices(names):
    names = tuple(names)
    if len(set(names)) != len(names) or not set(names) <= set(FOUR_POINT_NAMES):
        raise ValueError(f'Point names must be unique members of {FOUR_POINT_NAMES}')
    return [FOUR_POINT_NAMES.index(name) for name in names]


@dataclass
class FourPointPose:
    """One world-frame pose for each named UMI-4 link; quaternions are wxyz."""

    positions: np.ndarray
    quaternions: np.ndarray

    def __post_init__(self):
        self.positions = np.asarray(self.positions, dtype=float).copy()
        self.quaternions = np.asarray(self.quaternions, dtype=float).copy()
        if self.positions.shape != (4, 3) or self.quaternions.shape != (4, 4):
            raise ValueError('Four-point pose requires position (4,3) and quaternion (4,4)')
        if not np.isfinite(self.positions).all() or not np.isfinite(self.quaternions).all():
            raise ValueError('Four-point pose must be finite')
        norms = np.linalg.norm(self.quaternions, axis=1)
        if not np.allclose(norms, 1., atol=1e-4):
            raise ValueError('quaternion_wxyz must be unit length')
        self.quaternions /= norms[:, None]

    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict) or set(value) != set(FOUR_POINT_NAMES):
            raise ValueError(f'Pose must contain exactly these named points: {FOUR_POINT_NAMES}')
        try:
            positions = [value[name]['position_world_m'] for name in FOUR_POINT_NAMES]
            quaternions = [value[name]['quaternion_wxyz'] for name in FOUR_POINT_NAMES]
        except (KeyError, TypeError) as error:
            raise ValueError('Each point requires position_world_m and quaternion_wxyz') from error
        return cls(positions, quaternions)

    def copy(self):
        return FourPointPose(self.positions, self.quaternions)

    def to_mapping(self):
        return {
            name: {
                'position_world_m': self.positions[i].tolist(),
                'quaternion_wxyz': self.quaternions[i].tolist(),
            }
            for i, name in enumerate(FOUR_POINT_NAMES)
        }

    def translated(self, delta_world_m, *, names=FOUR_POINT_NAMES):
        delta = np.asarray(delta_world_m, dtype=float)
        if delta.shape != (3,) or not np.isfinite(delta).all():
            raise ValueError('Translation must be a finite world-frame xyz vector')
        result = self.copy()
        result.positions[_indices(names)] += delta
        return result

    def rotated(self, rotation_vector_world_rad, pivot_world_m, *, names=FOUR_POINT_NAMES):
        rotvec = np.asarray(rotation_vector_world_rad, dtype=float)
        pivot = np.asarray(pivot_world_m, dtype=float)
        if rotvec.shape != (3,) or pivot.shape != (3,) or not np.isfinite(np.r_[rotvec, pivot]).all():
            raise ValueError('Rotation vector and pivot must be finite xyz vectors')
        selected = _indices(names)
        delta = Rotation.from_rotvec(rotvec)
        result = self.copy()
        result.positions[selected] = delta.apply(result.positions[selected] - pivot) + pivot
        current_xyzw = result.quaternions[selected][:, [1, 2, 3, 0]]
        result_xyzw = (delta * Rotation.from_quat(current_xyzw)).as_quat()
        result.quaternions[selected] = result_xyzw[:, [3, 0, 1, 2]]
        return result


def interpolate_pose(start, goal, phase):
    """Minimum-jerk position plus shortest-path quaternion interpolation."""
    if not isinstance(start, FourPointPose) or not isinstance(goal, FourPointPose):
        raise ValueError('start and goal must be FourPointPose values')
    phase = np.asarray(phase, dtype=float)
    if not np.isfinite(phase).all() or np.any(phase < 0) or np.any(phase > 1):
        raise ValueError('Interpolation phase must be finite and within [0,1]')
    blend = 3 * phase**2 - 2 * phase**3
    positions = start.positions + blend[..., None, None] * (goal.positions - start.positions)

    q0 = start.quaternions
    q1 = goal.quaternions.copy()
    dot = np.sum(q0 * q1, axis=1)
    q1[dot < 0] *= -1
    dot = np.clip(np.abs(dot), -1., 1.)
    rows = []
    for alpha in blend.reshape(-1):
        theta = np.arccos(dot)
        sine = np.sin(theta)
        near = sine < 1e-7
        w0 = np.empty(4)
        w1 = np.empty(4)
        w0[near], w1[near] = 1 - alpha, alpha
        w0[~near] = np.sin((1-alpha) * theta[~near]) / sine[~near]
        w1[~near] = np.sin(alpha * theta[~near]) / sine[~near]
        q = w0[:, None] * q0 + w1[:, None] * q1
        rows.append(q / np.linalg.norm(q, axis=1, keepdims=True))
    quaternions = np.asarray(rows).reshape(phase.shape + (4, 4))
    return positions, quaternions
