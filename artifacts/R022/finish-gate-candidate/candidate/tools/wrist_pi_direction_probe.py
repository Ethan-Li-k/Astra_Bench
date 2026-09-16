"""Repeat the failed R012 right-wrist direction with the deployment WristPI."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from rsi.four_point import FourPointPose
from rsi.live import LiveSim


RIGHT = 'right_wrist_yaw_link'
DELTA = np.array([0.013043491, -0.006338092, 0.003833526])
ROTATIONS = {
    'right-yaw': np.array([0., 0., .08]),
    'right-world-y-negative': np.array([0., -.08, 0.]),
}


def run_trial(index, primitive, hold_orientation):
    sim = LiveSim(wrist_pi=True)
    for _ in range(250):
        sim.tick()
    observation = sim.observe()
    anchor = np.asarray(observation['four_point_world'][RIGHT]['position_world_m'])
    pose = FourPointPose.from_mapping(observation['four_point_world'])
    if primitive == 'failed-direction':
        target = pose.translated(DELTA, names=(RIGHT,))
        duration = 1.5
        active_rotation = (RIGHT,) if hold_orientation else ()
    else:
        target = pose.rotated(ROTATIONS[primitive], pose.positions[1], names=(RIGHT,))
        duration, active_rotation = 2., (RIGHT,)
    sim.move_four_points(
        observation['observation_id'], f'wrist-pi-direction-{index}',
        target.to_mapping(), duration=duration, position_names=(RIGHT,),
        orientation_names=active_rotation)
    errors, rotation_errors, torques = [], [], []
    for _ in range(180):
        sim.tick()
        status = sim.status()
        errors.append(status.get('actual_error_m', np.nan))
        rotation_errors.append(status.get('actual_rotation_error_rad', np.nan))
        torques.append(sim.wrist_pi_tau.copy())
        if status['status'] != 'executing':
            break
    final = sim.data.xpos[sim.adapter.body_ids[sim.four[1]]].copy()
    final_quat = sim.data.xquat[sim.adapter.body_ids[sim.four[1]]].copy()
    anchor_quat = np.asarray(observation['four_point_world'][RIGHT]['quaternion_wxyz'])
    final_rotation = Rotation.from_quat(final_quat[[1, 2, 3, 0]])
    anchor_rotation = Rotation.from_quat(anchor_quat[[1, 2, 3, 0]])
    status = sim.status()
    return ({'trial': index, 'status': status['status'], 'stop_reason': sim.reason,
             'ticks_after_command': len(errors),
             'final_active_error_m': status.get('actual_error_m'),
             'final_active_rotation_error_rad': status.get('actual_rotation_error_rad'),
             'final_delta_from_anchor_m': (final-anchor).tolist(),
             'final_rotation_from_anchor_world_rotvec_rad': (
                 final_rotation*anchor_rotation.inv()).as_rotvec().tolist(),
             'wrist_pi_integral_position_m': sim.wrist_pi.e_int[:, :3].tolist(),
             'wrist_pi_integral_rotation_rad': sim.wrist_pi.e_int[:, 3:].tolist(),
             'max_abs_wrist_pi_torque_nm': float(np.max(np.abs(torques)))},
            np.asarray(errors), np.asarray(rotation_errors), np.asarray(torques))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--primitive', choices=('failed-direction', *ROTATIONS),
                        default='failed-direction')
    parser.add_argument('--hold-orientation', action='store_true')
    args = parser.parse_args()
    if args.hold_orientation and args.primitive != 'failed-direction':
        parser.error('--hold-orientation applies only to failed-direction')
    args.output.mkdir(parents=True, exist_ok=False)
    summaries, arrays = [], {}
    for index in range(3):
        summary, errors, rotation_errors, torques = run_trial(
            index, args.primitive, args.hold_orientation)
        summaries.append(summary)
        arrays[f'error_m_{index}'] = errors
        arrays[f'rotation_error_rad_{index}'] = rotation_errors
        arrays[f'wrist_pi_tau29_nm_{index}'] = torques
    source = Path(__file__)
    wrist_pi = Path('/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/utils/wrist_pi.py')
    result = {
        'scope': ('three independent simulation resets; R012 failed position-only direction'
                  if args.primitive == 'failed-direction' else
                  f'three independent simulation resets; right-wrist {args.primitive} rotation'),
        'primitive': args.primitive,
        'hold_orientation': args.hold_orientation,
        'delta_world_m': (DELTA.tolist() if args.primitive == 'failed-direction' else None),
        'rotation_vector_world_rad': (ROTATIONS[args.primitive].tolist()
                                      if args.primitive in ROTATIONS else None),
        'duration_s': 1.5 if args.primitive == 'failed-direction' else 2.,
        'controller': 'deployment WristPI defaults; active-command integration only',
        'acceptance': '3/3 target_reached, position < 0.01 m, rotation < 0.05 rad, no stop',
        'accepted': all(row['status'] == 'target_reached'
                        and row['final_active_error_m'] < .01
                        and row['final_active_rotation_error_rad'] < .05
                        and row['stop_reason'] is None for row in summaries),
        'trials': summaries, 'llm_calls': 0,
        'policy_or_training_data': False,
        'sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (source, Path(__file__).parents[1]/'rsi/live.py', wrist_pi)}}
    np.savez(args.output/'trace.npz', **arrays)
    (args.output/'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
