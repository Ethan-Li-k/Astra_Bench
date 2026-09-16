"""Existing SIMPLE runtime, isolated offline configuration; no package writes."""
import json
import os
from pathlib import Path

import mujoco

from rsi.scalebfm import METADATA
from rsi.simple_live import SimpleLiveSim
from rsi.simple_sensors import install_pelvis_gyro
from rsi.simple_door_setup import configure_push_side
from rsi.simple_object_names import install_unique_object_labels
from rsi.simulation_provenance import reset_provenance

ROOT = Path(__file__).resolve().parents[1]
DOOR_ENV = 'simple/G1WholebodyCloseDoorTeleop-v0'


def load_hssd_metadata(manager, scene_uid):
    # Native MuJoCo constructs its geometry from this exact HssdSuite config.
    # USD existence checks and /tmp texture copies belong to Isaac rendering.
    from simple.scenes.hssd import HssdSuite
    configurations = {s['uid']:s for s in manager.hssd_scenes}
    return HssdSuite(configurations[scene_uid.split(':')[-1]])


def configure_offline_assets(data_root=None):
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import simple.utils
    simple.utils.get_data_dir = lambda: Path(data_root or ROOT/'data/simple/runtime').resolve()
    def no_download(*args, **kwargs):
        raise FileNotFoundError('Existing SIMPLE asset missing; downloads disabled: '
                                +str(kwargs.get('allow_patterns', 'unknown')))
    simple.utils.snapshot_download = no_download


def make_simple_env(env_id, *, data_root=None, sim_mode='mujoco', door_frame_override=False):
    configure_offline_assets(data_root)
    if sim_mode == 'mujoco':
        from simple.scenes.hssd import HssdSceneManager
        HssdSceneManager.load = load_hssd_metadata
    import gymnasium as gym
    import simple.envs  # noqa: F401
    import tyro
    from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
    config = tyro.cli(SimLoopConfig, config=(tyro.conf.ConsolidateSubcommandArgs,), args=[]).load_wbc_yaml()
    config.update(ENV_NAME='simple', ENABLE_ELASTIC_BAND=False)
    env = gym.make(env_id, sim_mode=sim_mode, headless=True,
                   render_hz=50, physics_dt=.005, sonic_config=config)
    install_pelvis_gyro(env)
    install_unique_object_labels(env)
    if door_frame_override:
        if env_id != DOOR_ENV or sim_mode != 'mujoco':
            raise ValueError('Frame override is scoped to the MuJoCo door variant')
        from rsi.simple_door_collision import install_frame_override
        install_frame_override(env)
    return env


def create_closed_door_backend(seed=0, *, settle_ticks=250, push_open=False, pd_profile='native',
                               door_frame_override=False):
    import random
    import numpy as np
    random.seed(seed); np.random.seed(seed)
    env = make_simple_env(DOOR_ENV, door_frame_override=door_frame_override)
    try:
        env.reset(seed=seed)
        runtime = env.unwrapped
        model, data = runtime.mjModel, runtime.mjData
        metadata = json.loads(METADATA.read_text())
        # Training standing posture, mapped by name; not a task demonstration.
        for name, value in zip(metadata['joint_names'], metadata['default_dof_pos']):
            data.qpos[model.joint(name).qposadr[0]] = value
        base = model.joint('floating_base_joint')
        data.qpos[int(base.qposadr[0])+2] = .755
        door = model.joint('articulate_joint_1')
        data.qpos[door.qposadr[0]] = float(model.jnt_range[door.id, 0])
        data.qvel[:] = data.ctrl[:] = 0
        data.qfrc_applied[:] = data.xfrc_applied[:] = 0
        mujoco.mj_forward(model, data)
        setup = configure_push_side(runtime) if push_open else {'variant': 'native close-door layout; closed diagnostic reset'}
        backend = SimpleLiveSim(env, pd_profile=pd_profile)
        setup['pd_profile'] = pd_profile
        if door_frame_override:
            setup['frame_collision_override'] = runtime.mujoco.rsi_frame_collision_override
        backend.scene_setup = setup
        for _ in range(settle_ticks):
            backend.tick()
            if backend.reason:
                raise RuntimeError('SIMPLE initial standing failed: '+backend.reason)
        backend.scene_setup['reset_provenance'] = reset_provenance(backend, seed)
        return backend
    except Exception:
        env.close()
        raise


def create_native_task_backend(env_id, seed=0, *, settle_ticks=250):
    """Preserve the native task's layout, object state and applied forces."""
    import random
    import numpy as np
    random.seed(seed); np.random.seed(seed)
    env = make_simple_env(env_id)
    try:
        env.reset(seed=seed)
        runtime = env.unwrapped
        model, data = runtime.mjModel, runtime.mjData
        metadata = json.loads(METADATA.read_text())
        for name, value in zip(metadata['joint_names'], metadata['default_dof_pos']):
            joint = model.joint(name)
            data.qpos[joint.qposadr[0]] = value
            data.qvel[joint.dofadr[0]] = 0.
        base = model.joint('floating_base_joint')
        data.qpos[int(base.qposadr[0])+2] = .755
        data.qvel[int(base.dofadr[0]):int(base.dofadr[0])+6] = 0.
        mujoco.mj_forward(model, data)
        backend = SimpleLiveSim(env, pd_profile='checkpoint')
        backend.scene_setup = {'variant':'native task layout with checkpoint standing reset',
            'env_id':env_id, 'seed':seed, 'pd_profile':'checkpoint',
            'object_state_and_forces_preserved':True,
            'object_identifier_changes':runtime.mujoco.rsi_object_identifier_changes}
        for _ in range(settle_ticks):
            backend.tick()
            if backend.reason:
                raise RuntimeError('SIMPLE initial standing failed: '+backend.reason)
        backend.scene_setup['reset_provenance'] = reset_provenance(backend, seed)
        return backend
    except Exception:
        env.close()
        raise
