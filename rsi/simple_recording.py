"""Host-only SIMPLE video and named joint states for existing Isaac sync."""
import json
import hashlib
from pathlib import Path

import mujoco
import numpy as np

from rsi.episode_video import EpisodeVideo


def external_robot_contacts(model, data):
    """Host audit only: robot versus non-floor objects, never actor input."""
    descendants = {model.body('pelvis').id}
    for body in range(model.nbody):
        if int(model.body_parentid[body]) in descendants:
            descendants.add(body)
    robot_geoms = set(np.flatnonzero(np.isin(model.geom_bodyid, list(descendants))))
    rows = []
    for index, contact in enumerate(data.contact):
        a, b = int(contact.geom1), int(contact.geom2)
        if (a in robot_geoms) == (b in robot_geoms):
            continue
        robot, other = (a, b) if a in robot_geoms else (b, a)
        if model.geom_type[other] == mujoco.mjtGeom.mjGEOM_PLANE:
            continue
        force = np.zeros(6)
        mujoco.mj_contactForce(model, data, index, force)
        rows.append({'robot_body': model.body(int(model.geom_bodyid[robot])).name,
                     'other_body': model.body(int(model.geom_bodyid[other])).name,
                     'other_geom': model.geom(other).name,
                     'distance_m': float(contact.dist),
                     'normal_force_n': float(force[0])})
    return rows


def named_render_state(backend):
    model, data = backend.model, backend.data
    ends = list(model.jnt_qposadr[1:])+[model.nq]
    return {'qpos_by_joint': {model.joint(i).name: data.qpos[start:end].tolist()
            for i, (start, end) in enumerate(zip(model.jnt_qposadr, ends))},
            'mocap_pos': data.mocap_pos.tolist(), 'mocap_quat': data.mocap_quat.tolist()}


def restore_named_render_state(model, data, state):
    # Joint-name matching includes free roots and door/faucet articulated joints.
    ends = list(model.jnt_qposadr[1:])+[model.nq]
    expected = {model.joint(i).name: (start, end)
                for i, (start, end) in enumerate(zip(model.jnt_qposadr, ends))}
    if set(expected) != set(state['qpos_by_joint']):
        raise ValueError('Render scene joints do not match recorded physics scene')
    for name, (start, end) in expected.items():
        values = state['qpos_by_joint'][name]
        if len(values) != end-start:
            raise ValueError(f'Render joint width mismatch: {name}')
        data.qpos[start:end] = values
    data.mocap_pos[:] = np.asarray(state['mocap_pos']).reshape(data.mocap_pos.shape)
    data.mocap_quat[:] = np.asarray(state['mocap_quat']).reshape(data.mocap_quat.shape)
    mujoco.mj_forward(model, data)


def simple_video(backend, output, *, door_audit=False,
                 label='Astra/xhigh Direct | SIMPLE | no demonstration'):
    from simple.utils import NumpyArrayEncoder
    camera_names = [backend.model.camera(i).name for i in range(backend.model.ncam)]
    head = [n for n in camera_names if 'head' in n.lower()]
    if not head:
        raise ValueError(f'No declared head camera in SIMPLE model: {camera_names}')
    camera = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(backend.model, camera)
    camera.lookat[:] = backend.data.xpos[backend.model.body('pelvis').id]
    camera.distance, camera.azimuth, camera.elevation = 3., 120., -20.
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if door_audit:
        from rsi.evaluator import DoorPushEvaluator
        audit = DoorPushEvaluator(); audit.reset(backend)
    def trace(b):
        result = named_render_state(b)
        result['native_task_success'] = b._native_task_success
        result['native_task_reward'] = b._native_task_reward
        result['external_robot_contacts_host_only'] = external_robot_contacts(b.model, b.data)
        if hasattr(b, 'placement_evaluator'):
            result['placement_completion_host_only'] = b.placement_evaluator.host_audit_state()
        raw_action = b.adapter.action_history[0, -1]
        raw_target = raw_action*b.adapter._action_scale_p+b.adapter._default_qpos_p
        result['control_chain'] = {
            'normalized_action29': raw_action.tolist(),
            'raw_joint_target29_rad': raw_target.tolist(),
            'commanded_joint_target29_rad': (raw_target+b.wrist_pi_tau/b.kp).tolist(),
            'wrist_pi_torque29_nm': b.wrist_pi_tau.tolist(),
            'last_substep_applied_torque29_nm': b.data.ctrl[b.act].tolist()}
        if door_audit:
            result['hand_door_contact'] = audit._hand_contact(b)
        return result
    root = Path(__file__).resolve().parents[1]
    sources = ('rsi/live.py','rsi/scalebfm.py','rsi/simple_live.py',
               'rsi/simple_environment.py','rsi/simple_recording.py','rsi/simple_object_names.py',
               'rsi/reference_sequence.py',
               'rsi/policy_harness.py','rsi/camera_calibration.py',
               'rsi/simple_hand_geometry.py','rsi/simulation_provenance.py',
               'rsi/evaluator.py','rsi/simple_door_setup.py','rsi/simple_door_collision.py',
               'rsi/simple_mp.py',
               'tools/learn_grasp_skill.py','tools/learn_door_skill.py',
               'tools/learn_simple_task.py','rsi/simple_placement.py')
    (output/'render_manifest.json').write_text(json.dumps({
        'actor_access': False, 'physics': 'MuJoCo', 'render': 'MuJoCo initial; Isaac rerender pending',
        'camera_names': camera_names, 'actor_cameras': head,
        'state_format': 'qpos_by_joint including articulated joints; no action replay',
        'environment_config': backend.env.task.state_dict(),
        'sonic_config': getattr(backend.env, 'sonic_config', None),
        'control_configuration': getattr(backend, 'control_configuration', None),
        'control_chain_joint_names': backend.adapter.metadata['joint_names'],
        'runtime_source_sha256': {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources},
        'initial_render_state': named_render_state(backend)}, indent=2, cls=NumpyArrayEncoder))
    if hasattr(backend, 'scene_setup'):
        (output/'scene_setup.json').write_text(json.dumps(backend.scene_setup, indent=2))
    return EpisodeVideo(backend, output, label=label,
                        cameras=head, video_cameras=(camera, head[0]), width=640, height=360,
                        extra_trace=trace)
