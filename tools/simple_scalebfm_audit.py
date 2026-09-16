"""Read-only SIMPLE/model_38000 compatibility audit; no physics action."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('MUJOCO_GL', 'egl')
os.environ.setdefault('OMNI_KIT_ACCEPT_EULA', 'Y')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import gymnasium as gym
import numpy as np
import simple.envs as _simple_envs  # noqa: F401
import tyro
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig

from rsi.four_point import FOUR_POINT_NAMES
from rsi.scalebfm import MODEL, MODEL_SHA256, Model38000
from rsi.simple_environment import make_simple_env


ENV_ID = 'simple/G1WholebodyCloseDoorTeleop-v0'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-root', type=Path)
    parser.add_argument('--env-id', default=ENV_ID)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    overlay = Path(__file__).resolve().parents[1]/'data/simple/runtime'
    if args.data_root is None and overlay.exists():
        args.data_root = overlay
    import simple.utils
    if args.data_root:
        simple.utils.get_data_dir = lambda: args.data_root.resolve()
    def reject_asset_download(*args, **kwargs):
        raise FileNotFoundError('SIMPLE offline reuse only; missing existing asset: '
                                +str(kwargs.get('allow_patterns', 'unknown')))
    # HF offline mode can still resolve cached downloads. Block this branch
    # completely because resolve_data_path also extracts and deletes archives.
    simple.utils.snapshot_download = reject_asset_download

    result = {
        'status': 'initializing',
        'scope': 'offline reset plus one model_38000 HOLD inference; no env.step',
        'env_id': args.env_id,
        'offline_only': True,
        'model_inference_calls': 0,
        'physics_action_calls': 0,
        'llm_calls': 0,
    }
    env = None
    try:
        env = make_simple_env(args.env_id, data_root=args.data_root)
        observation, info = env.reset(seed=0)
        runtime = env.unwrapped
        tracker = Model38000(runtime.mjModel)
        tracker.warm_start(runtime.mjData)

        positions = runtime.mjData.xpos[tracker.body_ids].copy()
        quaternions = runtime.mjData.xquat[tracker.body_ids].copy()
        motion = SimpleNamespace(
            num_frames=34,
            body_pos_w=np.tile(positions, (34, 1, 1)).astype(np.float32),
            body_quat_w=np.tile(quaternions, (34, 1, 1)).astype(np.float32),
        )
        target = tracker.infer(runtime.mjData, motion, 0)
        simple_order = list(runtime.task.robot.joint_names[:29])
        policy_order = list(tracker.metadata['joint_names'])
        cameras = {name: list(value.shape) for name, value in observation.items()
                   if isinstance(value, np.ndarray) and value.ndim == 3}
        result.update({
            'status': 'compatible' if simple_order == policy_order else 'joint_order_mismatch',
            'simple_body_joint_order': simple_order,
            'model_38000_joint_order': policy_order,
            'joint_order_exact': simple_order == policy_order,
            'four_point_bodies_present': {
                name: runtime.mjModel.body(name).id >= 0 for name in FOUR_POINT_NAMES
            },
            'camera_shapes': cameras,
            'info_is_privileged_and_actor_excluded': bool(info),
            'hold_target_finite': bool(np.isfinite(target).all()),
            'hold_target_shape': list(target.shape),
            'model_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
            'expected_model_sha256': MODEL_SHA256,
            'model_inference_calls': 1,
        })
    except Exception as error:
        result.update({
            'status': 'blocked_offline_initialization',
            'error_type': type(error).__name__,
            'error': str(error),
        })
    finally:
        if env is not None:
            env.close()
    (args.output/'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if result['status'] != 'compatible' or not result.get('hold_target_finite'):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
