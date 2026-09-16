"""Host-only native task evaluators.

Actor observations must never include evaluator state or object truth.  The
harness may expose only the public three-state outcome.
"""
from typing import Protocol


class TaskEvaluator(Protocol):
    def reset(self, backend): ...
    def update(self, backend): ...
    def outcome(self, backend): ...


class SimpleNativeEvaluator:
    """Use SIMPLE's existing per-task criterion, without extra reward calls."""
    def reset(self, backend):
        if backend._native_task_success:
            raise ValueError('SIMPLE scene already successful before actor control')
        self._outcome = 'in_progress'

    def update(self, backend):
        if backend.reason:
            self._outcome = 'failure'
        elif backend._native_task_success:
            self._outcome = 'success'

    def outcome(self, backend):
        return self._outcome


class LiftEvaluator:
    """Declare success after one hidden body stays above its reset height."""

    def __init__(self, *, body_name='diagnostic_cube', min_lift_m=.05,
                 sustain_ticks=13):
        if min_lift_m <= 0 or sustain_ticks < 1:
            raise ValueError('Lift threshold and sustain_ticks must be positive')
        self.body_name = body_name
        self.min_lift_m = float(min_lift_m)
        self.sustain_ticks = int(sustain_ticks)
        self._body_id = None
        self._initial_z = None
        self._dwell = 0
        self._outcome = 'in_progress'

    def reset(self, backend):
        self._body_id = int(backend.model.body(self.body_name).id)
        self._initial_z = float(backend.data.xpos[self._body_id, 2])
        self._dwell = 0
        self._outcome = 'in_progress'

    def update(self, backend):
        if self._initial_z is None:
            raise RuntimeError('Evaluator must be reset before update')
        if getattr(backend, 'reason', None):
            self._outcome = 'failure'
            return
        lifted = float(backend.data.xpos[self._body_id, 2]) - self._initial_z >= self.min_lift_m
        self._dwell = self._dwell + 1 if lifted else 0
        if self._dwell >= self.sustain_ticks:
            self._outcome = 'success'

    def outcome(self, backend):
        return self._outcome


class GraspLiftEvaluator(LiftEvaluator):
    """Host-only sustained lift with at least two contacting finger families."""
    def __init__(self):
        super().__init__(min_lift_m=.05, sustain_ticks=25)

    def _grasped(self, backend):
        import mujoco
        import numpy as np
        fingers = {'left': set(), 'right': set()}
        for i in range(backend.data.ncon):
            contact = backend.data.contact[i]
            geoms = [backend.model.geom(int(g)) for g in (contact.geom1, contact.geom2)]
            if not any(int(g.bodyid[0]) == self._body_id for g in geoms):
                continue
            force = np.zeros(6)
            mujoco.mj_contactForce(backend.model, backend.data, i, force)
            if force[0] <= .01:
                continue
            for geom in geoms:
                for side in fingers:
                    for finger in ('thumb', 'index', 'middle'):
                        if (geom.name or '').startswith(f'{side}_hand_{finger}_'):
                            fingers[side].add(finger)
        closure = backend.gripper_command_at(backend.data.time)
        return any(len(fingers[side]) >= 2 and closure[side] > .1 for side in fingers)

    def update(self, backend):
        if getattr(backend, 'reason', None):
            self._outcome = 'failure'
        elif self._grasped(backend):
            super().update(backend)
        else:
            self._dwell = 0


class DoorPushEvaluator:
    """Host-only: hand contact, >=30 degrees opening, and 1 s physical dwell.

    The scene starts closed and its positive hinge direction opens the door.
    A released door may remain open; a passive swing without hand contact fails.
    """
    def __init__(self, joint_name='articulate_joint_1'):
        self.joint_name = joint_name

    def reset(self, backend):
        model = backend.model
        joint = model.joint(self.joint_name)
        self._qadr = int(joint.qposadr[0])
        self._initial = float(backend.data.qpos[self._qadr])
        self._door_bodies = {int(model.jnt_bodyid[joint.id])}
        self._hand_bodies = {model.body(f'{s}_wrist_yaw_link').id for s in ('left', 'right')}
        # MuJoCo body IDs put parents before their descendants.
        for body in range(1, model.nbody):
            for subtree in (self._door_bodies, self._hand_bodies):
                if model.body_parentid[body] in subtree:
                    subtree.add(body)
        self._pushed, self._since, self._outcome = False, None, 'in_progress'

    def _hand_contact(self, backend):
        import mujoco
        import numpy as np
        for i in range(backend.data.ncon):
            contact = backend.data.contact[i]
            bodies = {int(backend.model.geom_bodyid[g]) for g in (contact.geom1, contact.geom2)}
            if bodies & self._door_bodies and bodies & self._hand_bodies:
                force = np.zeros(6)
                mujoco.mj_contactForce(backend.model, backend.data, i, force)
                if force[0] > .01:
                    return True
        return False

    def update(self, backend):
        import math
        if getattr(backend, 'reason', None):
            self._outcome = 'failure'
            return
        self._pushed |= self._hand_contact(backend)
        opened = float(backend.data.qpos[self._qadr])-self._initial >= math.pi/6
        if opened and self._pushed:
            if self._since is None:
                self._since = float(backend.data.time)
            if float(backend.data.time)-self._since >= 1.:
                self._outcome = 'success'
        else:
            self._since = None

    def outcome(self, backend):
        return self._outcome
