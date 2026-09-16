"""Explicit host-only completion gate; native SIMPLE rewards remain untouched."""
import numpy as np


PLACEMENT_CONTRACT = {
    'id': 'acquired-lift-then-released-container-support-v1',
    'scope': 'simple/G1WholebodyBendPickAndPlaceTeleop-v0',
    'native_reward_unchanged': True,
    'native_trigger_alone_terminates': False,
    'lift_m': .05, 'lift_hold_s': .5, 'released_support_s': 1.,
    'unsupported_release_grace_s': .3,
    'final_geometry_audit_required': True,
    'unmodified_native_benchmark': False,
}


class SimplePlacementEvaluator:
    """Reject pre-acquisition contact triggers and disconnected task phases.

    Final in/on-container geometry still requires the supervisor's video/trace
    audit. This gate is not a replacement for that independent task review.
    """
    def reset(self, backend):
        task, model = backend.env.task, backend.model
        if task.uid != 'g1_wholebody_bend_pick_and_place_teleop':
            raise ValueError('Placement gate is scoped to the reviewed box task')
        self.target = int(model.body(str(task.target.asset.label)).id)
        self.container = int(model.body(str(task.container.asset.label)).id)
        self.robot = {int(model.body('pelvis').id)}
        self.hands = {int(model.body(f'{s}_wrist_yaw_link').id) for s in ('left', 'right')}
        for body in range(1, model.nbody):
            for group in (self.robot, self.hands):
                if int(model.body_parentid[body]) in group:
                    group.add(body)
        self.initial_z = float(backend.data.xpos[self.target, 2])
        self._lift_since = self._release_since = self._gap_since = None
        self._acquired = False
        self._outcome = 'in_progress'
        self._last_sample = None
        # Only the host recorder consumes this state. Actor packets do not.
        backend.placement_evaluator = self

    def sample(self, backend):
        import mujoco
        contacted = set()
        fingers = {'left': set(), 'right': set()}
        for i in range(backend.data.ncon):
            c = backend.data.contact[i]
            a, b = (int(backend.model.geom_bodyid[g]) for g in (c.geom1, c.geom2))
            if self.target not in (a, b):
                continue
            force = np.zeros(6)
            mujoco.mj_contactForce(backend.model, backend.data, i, force)
            if force[0] <= .01:
                continue
            other = b if a == self.target else a
            contacted.add(other)
            name = backend.model.body(other).name or ''
            for side in fingers:
                for finger in ('thumb', 'index', 'middle'):
                    if name.startswith(f'{side}_hand_{finger}_'):
                        fingers[side].add(finger)
        closure = backend.gripper_command_at(backend.data.time)
        grasped = any('thumb' in fs and bool(fs & {'index', 'middle'})
                      and closure[side] > .1 for side, fs in fingers.items())
        return {
            'time': float(backend.data.time),
            'rise_m': float(backend.data.xpos[self.target, 2]) - self.initial_z,
            'grasped': grasped,
            'nonhand_support': bool(contacted - self.hands),
            'robot_contact': bool(contacted & self.robot),
            'container_contact': self.container in contacted,
            'other_support': bool(contacted - self.robot - {self.container}),
            'native_success': bool(backend._native_task_success),
        }

    def update_sample(self, s, reason=None):
        """Pure temporal gate, also used to audit frozen counterexamples."""
        self._last_sample = dict(s)
        if reason:
            self._outcome = 'failure'
            return
        if self._outcome != 'in_progress':
            return
        now = s['time']
        lifted = s['rise_m'] >= .05 and s['grasped'] and not s['nonhand_support']
        if lifted:
            if self._lift_since is None:
                self._lift_since = now
            if now - self._lift_since >= .5:
                self._acquired = True
        else:
            self._lift_since = None
        placed = (s['native_success'] and s['container_contact']
                  and not s['robot_contact'] and not s['other_support'])
        if self._acquired and (s['other_support'] or
                              (s['nonhand_support'] and not s['container_contact'])):
            self._acquired = False
        if self._acquired and not s['grasped'] and not placed:
            if self._gap_since is None:
                self._gap_since = now
            if s['other_support'] or now - self._gap_since > .3:
                self._acquired = False
        else:
            self._gap_since = None
        if self._acquired and placed:
            if self._release_since is None:
                self._release_since = now
            if now - self._release_since >= 1.:
                self._outcome = 'success'
        else:
            self._release_since = None

    def update(self, backend):
        self.update_sample(self.sample(backend), backend.reason)

    def outcome(self, backend):
        return self._outcome

    def host_audit_state(self):
        return {'contract': PLACEMENT_CONTRACT['id'], 'sample': self._last_sample,
                'acquired': self._acquired, 'lift_since': self._lift_since,
                'release_since': self._release_since, 'gap_since': self._gap_since,
                'outcome': self._outcome}
