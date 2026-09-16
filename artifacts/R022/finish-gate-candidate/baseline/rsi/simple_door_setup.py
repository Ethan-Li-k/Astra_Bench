"""Host-only setup of an explicitly labelled SIMPLE push-open variant."""
import mujoco
import numpy as np


def configure_push_side(runtime):
    model, data = runtime.mjModel, runtime.mjData
    joint = model.joint('articulate_joint_1')
    leaf = int(model.jnt_bodyid[joint.id]); address = int(joint.qposadr[0])
    base = model.body('articulate_base').id
    if model.body_parentid[base] != 0:
        raise ValueError('Door setup requires a world-attached articulated base')
    def opening_dot():
        q = float(data.qpos[address]); center = data.xipos[leaf].copy()
        data.qpos[address] = q+.001; mujoco.mj_forward(model, data)
        derivative = (data.xipos[leaf]-center)/.001
        data.qpos[address] = q; mujoco.mj_forward(model, data)
        away = center-data.body('pelvis').xpos
        return float(np.dot(derivative[:2], away[:2]))
    before = opening_dot(); center = data.xipos[leaf].copy()
    actor = runtime.task.layout.actors['articulated']
    original_pose = {'position': list(actor.pose.position),
                     'quaternion': list(actor.pose.quaternion)}
    if before <= 0:
        model.body_pos[base, :2] = 2*center[:2]-model.body_pos[base, :2]
        q = np.zeros(4)
        mujoco.mju_mulQuat(q, np.array([0., 0, 0, 1]), model.body_quat[base].copy())
        model.body_quat[base] = q
        position = np.array(actor.pose.position, dtype=float)
        position[:2] = 2*center[:2]-position[:2]
        mujoco.mju_mulQuat(q, np.array([0., 0, 0, 1]), np.asarray(actor.pose.quaternion))
        actor.pose.position, actor.pose.quaternion = position.tolist(), q.tolist()
        # mj_setConst resets its data argument; keep the actual reset state intact.
        mujoco.mj_setConst(model, mujoco.MjData(model))
        mujoco.mj_forward(model, data)
    after = opening_dot()
    if after <= 0:
        raise ValueError('Door opening still approaches the robot; push-side setup failed')
    return {'variant': 'SIMPLE asset 003 push-open; original task is close-door',
            'actor_access': False, 'opening_dot_before': before, 'opening_dot_after': after,
            'closed_leaf_center': center.tolist(), 'original_asset_pose': original_pose,
            'configured_asset_pose': {'position': list(actor.pose.position),
                                      'quaternion': list(actor.pose.quaternion)}}
