"""Privileged developer probe for grasp mechanics; never policy training data."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')
import numpy as np

from rsi.evaluator import LiftEvaluator
from rsi.four_point import FourPointPose
from rsi.live import LiveSim
from rsi.policy_harness import (LocalFourPointHarness, MujocoImageCapture,
                                wrist_pose_for_local_point)


RIGHT_WRIST = 'right_wrist_yaw_link'
# Midpoint of thumb and opposing fingers around the expected 5 cm object closure.
# This is an uncalibrated robot-local development proxy, not an actor input or TCP.
GRASP_PROXY_WRIST_M = np.array([.125, .05, 0.])
MAX_STEP_M = .015


def response(request_id, observation, desired_wrist_position, closure):
    pose = FourPointPose.from_mapping(observation['four_point_world'])
    current = pose.positions[1]
    delta = np.asarray(desired_wrist_position)-current
    distance = np.linalg.norm(delta)
    if distance > MAX_STEP_M:
        delta *= MAX_STEP_M/distance
    pose.positions[1] = current+delta
    return {'request_id': request_id, 'mode': 'four_point',
            'reason': 'privileged mechanics probe; excluded from policy data',
            'trajectory': [{'target': pose.to_mapping(), 'duration_s': 1.5,
                            'active': {'position': [RIGHT_WRIST], 'orientation': []},
                            'grippers': {'left': 0., 'right': float(closure)}}]}


def move_until(harness, packet, desired, phase, closure, max_chunks):
    records = []
    for index in range(max_chunks):
        current = np.asarray(packet['observation']['four_point_world'][RIGHT_WRIST]
                             ['position_world_m'])
        if np.linalg.norm(np.asarray(desired)-current) <= .008:
            break
        action = response(f'{phase}-{index:02d}', packet['observation'], desired, closure)
        packet = harness.scalebfm_act(packet['observation_path'], action)
        records.append({'phase': phase, 'chunk': index,
                        'command_status': packet['observation']['command_status']['status'],
                        'native_outcome': packet['native_outcome']})
        if packet['observation']['stop_reason'] or packet['native_outcome'] in ('success', 'failure'):
            break
        if packet['observation']['command_status']['status'] != 'target_reached':
            break
    return packet, records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    sim = LiveSim(wrist_pi=True)
    for _ in range(250):
        sim.tick()
    evaluator = LiftEvaluator(min_lift_m=.05, sustain_ticks=13)
    capture = MujocoImageCapture(sim)
    harness = LocalFourPointHarness(sim, args.output, image_capture=capture,
                                    evaluator=evaluator)
    records = []
    try:
        packet = harness.start('developer-only right-hand grasp mechanics probe')
        cube_body = sim.model.body('diagnostic_cube').id
        cube_initial = sim.data.xpos[cube_body].copy()
        wrist = packet['observation']['four_point_world'][RIGHT_WRIST]
        pre_point = cube_initial+np.array([-.09, 0., 0.])
        pre_wrist = wrist_pose_for_local_point(
            pre_point, wrist['quaternion_wxyz'], GRASP_PROXY_WRIST_M)['position_world_m']
        packet, rows = move_until(harness, packet, pre_wrist, 'pregrasp', 0., 8)
        records += rows

        if (records and not packet['observation']['stop_reason']
                and records[-1]['command_status'] == 'target_reached'):
            wrist = packet['observation']['four_point_world'][RIGHT_WRIST]
            grasp_wrist = wrist_pose_for_local_point(
                cube_initial, wrist['quaternion_wxyz'], GRASP_PROXY_WRIST_M)['position_world_m']
            packet, rows = move_until(harness, packet, grasp_wrist, 'approach', 0., 6)
            records += rows

        if (records and not packet['observation']['stop_reason']
                and records[-1]['command_status'] == 'target_reached'):
            current = packet['observation']['four_point_world'][RIGHT_WRIST]['position_world_m']
            action = response('close-00', packet['observation'], current, 1.)
            packet = harness.scalebfm_act(packet['observation_path'], action)
            records.append({'phase': 'close', 'chunk': 0,
                            'command_status': packet['observation']['command_status']['status'],
                            'native_outcome': packet['native_outcome']})

        if (records and not packet['observation']['stop_reason']
                and records[-1]['command_status'] == 'target_reached'):
            current = np.asarray(packet['observation']['four_point_world'][RIGHT_WRIST]
                                 ['position_world_m'])
            packet, rows = move_until(harness, packet, current+[0., 0., .08],
                                      'lift', 1., 5)
            records += rows

        cube_final = sim.data.xpos[cube_body].copy()
        sources = [Path(__file__), Path(__file__).parents[1]/'rsi/evaluator.py',
                   Path(__file__).parents[1]/'rsi/live.py',
                   Path(__file__).parents[1]/'rsi/policy_harness.py',
                   Path('/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/utils/wrist_pi.py')]
        result = {
            'scope': 'PRIVILEGED_DEVELOPMENT_ORACLE_NOT_POLICY_DATA',
            'actor_observation_contract': 'RGB plus named robot state; object truth omitted',
            'controller': 'model_38000 UMI-4 plus active-aware deployment WristPI defaults',
            'grasp_proxy_wrist_m': GRASP_PROXY_WRIST_M.tolist(),
            'native_outcome': packet['native_outcome'],
            'stop_reason': packet['observation']['stop_reason'],
            'records': records,
            'private_debug': {
                'cube_initial_world_m': cube_initial.tolist(),
                'cube_final_world_m': cube_final.tolist(),
                'cube_delta_world_m': (cube_final-cube_initial).tolist(),
            },
            'llm_calls': 0,
            'eligible_for_training': False,
            'sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sources},
        }
        (args.output/'oracle_debug.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        capture.close()


if __name__ == '__main__':
    main()
