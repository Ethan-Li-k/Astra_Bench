"""Bounded, timed four-point reference interpolation."""
import math
import numpy as np
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose, interpolate_pose


CONTINUOUS_CONTRACT = {
    'enabled': True, 'waypoints': [2, 5], 'segment_duration_s': [.5, 3.],
    'total_duration_max_s': 3., 'future_frames_cross_segment_boundaries': True,
    'segment_translation_max_m': {'wrist': .06, 'ankle': .30},
    'chunk_translation_from_measured_max_m': {'wrist': .20, 'ankle': .30},
    'segment_rotation_max_rad': .10, 'chunk_rotation_max_rad': .30,
    'same_active_links_and_gripper_goals_for_all_waypoints': True,
    'start_and_inactive_components': 'current measured four-point pose',
    'intermediate_waypoints': 'timed references; no wait for arrival between them',
    'completion': 'final target arrival or total duration plus 2s timeout; reobserve after chunk',
    'feedback': 'Public 50Hz named robot pose, measured/commanded joint trace and peak ankle samples; no contact or object truth',
    'scope': 'Simulation UMI-4 interface; no supplied gait or task-success guarantee',
}


def bounded_sequence(start_time, measured, waypoints, workspace_origin, workspace_radius):
    """Validate the entire normalized chunk before any backend mutation."""
    if not 2 <= len(waypoints) <= 5:
        raise ValueError('Continuous chunk requires 2..5 waypoints')
    active, grippers = waypoints[0]['active'], waypoints[0]['grippers']
    pi = [FOUR_POINT_NAMES.index(n) for n in active['position']]
    ri = [FOUR_POINT_NAMES.index(n) for n in active['orientation']]
    times, poses, durations = [float(start_time)], [measured.copy()], []
    per_segment = np.array([.06, .06, .30, .30])
    per_chunk = np.array([.20, .20, .30, .30])
    for row in waypoints:
        if row['active'] != active or row['grippers'] != grippers:
            raise ValueError('Continuous chunk requires constant active links and gripper goals')
        duration = float(row['duration_s'])
        if not np.isfinite(duration) or not .5 <= duration <= 3.:
            raise ValueError('Continuous segment duration must be within [0.5,3.0]')
        durations.append(duration)
        elapsed = math.fsum(durations)
        if elapsed > 3.+1e-9:
            raise ValueError('Continuous chunk total duration exceeds 3 seconds')
        times.append(times[0]+min(elapsed,3.))
        goal = poses[-1].copy()
        goal.positions[pi] = row['target'].positions[pi]
        goal.quaternions[ri] = row['target'].quaternions[ri]
        for previous, limits, angle_limit in ((poses[-1], per_segment, .10),
                                               (measured, per_chunk, .30)):
            delta = np.linalg.norm(goal.positions-previous.positions, axis=1)
            angle = 2*np.arccos(np.clip(np.abs(np.sum(goal.quaternions*previous.quaternions,axis=1)),0.,1.))
            if np.any(delta[pi] > limits[pi]+1e-6) or np.any(angle[ri] > angle_limit+1e-6):
                raise ValueError('Continuous reference exceeds segment or measured-anchor limits')
        if np.any(np.linalg.norm(goal.positions[pi]-workspace_origin[pi],axis=1) > workspace_radius):
            raise ValueError('Continuous target outside bounded workspace')
        poses.append(goal)
    return ReferenceSequence(times, poses)


class ReferenceSequence:
    def __init__(self, times, poses):
        self.times = np.asarray(times, dtype=float)
        if (self.times.ndim != 1 or len(self.times) < 2
                or not np.isfinite(self.times).all() or np.any(np.diff(self.times) <= 0)
                or len(poses) != len(self.times)):
            raise ValueError('Strictly increasing finite knot times and matching poses required')
        self.poses = [p.copy() for p in poses]

    def sample(self, times):
        times = np.asarray(times, dtype=float)
        if not np.isfinite(times).all():
            raise ValueError('Sample times must be finite')
        flat = times.reshape(-1)
        positions = np.empty((len(flat), 4, 3))
        quaternions = np.empty((len(flat), 4, 4))
        indices = np.clip(np.searchsorted(self.times, flat, side='right')-1,
                          0, len(self.times)-2)
        for index in np.unique(indices):
            selected = indices == index
            phase = np.clip((flat[selected]-self.times[index]) /
                            (self.times[index+1]-self.times[index]), 0., 1.)
            positions[selected], quaternions[selected] = interpolate_pose(
                self.poses[index], self.poses[index+1], phase)
        return positions.reshape(times.shape+(4, 3)), quaternions.reshape(times.shape+(4, 4))

    def pose_at(self, time):
        return FourPointPose(*self.sample(float(time)))
