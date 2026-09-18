"""Exact native G1 MP assets with UMI-4 checkpoint PD, never the legacy policy.

This adapter is explicit: it changes control and the world-coordinate origin,
while preserving native robot/object geometry and native task criteria.
"""
import hashlib
import json
import random

import mujoco
import numpy as np

from rsi.live import LiveSim
from rsi.scalebfm import METADATA
from rsi.simulation_provenance import reset_provenance

MP_ENVS = frozenset(('simple/G1WholebodyBendPickMP-v0',
                     'simple/G1WholebodyTabletopGraspMP-v0'))


class _ForbiddenLegacyPolicy:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        raise RuntimeError('Legacy AMO policy is forbidden in the ScaleBFM adapter: '+name)


class SimpleMPLiveSim(LiveSim):
    def __init__(self, env, model, data):
        self.env = env.unwrapped
        self._native_task_success = False
        self._native_task_reward = 0.
        self.physics_action_calls = 0
        self.pd_profile = 'checkpoint'
        super().__init__(model=model, data=data, physics_dt=.002,
                         wrist_pi=True, workspace_radius_m=2.)
        self.control_configuration = {'adapter':'native-mp-checkpoint-force-v1',
            'joint_names':self.adapter.metadata['joint_names'],
            'kp':self.kp.tolist(),'kd':self.kd.tolist(),
            'physics_dt':.002,'tracker_dt':.02,'legacy_policy_used':False}

    def _advance_physics(self, target):
        # The tested force-PD path; retain name-based maps and native force caps.
        super()._advance_physics(target)
        engine = self.env.mujoco
        engine.render_step += 1
        if engine.render_step > 5:
            for key, body in engine.mj_objects.items():
                self.env.task.layout.actors[key].pose.position = list(body.xpos)
                self.env.task.layout.actors[key].pose.quaternion = list(body.xquat)
            actor = self.env.task.layout.actors['robot']
            actor.pose.position = list(np.round(self.data.qpos[:3], 3))
            actor.pose.quaternion = list(np.round(self.data.qpos[3:7], 3))
        info = self.env._get_info()
        # Original LocoManipulationEnv calls compute_reward then check_success;
        # check_success may itself compute reward. Do not alter that contract.
        self._native_task_reward = float(self.env.task.compute_reward(info, mujoco_env=engine))
        self._native_task_success = bool(self.env.task.check_success(info, mujoco_env=engine))
        self.env._success = self._native_task_success
        self.env.step_count += 1
        self.physics_action_calls += 1

    def close(self):
        self.env.close()


def create_native_mp_backend(env_id, seed=0, *, settle_ticks=250, saved_reset_options=None):
    if env_id not in MP_ENVS:
        raise ValueError('MP adapter is restricted to the exact two benchmark entries')
    from rsi.simple_environment import configure_offline_assets, load_hssd_metadata
    from rsi.simple_sensors import install_pelvis_gyro
    from rsi.simple_object_names import install_unique_object_labels
    configure_offline_assets()
    from simple.scenes.hssd import HssdSceneManager
    HssdSceneManager.load = load_hssd_metadata
    import gymnasium as gym
    import simple.envs  # noqa: F401
    import simple.robots.g1_wholebody as native_robot
    random.seed(seed); np.random.seed(seed)
    original_policy = native_robot.AMO_Policy
    env = None
    try:
        # Constructors/reset create this placeholder, not a loaded policy.
        native_robot.AMO_Policy = _ForbiddenLegacyPolicy
        env = gym.make(env_id, sim_mode='mujoco', headless=True,
                       render_hz=50, physics_dt=.002)
        install_pelvis_gyro(env); install_unique_object_labels(env)
        env.reset(seed=seed, options=saved_reset_options)
    except Exception:
        if env is not None: env.close()
        raise
    finally:
        native_robot.AMO_Policy = original_policy
    try:
        runtime = env.unwrapped
        engine = runtime.mujoco
        old_model, old_data = engine.mjModel, engine.mjData
        native_xml_hash = hashlib.sha256(engine.mjSpec.to_xml().encode()).hexdigest()
        native_state_hash = hashlib.sha256(b''.join(v.tobytes() for v in (
            old_data.qpos,old_data.qvel,old_data.ctrl,old_data.xfrc_applied,
            old_data.qfrc_applied))).hexdigest()
        translation = np.array([0., 0., -float(old_model.geom_pos[old_model.geom('ground').id, 2])])
        spec = mujoco.MjSpec(); spec.option = engine.mjSpec.option
        spec.attach(engine.mjSpec.copy(), frame=spec.worldbody.add_frame(pos=translation))
        model = spec.compile(); data = mujoco.MjData(model)
        assert [model.joint(i).name for i in range(model.njnt)] == [old_model.joint(i).name for i in range(old_model.njnt)]
        for name in ('qpos','qvel','ctrl','xfrc_applied','qfrc_applied','mocap_pos','mocap_quat'):
            getattr(data,name)[:] = getattr(old_data,name)
        data.mocap_pos[:] += translation
        for j in range(model.njnt):
            if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
                adr = int(model.jnt_qposadr[j]); data.qpos[adr:adr+3] += translation
        data.time = old_data.time
        mujoco.mj_forward(model,data); mujoco.mj_forward(old_model,old_data)
        checks = {'body_translation_max_error_m':float(np.max(abs(data.xpos[1:]-old_data.xpos[1:]-translation))),
            'camera_translation_max_error_m':float(np.max(abs(data.cam_xpos-old_data.cam_xpos-translation))),
            'body_rotation_max_error':float(np.max(abs(data.xmat-old_data.xmat))),
            'mass_max_difference':float(np.max(abs(model.body_mass-old_model.body_mass))),
            'inertia_max_difference':float(np.max(abs(model.body_inertia-old_model.body_inertia)))}
        if max(checks.values()) > 1e-10:
            raise ValueError('Rigid world-origin transformation changed native geometry')
        metadata = json.loads(METADATA.read_text())
        original_position_servos = []
        for name in metadata['joint_names']:
            actuator = model.actuator(name).id; joint = model.joint(name)
            if model.actuator_biasprm[actuator,1] != 0:
                original_position_servos.append(name)
            if model.actuator_gear[actuator,0] != 1:
                raise ValueError('Unreviewed native actuator gear')
            model.actuator_gainprm[actuator] = 0.; model.actuator_gainprm[actuator,0] = 1.
            model.actuator_biasprm[actuator] = 0.; model.actuator_biastype[actuator] = mujoco.mjtBias.mjBIAS_NONE
            model.actuator_ctrllimited[actuator] = 1
            model.actuator_ctrlrange[actuator] = model.jnt_actfrcrange[joint.id]
        if len(original_position_servos) != 14:
            raise ValueError('Unexpected native MP actuator contract')
        for name,value in zip(metadata['joint_names'], metadata['default_dof_pos']):
            joint=model.joint(name)
            if name not in original_position_servos: data.qpos[joint.qposadr[0]] = value
            data.qvel[joint.dofadr[0]] = 0.
        base=model.joint('pelvis')
        if int(base.qposadr[0]) != 0: raise ValueError('Unexpected MP free root layout')
        data.qpos[2] = .755; data.qvel[:6] = 0.; data.ctrl[:] = 0.
        mujoco.mj_forward(model,data)
        # Rebind all native views used by _get_info/reward. Old renderers never
        # receive new-model data; actor capture creates fresh calibrated renderers.
        objects={key:data.body(body.name) for key,body in engine.mj_objects.items()}
        for renderer in engine.renderers.values(): renderer.close()
        engine.renderers={}
        engine.mjModel,engine.mjData,engine.mjSpec=model,data,spec
        engine.mj_objects=objects
        robot=runtime.task.robot
        engine.joints=robot.joints={name:data.joint(name) for name in engine.joints}
        engine.actuators=robot.actuators={name:data.actuator(name) for name in engine.actuators}
        robot.mjdata=data; robot.mjmodel=model
        backend=SimpleMPLiveSim(env,model,data)
        backend.scene_setup={'variant':'Native MP geometry; rigid world-origin translation, checkpoint force PD and original arm initialization',
            'env_id':env_id,'seed':seed,'pd_profile':'checkpoint','mp_adapter':'native-mp-checkpoint-force-v1',
            'world_translation_m':translation.tolist(),'geometry_equivalence':checks,
            'native_xml_sha256':native_xml_hash,'native_reset_state_sha256':native_state_hash,
            'original_arm_pose_preserved':True,'object_state_and_forces_preserved':True,
            'object_velocity_preserved_note':'Only named robot/root velocities reset; earlier standalone diagnostics zeroed all velocities. This adapter preserves native object velocities and must be separately checked.',
            'native_reward_preserved':True,'legacy_policy_used':False,
            'object_identifier_changes':engine.rsi_object_identifier_changes}
        for _ in range(settle_ticks):
            backend.tick()
            if backend.reason: raise RuntimeError('MP standing initialization failed: '+backend.reason)
        backend.scene_setup['reset_provenance']=reset_provenance(backend,seed)
        return backend
    except Exception:
        env.close()
        raise
