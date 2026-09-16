"""RGB-only red-cube reach probe; no object state, contact, reward, or GPT."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')

import numpy as np
from PIL import Image

from rsi.live import LiveSim
from rsi.policy_harness import MujocoImageCapture
from rsi.tool_host import LocoManipToolHost


RIGHT_WRIST = 'right_wrist_yaw_link'


def red_centroid(image_path):
    rgb = np.asarray(Image.open(image_path).convert('RGB'))
    mask = ((rgb[:, :, 0] > 160)
            & (rgb[:, :, 0] > 1.6*rgb[:, :, 1])
            & (rgb[:, :, 0] > 1.6*rgb[:, :, 2]))
    y, x = np.nonzero(mask)
    if len(x) < 10:
        raise RuntimeError('visible red region not detected')
    return [float(x.mean()), float(y.mean())], {
        'bbox_xyxy': [int(x.min()), int(y.min()), int(x.max()), int(y.max())],
        'pixel_count': int(mask.sum())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plane-z', type=float, default=.630)
    parser.add_argument('--pregrasp-height', type=float, default=.10)
    parser.add_argument('--step-m', type=float, default=.025)
    parser.add_argument('--max-chunks', type=int, default=12)
    parser.add_argument('--step-strategy', choices=('vector', 'largest_axis'),
                        default='vector')
    parser.add_argument('--table-offset-x', type=float, default=0.)
    args = parser.parse_args()
    if (args.output.exists() or not np.isfinite([
            args.plane_z, args.pregrasp_height, args.step_m,
            args.table_offset_x]).all()
            or args.pregrasp_height <= 0 or not 0 < args.step_m <= .03
            or not 1 <= args.max_chunks <= 20):
        raise ValueError('invalid arguments or output already exists')

    def backend_factory():
        backend = LiveSim(wrist_pi=True, table_offset_x=args.table_offset_x)
        for _ in range(250):
            backend.tick()
        if backend.reason:
            raise RuntimeError(f'initial settling failed: {backend.reason}')
        return backend

    root = args.output.resolve()
    host = LocoManipToolHost(
        root, backend_factory, method='direct',
        image_capture_factory=MujocoImageCapture)
    trace = []
    stop = 'max_chunks'
    try:
        packet = host.dispatch('loco_start', {
            'task': 'Visually reach above the red cube without closing the hand.',
            'output_dir': str(root/'episode')})
        for index in range(args.max_chunks):
            observation = packet['observation']
            head = next(image for image in observation['images']
                        if image['camera'] == 'head_cam')
            pixel, region = red_centroid(head['path'])
            projected = host.dispatch('image_pixel_to_world_plane', {
                'observation_path': packet['observation_path'],
                'camera': 'head_cam', 'pixel_xy': pixel,
                'horizontal_plane_z_m': args.plane_z,
                'output_dir': str(root/f'call-{index:02d}-pixel')})
            point = projected['point_position_world_m'].copy()
            point[2] += args.pregrasp_height
            placed = host.dispatch('four_point_place_local_point', {
                'observation_path': packet['observation_path'],
                'link_name': RIGHT_WRIST,
                'point_position_world_m': point,
                'point_offset_link_m': [.08, 0., 0.],
                'output_dir': str(root/f'call-{index:02d}-place')})
            delta = np.asarray(placed['required_wrist_delta_world_m'])
            distance = float(np.linalg.norm(delta))
            row = {'chunk': index, 'observation_path': packet['observation_path'],
                   'red_pixel_xy': pixel, 'red_region': region,
                   'projected_plane_point_world_m': projected['point_position_world_m'],
                   'desired_right_palm_world_m': point,
                   'required_wrist_delta_world_m': delta.tolist(),
                   'required_wrist_distance_m': distance}
            if distance <= .01:
                row['status'] = 'visual_pregrasp_position_reached'
                trace.append(row)
                stop = row['status']
                break
            if args.step_strategy == 'vector':
                step = delta * min(1., args.step_m/distance)
            else:
                axis = int(np.argmax(np.abs(delta)))
                step = np.zeros(3)
                step[axis] = np.sign(delta[axis])*min(
                    args.step_m, abs(delta[axis]))
            translated = host.dispatch('four_point_translate', {
                'observation_path': packet['observation_path'],
                'names': [RIGHT_WRIST], 'delta_world_m': step.tolist(),
                'output_dir': str(root/f'call-{index:02d}-translate')})
            response = {
                'request_id': f'vision-reach-{index:02d}', 'mode': 'four_point',
                'reason': 'bounded RGB-grounded approach to a declared palm pregrasp point',
                'trajectory': [{
                    'target': translated['target'], 'active': translated['active'],
                    'duration_s': 1.5,
                    'grippers': {'left': 0., 'right': 0.}}]}
            packet = host.dispatch('scalebfm_act', {
                'observation_path': packet['observation_path'],
                'response': response,
                'output_dir': str(root/f'call-{index:02d}-act')})
            row['commanded_step_world_m'] = step.tolist()
            row['receipt'] = packet['execution'][-1]
            trace.append(row)
            if row['receipt']['status'] != 'target_reached':
                stop = f"tracker_{row['receipt']['status']}"
                break
        result = {
            'scope': 'head RGB, calibrated camera, declared horizontal work plane, named robot state; no object pose, depth, segmentation buffer, contact, reward, or GPT',
            'status': stop, 'chunks_attempted': len(trace), 'trace': trace,
            'step_strategy': args.step_strategy,
            'table_offset_x_m': args.table_offset_x,
            'right_palm_offset_link_m': [.08, 0., 0.],
            'right_palm_is_calibrated_grasp_tcp': False,
            'gripper_commands': 'open_only', 'gpt_or_api_calls': 0}
        (root/'result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({key: result[key] for key in (
            'status', 'chunks_attempted', 'right_palm_is_calibrated_grasp_tcp',
            'gpt_or_api_calls')}, indent=2))
    finally:
        host.close()


if __name__ == '__main__':
    main()
