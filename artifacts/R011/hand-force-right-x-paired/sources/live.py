"""Simulation-only single-writer runtime. Actor packets omit object state.

The motion interface is wrist/world coordinates until TCP calibration exists.
Runtime robot localization is currently simulator state, explicitly diagnostic.
"""
import time
from types import SimpleNamespace

import mujoco
import numpy as np
from locomanip.utils.dex3 import DEX3_CLOSED_POS
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose, interpolate_pose
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
    def __init__(self, *, reference_servo=False, table_offset_x=0., physics_dt=.004):
        self.model = tabletop_model(table_offset_x)
        if not np.isfinite(physics_dt) or physics_dt <= 0:
            raise ValueError('physics_dt must be positive and finite')
        self.physics_substeps = round(.02/physics_dt)
        if self.physics_substeps < 1 or not np.isclose(self.physics_substeps*physics_dt, .02):
            raise ValueError('physics_dt must divide the 20 ms tracker period')
        self.model.opt.timestep = physics_dt
        self.data = mujoco.MjData(self.model)
        self.adapter = Model38000(self.model)
        self.data.qpos[2] = .755
        self.data.qpos[self.adapter._policy_qpos_adr] = self.adapter._default_qpos_p
        mujoco.mj_forward(self.model, self.data)
        self.adapter.warm_start(self.data)
        self.pos0 = self.data.xpos[self.adapter.body_ids].copy()
        self.quat0 = self.data.xquat[self.adapter.body_ids].copy()
        selected = self.adapter.metadata['selected_body_names']
        self.four = np.array([selected.index(name) for name in FOUR_POINT_NAMES])
        initial = FourPointPose(self.pos0[self.four], self.quat0[self.four])
        self._reference_pose = initial.copy()
        self._start_pose = initial.copy()
        self._goal_pose = initial.copy()
        self.right_four = FOUR_POINT_NAMES.index('right_wrist_yaw_link')
        self.wrist = self.adapter.metadata['selected_body_names'].index('right_wrist_yaw_link')
        self.wrists = [self.adapter.metadata['selected_body_names'].index(n)
                       for n in ('left_wrist_yaw_link', 'right_wrist_yaw_link')]
        self.servo = WristReferenceServo() if reference_servo else None
        self.t0 = 0.
        self.duration = 1.
        self.active = None
        self.commands = {}
        self.observations = {}
        self.sequence = 0
        self.grip = 0.
        self.grips = {'left': 0., 'right': 0.}
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
        self.closed = np.array([DEX3_CLOSED_POS[n] for n in self.fingers])

    @property
    def reference(self):
        return self._reference_pose.positions[self.right_four]

    @reference.setter
    def reference(self, value):
        self._reference_pose.positions[self.right_four] = np.asarray(value, dtype=float)

    @property
    def start(self):
        return self._start_pose.positions[self.right_four]

    @start.setter
    def start(self, value):
        self._start_pose.positions[self.right_four] = np.asarray(value, dtype=float)

    @property
    def goal(self):
        return self._goal_pose.positions[self.right_four]

    @goal.setter
    def goal(self, value):
        self._goal_pose.positions[self.right_four] = np.asarray(value, dtype=float)

    def observe(self):
        self.sequence += 1
        key = f'obs_{self.sequence:06d}'
        measured = FourPointPose(self.data.xpos[self.adapter.body_ids[self.four]],
                                 self.data.xquat[self.adapter.body_ids[self.four]])
        reference = self.reference_pose_at(self.data.time)
        packet = {'observation_id': key, 'sim_s': float(self.data.time),
                  'captured_monotonic_s': time.monotonic(),
                  'localization_source': 'sim_robot_state_diagnostic',
                  'wrist_world_m': self.data.xpos[self.adapter.body_ids[self.wrist]].tolist(),
                  'wrist_reference_world_m': self.reference_at(self.data.time).tolist(),
                  'wrist_tracking_error_world_m': (self.data.xpos[self.adapter.body_ids[self.wrist]] - self.reference_at(self.data.time)).tolist(),
                  'four_point_world': measured.to_mapping(),
                  'four_point_reference_world': reference.to_mapping(),
                  'four_point_position_error_world_m': (measured.positions-reference.positions).tolist(),
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

    def move_four_points(self, observation_id, command_id, targets, duration=1.):
        target = FourPointPose.from_mapping(targets)
        if not np.isfinite(duration) or not .5 <= duration <= 3.:
            raise ValueError('Duration outside diagnostic range')
        fingerprint = (observation_id, tuple(target.positions.flat),
                       tuple(target.quaternions.flat), float(duration))
        if command_id in self.commands:
            if self.commands[command_id]['fingerprint'] != fingerprint:
                raise ValueError('Command ID reused for a different request')
            return self.commands[command_id]
        if self.reason or self.active:
            raise ValueError('Runtime stopped or motion already active')
        obs = self.observations.get(observation_id)
        if obs is None or time.monotonic() - obs['captured_monotonic_s'] > .5:
            raise ValueError('Observation expired')
        measured = FourPointPose.from_mapping(obs['four_point_world'])
        displacement = np.linalg.norm(target.positions-measured.positions, axis=1)
        angle = 2*np.arccos(np.clip(np.abs(np.sum(target.quaternions*measured.quaternions, axis=1)), 0., 1.))
        if np.any(displacement > .030001) or np.any(angle > .100001):
            raise ValueError('Each four-point step is limited to 3 cm and 0.1 rad')
        if np.any(np.linalg.norm(target.positions-self.pos0[self.four], axis=1) > .25):
            raise ValueError('Target outside bounded diagnostic workspace')
        self._start_pose = self.reference_pose_at(self.data.time)
        self._goal_pose = target
        self.t0, self.duration = float(self.data.time), float(duration)
        self.active = command_id
        record = {'command_id': command_id, 'fingerprint': fingerprint,
                  'mode': 'UMI-4', 'frame': 'world',
                  'controlled_links': list(FOUR_POINT_NAMES),
                  'observation_anchor': measured.to_mapping(),
                  'approved_target': target.to_mapping(), 'status': 'executing',
                  'start_sim_s': self.t0, 'duration_s': self.duration,
                  'reached_ticks': 0, '_four_indices': list(range(4))}
        self.commands[command_id] = record
        return record

    def set_gripper(self, closure):
        if self.reason or not np.isfinite(closure) or not 0 <= closure <= 1:
            raise ValueError('Invalid gripper request or runtime stopped')
        self.grip = float(closure)
        self.grips['right'] = self.grip
        return {'requested_closure': self.grip, 'profile': 'Dex3 mechanical fraction; grasp not calibrated'}

    def set_grippers(self, left, right):
        values = np.asarray([left, right], dtype=float)
        if self.reason or not np.isfinite(values).all() or np.any(values < 0) or np.any(values > 1):
            raise ValueError('Invalid gripper request or runtime stopped')
        self.grips = {'left': float(left), 'right': float(right)}
        self.grip = self.grips['right']
        return {'requested_closure': dict(self.grips),
                'profile': 'Dex3 mechanical fraction; grasp not calibrated'}

    def reference_at(self, when):
        u = np.clip((np.asarray(when) - self.t0) / self.duration, 0., 1.)
        positions, _ = interpolate_pose(self._start_pose, self._goal_pose, u)
        return positions[..., self.right_four, :]

    def reference_pose_at(self, when):
        u = float(np.clip((when-self.t0) / self.duration, 0., 1.))
        positions, quaternions = interpolate_pose(self._start_pose, self._goal_pose, u)
        return FourPointPose(positions, quaternions)

    def cancel(self):
        if self.active:
            self.commands[self.active]['status'] = 'cancelled'
        self.active = None
        pose = self.reference_pose_at(self.data.time)
        self._start_pose = pose.copy()
        self._goal_pose = pose.copy()
        self._reference_pose = pose.copy()
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
        phase = np.clip((self.data.time + np.arange(34)*.02-self.t0) / self.duration, 0., 1.)
        four_pos, four_quat = interpolate_pose(self._start_pose, self._goal_pose, phase)
        pos[:, self.four] = four_pos
        quat = np.tile(self.quat0, (34, 1, 1)).astype(np.float32)
        quat[:, self.four] = four_quat
        if self.servo:
            pos[:, self.wrists] = self.servo.correct(pos[:, self.wrists], self.data.xpos[self.adapter.body_ids[self.wrists]])
        motion = SimpleNamespace(num_frames=34, body_pos_w=pos,
                                 body_quat_w=quat)
        target = self.adapter.infer(self.data, motion, 0)
        if not np.isfinite(target).all():
            self.reason = 'nonfinite_policy_output'
            return
        for _ in range(self.physics_substeps):
            tq = self.kp * (target - self.data.qpos[self.adapter._policy_qpos_adr]) - self.kd * self.data.qvel[self.adapter._policy_dof_adr]
            self.data.ctrl[self.act] = np.clip(tq, self.limits[:, 0], self.limits[:, 1])
            closure = np.array([self.grips['left'] if name.startswith('left_') else self.grips['right']
                                for name in self.fingers])
            ft = 20*(self.closed*closure - self.data.qpos[self.fq]) - self.data.qvel[self.fv]
            self.data.ctrl[self.fa] = np.clip(ft, self.fl[:, 0], self.fl[:, 1])
            mujoco.mj_step(self.model, self.data)
        self.last_sim_time = float(self.data.time)
        mujoco.mj_forward(self.model, self.data)
        self._reference_pose = self.reference_pose_at(self.data.time)
        tilt = np.rad2deg(np.arccos(np.clip(self.data.xmat[self.adapter.body_ids[0]].reshape(3, 3)[2, 2], -1, 1)))
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            self.reason = 'nonfinite_state'
        elif self.data.qpos[2] < .55 or tilt > 25:
            self.reason = 'diagnostic_stability_stop'
        if self.active:
            record = self.commands[self.active]
            indices = record.get('_four_indices', [self.right_four])
            measured_pos = self.data.xpos[self.adapter.body_ids[self.four]][indices]
            position_error = np.linalg.norm(measured_pos-self._goal_pose.positions[indices], axis=1)
            error = float(np.max(position_error))
            record['actual_error_m'] = error
            record['actual_position_error_m_by_link'] = {
                FOUR_POINT_NAMES[i]: float(e) for i, e in zip(indices, position_error)
            }
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
