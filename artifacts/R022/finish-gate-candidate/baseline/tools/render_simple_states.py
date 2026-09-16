"""Reuse SIMPLE Isaac synchronization to render recorded named states, no physics rollout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import traceback

os.environ.setdefault('OMNI_KIT_ACCEPT_EULA', 'Y')
os.environ.setdefault('MUJOCO_GL', 'egl')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import gymnasium as gym
import numpy as np
from PIL import Image, ImageDraw
import simple.envs  # noqa: F401
import simple.utils
import tyro
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from rsi.simple_recording import restore_named_render_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--env-id', default='simple/G1WholebodyCloseDoorTeleop-v0')
    parser.add_argument('--stride', type=int, default=2)
    parser.add_argument('--max-frames', type=int)
    parser.add_argument('--asset-table-material', action='store_true')
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    simple.utils.get_data_dir = lambda: args.data_root.resolve()
    def no_download(*a, **kw):
        raise FileNotFoundError('Reuse-only renderer: missing '+str(kw.get('allow_patterns')))
    simple.utils.snapshot_download = no_download
    manifest = json.loads((args.recording/'render_manifest.json').read_text())
    # Asset paths reference the source machine; preserve their data-relative suffix.
    def remap(value):
        if isinstance(value, str):
            prefix = '/home/galbot/lizekai/RSI/data/simple/runtime/'
            return str(args.data_root/value[len(prefix):]) if value.startswith(prefix) else value
        if isinstance(value, list): return [remap(v) for v in value]
        if isinstance(value, dict): return {k:remap(v) for k,v in value.items()}
        return value
    config = tyro.cli(SimLoopConfig, config=(tyro.conf.ConsolidateSubcommandArgs,), args=[]).load_wbc_yaml()
    config.update(ENV_NAME='simple', ENABLE_ELASTIC_BAND=False)
    env = encoder = None; result = {'physics_rollout':False, 'new_task_successes':0, 'frames':0,
                                  'table_material_overrides':[]}
    try:
        env = gym.make(args.env_id, sim_mode='mujoco_isaac', render_hz=25,
                       physics_dt=.005, headless=True, webrtc=False, sonic_config=config)
        if args.asset_table_material:
            setup_table = env.unwrapped.isaac._setup_table
            def setup_without_missing_mdl(prim_path, table):
                material = getattr(table, 'material', None)
                if material and 'vMaterials_2' in material.get('path',''):
                    result['table_material_overrides'].append(material)
                    table.material = None
                    try: return setup_table(prim_path, table)
                    finally: table.material = material
                return setup_table(prim_path, table)
            env.unwrapped.isaac._setup_table = setup_without_missing_mdl
        env.reset(options={'state_dict':remap(manifest['environment_config'])})
        runtime = env.unwrapped
        with (args.recording/'robot_trace.jsonl').open() as trace:
            for index, line in enumerate(trace):
                if index % args.stride: continue
                row = json.loads(line)
                restore_named_render_state(runtime.mjModel, runtime.mjData, row['host_render_state'])
                runtime.mjData.time = row['sim_s']
                runtime.isaac.step(runtime.mujoco)
                rgb = np.asarray(runtime.isaac.render()['head_stereo_left'])[:, :, :3]
                h,w = rgb.shape[:2]
                frame = Image.new('RGB',(w,h+48),(20,23,27));frame.paste(Image.fromarray(rgb),(0,48))
                draw = ImageDraw.Draw(frame)
                draw.text((8,5),'Isaac rerender of recorded MuJoCo states | no new physics trial',fill='white')
                draw.text((8,25),f"source sim {row['sim_s']:.2f}s",fill='white')
                if encoder is None:
                    frame.save(args.output/'first_frame.png')
                    encoder = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-n',
                        '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h+48}',
                        '-framerate',str(50/args.stride),'-i','pipe:0','-an','-c:v','libx264',
                        '-pix_fmt','yuv420p','-movflags','+faststart',str(args.output/'episode_isaac.mp4')],stdin=subprocess.PIPE)
                encoder.stdin.write(frame.tobytes());result['frames'] += 1
                if args.max_frames and result['frames'] >= args.max_frames: break
        result['status'] = 'rendered'
    except Exception as exc:
        result.update(status='error',error=f'{type(exc).__name__}: {exc}')
        traceback.print_exc()
        raise
    finally:
        if encoder:
            encoder.stdin.close(); result['encoder_exit_code'] = encoder.wait()
        (args.output/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result),flush=True)
        if env: env.close()


if __name__ == '__main__': main()
