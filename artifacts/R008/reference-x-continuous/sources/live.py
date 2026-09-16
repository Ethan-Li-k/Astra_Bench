"""Simulation-only single-writer runtime. Actor packets omit object state.

The motion interface is wrist/world coordinates until TCP calibration exists.
Runtime robot localization is currently simulator state, explicitly diagnostic.
"""
import time
from types import SimpleNamespace

import mujoco
import numpy as np
from locomanip.utils.dex3 import DEX3_CLOSED_POS
from rsi.scalebfm import Model38000, SCENE
from rsi.reference_servo import WristReferenceServo


def tabletop_model(offset_x=0.):
    # All object geometry belongs to environment construction, not actor input.
    robot = mujoco.MjModel.from_xml_path(str(SCENE))
    collision_names = [robot.geom(i).name for i in range(robot.ngeom)
                       if robot.geom(i).name and 'collision' in robot.geom(i).name]
    pairs = ''.join(f'<pair geom1="{name}" geom2="{other}"/>'
                    for name in collision_names
                    for other in ('diagnostic_table', 'diagnostic_cube_geom'))
    legs = ''.join(f'<geom name="table_leg_{i}" type="box" pos="{x+offset_x} {y} 0.285" '
                   'size="0.02 0.02 0.285" rgba="0.35 0.24 0.15 1" contype="1" conaffinity="5"/>'
                   for i, (x, y) in enumerate(((.28, -.37), (.52, -.37), (.28, -.07), (.52, -.07))))
    xml = f'''<mujoco><include file="{SCENE}"/>
    <compiler meshdir="{SCENE.parent / 'assets'}"/>
    <worldbody>
      {legs}
      <geom name="diagnostic_table" type="box" pos="{.40+offset_x} -0.22 0.60"
            size="0.15 0.18 0.03" rgba="0.45 0.30 0.18 1" contype="1" conaffinity="5"/>
      <body name="diagnostic_cube" pos="{.33+offset_x} -0.22 0.656">
        <freejoint name="diagnostic_cube_free"/>
        <geom name="diagnostic_cube_geom" type="box" size="0.025 0.025 0.025"
              mass="0.06" rgba="0.85 0.12 0.06 1" contype="1" conaffinity="5"
              friction="0.7 0.005 0.0001"/>
      </body>
    </worldbody><contact>{pairs}</contact></mujoco>'''
    return mujoco.MjModel.from_xml_string(xml)


class LiveSim:
    def __init__(self, *, reference_servo=False, table_offset_x=0.):
        self.model = tabletop_model(table_offset_x)
        self.model.opt.timestep = .004
        self.data = mujoco.MjData(self.model)
        self.adapter = Model38000(self.model)
        self.data.qpos[2] = .755
        self.data.qpos[self.adapter._policy_qpos_adr] = self.adapter._default_qpos_p
        mujoco.mj_forward(self.model, self.data)
        self.adapter.warm_start(self.data)
        self.pos0 = self.data.xpos[self.adapter.body_ids].copy()
        self.quat0 = self.data.xquat[self.adapter.body_ids].copy()
        self.wrist = self.adapter.metadata['selected_body_names'].index('right_wrist_yaw_link')
        self.wrists = [self.adapter.metadata['selected_body_names'].index(n)
                       for n in ('left_wrist_yaw_link', 'right_wrist_yaw_link')]
        self.servo = WristReferenceServo() if reference_servo else None
        self.reference = self.pos0[self.wrist].copy()
        self.start = self.reference.copy()
        self.goal = self.reference.copy()
        self.t0 = 0.
        self.duration = 1.
        self.active = None
        self.commands = {}
        self.observations = {}
        self.sequence = 0
        self.grip = 0.
        self.reason = None
        self.last_sim_time = float(self.data.time)
        names = self.adapter.metadata['joint_names']
        self.act = np.array([self.model.actuator(n).id for n in names])
        self.kp = self.adapter.kp[self.adapter.policy_jnt_idx]
        self.kd = self.adapter.kd[self.adapter.policy_jnt_idx]
        self.limits = self.model.jnt_actfrcrange[[self.model.joint(n).id for n in names]]
        self.fingers = list(DEX3_CLOSED_POS)
        self.fq = np.array([self.model.joint(n).qposadr[0] for n in self.fingers])
        self.fv = np.array([self.model.joint(n).dofadr[0] for n in self.fingers])
        self.fa = np.array([self.model.actuator(n).id for n in self.fingers])
        self.fl = self.model.jnt_actfrcrange[[self.model.joint(n).id for n in self.fingers]]
        self.closed = np.array([DEX3_CLOSED_POS[n] if n.startswith('right_') else 0. for n in self.fingers])

    def observe(self):
        self.sequence += 1
        key = f'obs_{self.sequence:06d}'
        packet = {'observation_id': key, 'sim_s': float(self.data.time),
                  'captured_monotonic_s': time.monotonic(),
                  'localization_source': 'sim_robot_state_diagnostic',
                  'wrist_world_m': self.data.xpos[self.adapter.body_ids[self.wrist]].tolist(),
                  'wrist_reference_world_m': self.reference_at(self.data.time).tolist(),
                  'wrist_tracking_error_world_m': (self.data.xpos[self.adapter.body_ids[self.wrist]] - self.reference_at(self.data.time)).tolist(),
                  'joint_names': self.adapter.metadata['joint_names'],
                  'joint_position_rad': self.data.qpos[self.adapter._policy_qpos_adr].tolist(),
                  'finger_names': self.fingers,
                  'finger_position_rad': self.data.qpos[self.fq].tolist(),
                  'command_status': self.status(), 'stop_reason': self.reason}
        self.observations = {key: packet}
        return packet

    def move_wrist(self, observation_id, command_id, delta, duration=1.):
        delta = np.asarray(delta, dtype=float)
        if delta.shape != (3,) or not np.isfinite(delta).all() or np.linalg.norm(delta) > .030001:
            raise ValueError('Request must be a finite world-frame wrist delta <= 3 cm')
        if not np.isfinite(duration) or not .5 <= duration <= 3.:
            raise ValueError('Duration outside diagnostic range')
        fingerprint = (observation_id, tuple(delta), float(duration))
        if command_id in self.commands:
            if self.commands[command_id]['fingerprint'] != fingerprint:
                raise ValueError('Command ID reused for a different request')
            return self.commands[command_id]
        if self.reason or self.active:
            raise ValueError('Runtime stopped or motion already active')
        obs = self.observations.get(observation_id)
        if obs is None or time.monotonic() - obs['captured_monotonic_s'] > .5:
            raise ValueError('Observation expired')
        target = np.asarray(obs['wrist_world_m']) + delta
        if np.linalg.norm(target - self.pos0[self.wrist]) > .25:
            raise ValueError('Target outside bounded diagnostic workspace')
        self.start = self.reference_at(self.data.time).copy()
        self.goal = target.copy()  # Frozen observation anchor, never accumulated each tick.
        self.t0, self.duration = float(self.data.time), float(duration)
        self.active = command_id
        record = {'command_id': command_id, 'fingerprint': fingerprint,
                  'frame': 'world', 'controlled_link': 'right_wrist_yaw_link',
                  'observation_anchor_world_m': list(obs['wrist_world_m']),
                  'reference_start_world_m': self.start.tolist(),
                  'requested_delta_world_m': delta.tolist(),
                  'reference_delta_world_m': (target-self.start).tolist(),
                  'approved_wrist_world_m': target.tolist(), 'status': 'executing',
                  'start_sim_s': self.t0, 'duration_s': self.duration, 'reached_ticks': 0}
        self.commands[command_id] = record
        return record

    def set_gripper(self, closure):
        if self.reason or not np.isfinite(closure) or not 0 <= closure <= 1:
            raise ValueError('Invalid gripper request or runtime stopped')
        self.grip = float(closure)
        return {'requested_closure': self.grip, 'profile': 'Dex3 mechanical fraction; grasp not calibrated'}

    def reference_at(self, when):
        u = np.clip((np.asarray(when) - self.t0) / self.duration, 0., 1.)
        return self.start + np.asarray(3*u*u - 2*u*u*u)[..., None] * (self.goal - self.start)

    def cancel(self):
        if self.active:
            self.commands[self.active]['status'] = 'cancelled'
        self.active = None
        self.start = self.goal = self.reference_at(self.data.time).copy()
        return {'status': 'cancelled_reference_hold', 'hardware_validated': False}

    def status(self):
        if not self.commands:
            return {'status': 'idle'}
        return dict(next(reversed(self.commands.values())))

    def tick(self):
        if self.reason:
            return
        if abs(self.data.time - self.last_sim_time) > 1e-9:
            self.reason = 'external_sim_time_change'
            if self.active:
                self.commands[self.active]['status'] = 'aborted'
                self.active = None
            return
        pos = np.tile(self.pos0, (34, 1, 1)).astype(np.float32)
        pos[:, self.wrist] = self.reference_at(self.data.time + np.arange(34) * .02)
        if self.servo:
            pos[:, self.wrists] = self.servo.correct(pos[:, self.wrists], self.data.xpos[self.adapter.body_ids[self.wrists]])
        motion = SimpleNamespace(num_frames=34, body_pos_w=pos,
                                 body_quat_w=np.tile(self.quat0, (34, 1, 1)).astype(np.float32))
        target = self.adapter.infer(self.data, motion, 0)
        if not np.isfinite(target).all():
            self.reason = 'nonfinite_policy_output'
            return
        for _ in range(5):
            tq = self.kp * (target - self.data.qpos[self.adapter._policy_qpos_adr]) - self.kd * self.data.qvel[self.adapter._policy_dof_adr]
            self.data.ctrl[self.act] = np.clip(tq, self.limits[:, 0], self.limits[:, 1])
            ft = 20*(self.closed*self.grip - self.data.qpos[self.fq]) - self.data.qvel[self.fv]
            self.data.ctrl[self.fa] = np.clip(ft, self.fl[:, 0], self.fl[:, 1])
            mujoco.mj_step(self.model, self.data)
        self.last_sim_time = float(self.data.time)
        mujoco.mj_forward(self.model, self.data)
        self.reference = self.reference_at(self.data.time).copy()
        tilt = np.rad2deg(np.arccos(np.clip(self.data.xmat[self.adapter.body_ids[0]].reshape(3, 3)[2, 2], -1, 1)))
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            self.reason = 'nonfinite_state'
        elif self.data.qpos[2] < .55 or tilt > 25:
            self.reason = 'diagnostic_stability_stop'
        if self.active:
            record = self.commands[self.active]
            error = np.linalg.norm(self.data.xpos[self.adapter.body_ids[self.wrist]] - self.goal)
            record['actual_error_m'] = float(error)
            elapsed = self.data.time - self.t0
            record['reference_finished'] = bool(elapsed >= self.duration)
            record['reached_ticks'] = record['reached_ticks'] + 1 if error < .01 else 0
            if self.reason:
                record['status'] = 'aborted'
            elif record['reference_finished'] and record['reached_ticks'] >= 5:
                record['status'] = 'target_reached'
            elif elapsed > self.duration + 2:
                record['status'] = 'timed_out'
            if record['status'] != 'executing':
                self.active = None
