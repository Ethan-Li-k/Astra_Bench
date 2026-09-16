"""Simulation-only single-writer runtime. Actor packets omit object state.

The motion interface is wrist/world coordinates until TCP calibration exists.
Runtime robot localization is currently simulator state, explicitly diagnostic.
"""
import time
import math
from types import SimpleNamespace

import mujoco
import numpy as np
from locomanip.utils.dex3 import DEX3_CLOSED_POS
from locomanip.utils.hand_force_comp import HandForceCompensation
from locomanip.utils.wrist_pi import WristPI
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose, interpolate_pose
from rsi.scalebfm import Model38000, SCENE
from rsi.reference_servo import WristReferenceServo
from rsi.reference_sequence import CONTINUOUS_CONTRACT, bounded_sequence


POSITION_TOLERANCE_M = .01
ROTATION_TOLERANCE_RAD = .05


def tabletop_model(offset_x=0., table_only_offset_x=0.):
    # All object geometry belongs to environment construction, not actor input.
    robot = mujoco.MjModel.from_xml_path(str(SCENE))
    collision_names = [robot.geom(i).name for i in range(robot.ngeom)
                       if robot.geom(i).name and 'collision' in robot.geom(i).name]
    pairs = ''.join(f'<pair geom1="{name}" geom2="{other}"/>'
                    for name in collision_names
                    for other in ('diagnostic_table', 'diagnostic_cube_geom'))
    legs = ''.join(f'<geom name="table_leg_{i}" type="box" pos="{x+offset_x+table_only_offset_x} {y} 0.285" '
                   'size="0.02 0.02 0.285" rgba="0.35 0.24 0.15 1" contype="1" conaffinity="5"/>'
                   for i, (x, y) in enumerate(((.28, -.37), (.52, -.37), (.28, -.07), (.52, -.07))))
    xml = f'''<mujoco><include file="{SCENE}"/>
    <compiler meshdir="{SCENE.parent / 'assets'}"/>
    <worldbody>
      {legs}
      <geom name="diagnostic_table" type="box" pos="{.40+offset_x+table_only_offset_x} -0.22 0.60"
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
    def __init__(self, *, reference_servo=False, hand_force_comp=False,
                 wrist_pi=False, table_offset_x=0., table_only_offset_x=0., physics_dt=.004,
                 model=None, data=None, workspace_radius_m=.25,
                 stability_min_pelvis_m=.55, stability_max_tilt_deg=25.):
        if sum(map(bool, (reference_servo, hand_force_comp, wrist_pi))) > 1:
            raise ValueError('Choose at most one local wrist controller')
        self.model = model if model is not None else tabletop_model(table_offset_x, table_only_offset_x)
        if not 0 < stability_min_pelvis_m <= .75 or not 0 < stability_max_tilt_deg < 90:
            raise ValueError('Invalid explicit simulation stability limits')
        self.stability_min_pelvis_m=float(stability_min_pelvis_m)
        self.stability_max_tilt_deg=float(stability_max_tilt_deg)
        if not np.isfinite(workspace_radius_m) or workspace_radius_m <= 0:
            raise ValueError('workspace_radius_m must be positive and finite')
        self.workspace_radius_m = float(workspace_radius_m)
        self.translation_limit_m_by_link = {name: .03 for name in FOUR_POINT_NAMES}
        if not np.isfinite(physics_dt) or physics_dt <= 0:
            raise ValueError('physics_dt must be positive and finite')
        self.physics_substeps = round(.02/physics_dt)
        if self.physics_substeps < 1 or not np.isclose(self.physics_substeps*physics_dt, .02):
            raise ValueError('physics_dt must divide the 20 ms tracker period')
        self.model.opt.timestep = physics_dt
        self.data = data if data is not None else mujoco.MjData(self.model)
        self.adapter = Model38000(self.model)
        # A known robot inertial model plus measured FK supplies this estimate.
        # The independently free cube and world/table are not descendants.
        robot_bodies={int(self.adapter.body_ids[0])}
        for bid in range(self.model.nbody):
            if int(self.model.body_parentid[bid]) in robot_bodies:robot_bodies.add(bid)
        self.robot_com_bodies=np.array(sorted(robot_bodies),dtype=int)
        self.robot_com_masses=self.model.body_mass[self.robot_com_bodies].copy()
        if data is None:
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
        self._reference_sequence = None
        self.continuous_chunks_enabled = False
        self.last_control_feedback = None
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
        self.grip_start = dict(self.grips)
        self.grip_t0 = float(self.data.time)
        self.grip_duration = 0.
        self.reason = None
        self.last_sim_time = float(self.data.time)
        names = self.adapter.metadata['joint_names']
        self.hand_comp = (HandForceCompensation(
            self.model, kp_task=2000., kd_task=30., max_force=20.)
            if hand_force_comp else None)
        self.hand_comp_dof = np.array([
            self.model.joint(name).dofadr[0] - 6 for name in names])
        if not np.array_equal(self.hand_comp_dof, self.adapter._policy_dof_adr - 6):
            raise RuntimeError('Named policy/non-root DOF mapping mismatch')
        self.act = np.array([self.model.actuator(n).id for n in names])
        self.kp = self.adapter.kp[self.adapter.policy_jnt_idx]
        self.kd = self.adapter.kd[self.adapter.policy_jnt_idx]
        self.limits = self.model.jnt_actfrcrange[[self.model.joint(n).id for n in names]]
        self.wrist_pi = (WristPI(
            self.model, names, self.kp, self.limits[:, 1]) if wrist_pi else None)
        self.wrist_pi_tau = np.zeros(len(names))
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
                  'pelvis_world': {
                      'position_world_m': self.data.xpos[self.adapter.body_ids[0]].tolist(),
                      'quaternion_wxyz': self.data.xquat[self.adapter.body_ids[0]].tolist()},
                  'robot_com_model': {
                      'position_world_m':np.average(self.data.xipos[self.robot_com_bodies],
                          axis=0,weights=self.robot_com_masses).tolist(),
                      'meaning':'Robot-only known inertial model plus measured root/joint FK; excludes objects and carried loads. Not a contact sensor or proof of dynamic balance.'},
                  'wrist_world_m': self.data.xpos[self.adapter.body_ids[self.wrist]].tolist(),
                  'wrist_reference_world_m': self.reference_at(self.data.time).tolist(),
                  'wrist_tracking_error_world_m': (self.data.xpos[self.adapter.body_ids[self.wrist]] - self.reference_at(self.data.time)).tolist(),
                  'four_point_world': measured.to_mapping(),
                  'four_point_reference_world': reference.to_mapping(),
                  'translation_limit_m_by_link': dict(self.translation_limit_m_by_link),
                  'four_point_position_error_world_m': (measured.positions-reference.positions).tolist(),
                  'joint_names': self.adapter.metadata['joint_names'],
                  'joint_position_rad': self.data.qpos[self.adapter._policy_qpos_adr].tolist(),
                  'robot_control_feedback': self.last_control_feedback,
                  'finger_names': self.fingers,
                  'finger_position_rad': self.data.qpos[self.fq].tolist(),
                  'gripper_commanded_closure': self.gripper_command_at(self.data.time),
                  'gripper_goal_closure': dict(self.grips),
                  'command_status': self.status(), 'stop_reason': self.reason}
        if self.continuous_chunks_enabled:
            packet['continuous_chunk_contract'] = CONTINUOUS_CONTRACT
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
        if np.linalg.norm(target - self.pos0[self.wrist]) > self.workspace_radius_m:
            raise ValueError('Target outside bounded diagnostic workspace')
        self.start = self.reference_at(self.data.time).copy()
        self._reference_sequence = None
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
                  'start_sim_s': self.t0, 'duration_s': self.duration, 'reached_ticks': 0,
                  '_active_position_indices': [self.right_four],
                  '_active_orientation_indices': []}
        self.commands[command_id] = record
        return record

    def move_four_points(self, observation_id, command_id, targets, duration=1.,
                         position_names=FOUR_POINT_NAMES,
                         orientation_names=FOUR_POINT_NAMES):
        requested = FourPointPose.from_mapping(targets)
        position_names, orientation_names = tuple(position_names), tuple(orientation_names)
        for label, names in (('position', position_names),
                             ('orientation', orientation_names)):
            if len(names) != len(set(names)) or not set(names) <= set(FOUR_POINT_NAMES):
                raise ValueError(f'Active {label} names must be unique four-point links')
        position_indices = [FOUR_POINT_NAMES.index(name) for name in position_names]
        orientation_indices = [FOUR_POINT_NAMES.index(name) for name in orientation_names]
        if not np.isfinite(duration) or not .5 <= duration <= 3.:
            raise ValueError('Duration outside diagnostic range')
        fingerprint = (observation_id, tuple(requested.positions.flat),
                       tuple(requested.quaternions.flat), float(duration),
                       position_names, orientation_names)
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
        displacement = np.linalg.norm(requested.positions-measured.positions, axis=1)
        angle = 2*np.arccos(np.clip(np.abs(np.sum(
            requested.quaternions*measured.quaternions, axis=1)), 0., 1.))
        limits = np.array([self.translation_limit_m_by_link[n] for n in FOUR_POINT_NAMES])
        if (np.any(displacement[position_indices] > limits[position_indices]+1e-6)
                or np.any(angle[orientation_indices] > .100001)):
            raise ValueError('Four-point step exceeds its named translation limit or 0.1 rad')
        if np.any(np.linalg.norm(
                requested.positions[position_indices]-self.pos0[self.four][position_indices],
                axis=1) > self.workspace_radius_m):
            raise ValueError('Target outside bounded diagnostic workspace')
        self._start_pose = self.reference_pose_at(self.data.time)
        self._reference_sequence = None
        approved = self._start_pose.copy()
        approved.positions[position_indices] = requested.positions[position_indices]
        approved.quaternions[orientation_indices] = requested.quaternions[orientation_indices]
        self._goal_pose = approved
        self.t0, self.duration = float(self.data.time), float(duration)
        self.active = command_id
        record = {'command_id': command_id, 'fingerprint': fingerprint,
                  'command_kind': ('four_point' if position_indices or orientation_indices
                                   else 'gripper_only'),
                  'mode': 'UMI-4', 'frame': 'world',
                  'controlled_links': list(FOUR_POINT_NAMES),
                  'active_position_links': list(position_names),
                  'active_orientation_links': list(orientation_names),
                  'observation_anchor': measured.to_mapping(),
                  'requested_target': requested.to_mapping(),
                  'approved_target': approved.to_mapping(), 'status': 'executing',
                  'start_sim_s': self.t0, 'duration_s': self.duration,
                  'reached_ticks': 0,
                  '_active_position_indices': position_indices,
                  '_active_orientation_indices': orientation_indices}
        self.commands[command_id] = record
        return record

    def move_four_point_sequence(self, observation_id, command_id, waypoints):
        if not self.continuous_chunks_enabled:
            raise ValueError('Continuous chunks are not enabled for this backend')
        fingerprint = (observation_id, tuple((tuple(w['target'].positions.flat),
            tuple(w['target'].quaternions.flat), float(w['duration_s']),
            tuple(w['active']['position']), tuple(w['active']['orientation']),
            tuple(sorted(w['grippers'].items()))) for w in waypoints))
        if command_id in self.commands:
            if self.commands[command_id]['fingerprint'] != fingerprint:
                raise ValueError('Command ID reused for a different continuous request')
            return self.commands[command_id]
        if self.reason or self.active:
            raise ValueError('Runtime stopped or motion already active')
        obs = self.observations.get(observation_id)
        if obs is None or time.monotonic()-obs['captured_monotonic_s'] > .5:
            raise ValueError('Observation expired')
        measured = FourPointPose.from_mapping(obs['four_point_world'])
        sequence = bounded_sequence(self.data.time, measured, waypoints,
                                    self.pos0[self.four], self.workspace_radius_m)
        # Do not recover duration by subtracting large absolute simulation
        # timestamps: five legal .6s segments can become 3.000000000000007s.
        duration=min(3.,math.fsum(float(w['duration_s']) for w in waypoints))
        self.validate_grippers(**waypoints[0]['grippers'],duration=duration)
        active = waypoints[0]['active']
        # Mutation begins only after the complete chunk has passed validation.
        self._start_pose, self._goal_pose = sequence.poses[0].copy(), sequence.poses[-1].copy()
        self._reference_sequence = sequence
        self.t0, self.duration = float(sequence.times[0]), duration
        self.active = command_id
        record = {'command_id': command_id, 'fingerprint': fingerprint,
                  'command_kind': 'four_point_continuous', 'mode': 'UMI-4', 'frame': 'world',
                  'controlled_links': list(FOUR_POINT_NAMES),
                  'active_position_links': list(active['position']),
                  'active_orientation_links': list(active['orientation']),
                  'observation_anchor': measured.to_mapping(),
                  'approved_target': self._goal_pose.to_mapping(),
                  'approved_knots': [p.to_mapping() for p in sequence.poses],
                  'knot_sim_s': sequence.times.tolist(), 'status': 'executing',
                  'start_sim_s': self.t0, 'duration_s': self.duration, 'reached_ticks': 0,
                  '_active_position_indices': [FOUR_POINT_NAMES.index(n) for n in active['position']],
                  '_active_orientation_indices': [FOUR_POINT_NAMES.index(n) for n in active['orientation']]}
        self.commands[command_id] = record
        return record

    def gripper_command_at(self, when):
        if self.grip_duration == 0:
            alpha = 1.
        else:
            alpha = float(np.clip((when-self.grip_t0)/self.grip_duration, 0., 1.))
        return {side: self.grip_start[side] + alpha*(self.grips[side]-self.grip_start[side])
                for side in ('left', 'right')}

    def set_gripper(self, closure, duration=0.):
        if self.reason or not np.isfinite(closure) or not 0 <= closure <= 1:
            raise ValueError('Invalid gripper request or runtime stopped')
        return self.set_grippers(self.grips['left'], closure, duration=duration)

    def validate_grippers(self, left, right, duration=0.):
        values = np.asarray([left, right], dtype=float)
        duration = float(duration)
        if (self.reason or not np.isfinite(values).all()
                or np.any(values < 0) or np.any(values > 1)
                or not np.isfinite(duration)
                or not (duration == 0. or .5 <= duration <= 3.)):
            raise ValueError('Invalid gripper request or runtime stopped')
        return duration

    def set_grippers(self, left, right, duration=0.):
        duration=self.validate_grippers(left,right,duration)
        self.grip_start = self.gripper_command_at(self.data.time)
        self.grips = {'left': float(left), 'right': float(right)}
        self.grip = self.grips['right']
        self.grip_t0 = float(self.data.time)
        self.grip_duration = duration
        if self.active:
            self.commands[self.active]['gripper_ramp'] = {
                'start': dict(self.grip_start), 'goal': dict(self.grips),
                'duration_s': duration,
                'evidence': 'commanded closure only; not contact or grasp'}
        return {'requested_closure': dict(self.grips),
                'duration_s': duration,
                'profile': 'Dex3 mechanical fraction; grasp not calibrated'}

    def reference_at(self, when):
        if self._reference_sequence is not None:
            return self._reference_sequence.sample(when)[0][..., self.right_four, :]
        u = np.clip((np.asarray(when) - self.t0) / self.duration, 0., 1.)
        positions, _ = interpolate_pose(self._start_pose, self._goal_pose, u)
        return positions[..., self.right_four, :]

    def reference_pose_at(self, when):
        if self._reference_sequence is not None:
            return self._reference_sequence.pose_at(when)
        u = float(np.clip((when-self.t0) / self.duration, 0., 1.))
        positions, quaternions = interpolate_pose(self._start_pose, self._goal_pose, u)
        return FourPointPose(positions, quaternions)

    def cancel(self):
        if self.active:
            self.commands[self.active]['status'] = 'cancelled'
        self.active = None
        pose = self.reference_pose_at(self.data.time)
        self._reference_sequence = None
        self._start_pose = pose.copy()
        self._goal_pose = pose.copy()
        self._reference_pose = pose.copy()
        self.grips = self.gripper_command_at(self.data.time)
        self.grip_start = dict(self.grips)
        self.grip_t0 = float(self.data.time)
        self.grip_duration = 0.
        self.grip = self.grips['right']
        if self.wrist_pi:
            self.wrist_pi.reset()
            self.wrist_pi_tau[:] = 0.
        return {'status': 'cancelled_reference_hold', 'hardware_validated': False}

    def status(self):
        if not self.commands:
            return {'status': 'idle'}
        return dict(next(reversed(self.commands.values())))

    def _advance_physics(self, target):
        for _ in range(self.physics_substeps):
            tq = self.kp * (target - self.data.qpos[self.adapter._policy_qpos_adr]) - self.kd * self.data.qvel[self.adapter._policy_dof_adr]
            tq += self.wrist_pi_tau
            if self.hand_comp:
                ref = self.reference_pose_at(self.data.time).positions
                extra = self.hand_comp.compute(self.model, self.data, ref[0], ref[1])
                tq += extra[self.hand_comp_dof]
            self.data.ctrl[self.act] = np.clip(tq, self.limits[:, 0], self.limits[:, 1])
            grip_command = self.gripper_command_at(self.data.time)
            closure = np.array([grip_command['left'] if name.startswith('left_') else grip_command['right']
                                for name in self.fingers])
            ft = 20*(self.closed*closure - self.data.qpos[self.fq]) - self.data.qvel[self.fv]
            self.data.ctrl[self.fa] = np.clip(ft, self.fl[:, 0], self.fl[:, 1])
            mujoco.mj_step(self.model, self.data)

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
        if self._reference_sequence is not None:
            four_pos, four_quat = self._reference_sequence.sample(self.data.time+np.arange(34)*.02)
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
        if self.wrist_pi and self.active:
            ref = self.reference_pose_at(self.data.time)
            wrist_body_ids = self.adapter.body_ids[self.wrists]
            ref_pos, ref_quat = ref.positions[:2].copy(), ref.quaternions[:2].copy()
            act_pos = self.data.xpos[wrist_body_ids]
            act_quat = self.data.xquat[wrist_body_ids]
            record = self.commands[self.active]
            active_pos = set(record.get('_active_position_indices', ()))
            active_rot = set(record.get('_active_orientation_indices', ()))
            for wrist_index in range(2):
                if wrist_index not in active_pos:
                    ref_pos[wrist_index] = act_pos[wrist_index]
                    self.wrist_pi.e_int[wrist_index, :3] = 0.
                if wrist_index not in active_rot:
                    ref_quat[wrist_index] = act_quat[wrist_index]
                    self.wrist_pi.e_int[wrist_index, 3:] = 0.
            self.wrist_pi_tau = self.wrist_pi(
                self.data.qpos[3:7], self.data.qpos[self.adapter._policy_qpos_adr],
                ref_pos, ref_quat, act_pos, act_quat, .02)
        elif self.wrist_pi:
            self.wrist_pi.reset()
            self.wrist_pi_tau[:] = 0.
        # Copy only this robot's own references and controller commands. These
        # are the actual float32 motion samples consumed by the adapter, before
        # its documented full-pelvis-frame transform; never scene/object data.
        offsets=np.asarray(self.adapter.future_idx,dtype=int)
        self.last_control_feedback={
            'command_id':self.active,'interval_start_sim_s':float(self.data.time),
            'interval_end_sim_s':float(self.data.time)+.02,
            'mode':'UMI-4','reference_frame':'world; adapter uses full measured pelvis quaternion',
            'link_names':list(FOUR_POINT_NAMES),'future_offsets_ticks':offsets.tolist(),
            'reference_times_sim_s':(float(self.data.time)+offsets*.02).tolist(),
            'reference_positions_world_m':motion.body_pos_w[offsets][:,self.four].tolist(),
            'reference_quaternions_wxyz':motion.body_quat_w[offsets][:,self.four].tolist(),
            'joint_target_before_wrist_pi_rad':target.tolist(),
            'wrist_pi_additive_torque_nm':self.wrist_pi_tau.tolist(),
            'meaning':'Commands for the just-executed 20ms interval, ordered by joint_names; not achieved poses or contact evidence. PD torque is clipped at unchanged original limits.'}
        self._advance_physics(target)
        self.last_sim_time = float(self.data.time)
        mujoco.mj_forward(self.model, self.data)
        self._reference_pose = self.reference_pose_at(self.data.time)
        tilt = np.rad2deg(np.arccos(np.clip(self.data.xmat[self.adapter.body_ids[0]].reshape(3, 3)[2, 2], -1, 1)))
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            self.reason = 'nonfinite_state'
        elif self.data.qpos[2] < self.stability_min_pelvis_m or tilt > self.stability_max_tilt_deg:
            self.reason = 'diagnostic_stability_stop'
        if self.active:
            record = self.commands[self.active]
            position_indices = record.get('_active_position_indices', [self.right_four])
            orientation_indices = record.get('_active_orientation_indices', [])
            measured_pos = self.data.xpos[self.adapter.body_ids[self.four]]
            measured_quat = self.data.xquat[self.adapter.body_ids[self.four]]
            position_error = np.linalg.norm(measured_pos-self._goal_pose.positions, axis=1)
            quat_dot = np.sum(measured_quat*self._goal_pose.quaternions, axis=1)
            rotation_error = 2*np.arccos(np.clip(np.abs(quat_dot), 0., 1.))
            error = float(np.max(position_error[position_indices])) if position_indices else 0.
            angular_error = (float(np.max(rotation_error[orientation_indices]))
                             if orientation_indices else 0.)
            record['actual_error_m'] = error
            record['actual_rotation_error_rad'] = angular_error
            record['actual_position_error_m_by_link'] = {
                name: float(value) for name, value in zip(FOUR_POINT_NAMES, position_error)
            }
            record['actual_rotation_error_rad_by_link'] = {
                name: float(value) for name, value in zip(FOUR_POINT_NAMES, rotation_error)
            }
            elapsed = self.data.time - self.t0
            record['reference_finished'] = bool(elapsed >= self.duration)
            reached = error < POSITION_TOLERANCE_M and angular_error < ROTATION_TOLERANCE_RAD
            record['reached_ticks'] = record['reached_ticks'] + 1 if reached else 0
            if self.reason:
                record['status'] = 'aborted'
            elif record['reference_finished'] and record['reached_ticks'] >= 5:
                record['status'] = ('gripper_duration_elapsed'
                                    if record['command_kind'] == 'gripper_only'
                                    else 'target_reached')
            elif elapsed > self.duration + 2:
                record['status'] = 'timed_out'
            if record['status'] != 'executing':
                self.active = None
