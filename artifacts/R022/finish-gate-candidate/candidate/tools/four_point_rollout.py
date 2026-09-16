"""Recorded local UMI-4 interface smoke; no GPT/API calls."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')

from rsi.four_point import FOUR_POINT_NAMES
from rsi.live import LiveSim
from rsi.policy_harness import LocalFourPointHarness, MujocoImageCapture, rotate_target, translate_target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--primitive', choices=('hold', 'right-x', 'right-yaw'), default='hold')
    args = parser.parse_args()
    sim = LiveSim()
    capture = MujocoImageCapture(sim)
    harness = LocalFourPointHarness(sim, args.output, image_capture=capture)
    try:
        started = harness.start(f'UMI-4 {args.primitive} interface smoke; grasp not evaluated')
        observation = started['observation']
        if args.primitive == 'hold':
            target = observation['four_point_world']
        elif args.primitive == 'right-x':
            target = translate_target(observation, [.01, 0., 0.], names=('right_wrist_yaw_link',))
        else:
            wrist = observation['four_point_world']['right_wrist_yaw_link']['position_world_m']
            target = rotate_target(observation, [0., 0., .05], wrist,
                                   names=('right_wrist_yaw_link',))
        response = {'request_id': f'{args.primitive}-0001', 'mode': 'four_point',
                    'reason': 'scripted primitive smoke; no model decision',
                    'trajectory': [{'target': target, 'duration_s': 1.,
                                    'active': {
                                        'position': (list(FOUR_POINT_NAMES) if args.primitive == 'hold'
                                                     else ['right_wrist_yaw_link']),
                                        'orientation': (['right_wrist_yaw_link']
                                                        if args.primitive == 'right-yaw' else [])},
                                    'grippers': {'left': 0., 'right': 0.}}]}
        result = harness.scalebfm_act(started['observation_path'], response)
        print(json.dumps({'execution': result['execution'],
                          'observation_path': result['observation_path'],
                          'images': result['observation']['images'],
                          'stop_reason': result['observation']['stop_reason']}, indent=2))
    finally:
        capture.close()


if __name__ == '__main__':
    main()
