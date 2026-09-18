"""Host-only Handover learning completion; original native task is untouched."""
import numpy as np
from rsi.simple_placement import SimplePlacementEvaluator

HANDOVER_ENV = 'simple/G1WholebodyHandoverTeleop-v0'
HANDOVER_CONTRACT = {
    'id': 'handover-right-left-released-support-v1', 'scope': HANDOVER_ENV,
    'native_reward_unchanged': True, 'native_trigger_alone_terminates': False,
    'unmodified_native_benchmark': False,
    'right_only_hold_s': .5, 'left_only_hold_s': .5,
    'full_object_clearance_m': .001, 'released_support_s': 1.,
    'unsupported_release_grace_s': .3, 'settled_translation_m': .01,
    'settled_rotation_rad': float(np.deg2rad(5)),
    'final_geometry_audit_required': True,
}

HANDOVER_SIM_ENV = 'simple/G1WholebodyHandoverSimToRealTeleop-v0'
HANDOVER_BACK_ENV = 'simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0'
BEND_HANDOVER_ENV = 'simple/G1WholebodyBendHandoverTeleop-v0'
HANDOVER_ENVS = (HANDOVER_ENV, HANDOVER_SIM_ENV, HANDOVER_BACK_ENV, BEND_HANDOVER_ENV)


def handover_contract(env_id):
    if env_id == HANDOVER_ENV:
        return dict(HANDOVER_CONTRACT)
    if env_id == BEND_HANDOVER_ENV:
        return dict(HANDOVER_CONTRACT, scope=env_id,
            id='bend-handover-right-left-released-support-v1',
            destination='native_container', native_container_present=True)
    if env_id not in HANDOVER_ENVS:
        raise ValueError('Unreviewed Handover variant')
    return dict(HANDOVER_CONTRACT, scope=env_id,
        id=('handover-right-left-independent-support-v1' if env_id == HANDOVER_SIM_ENV
            else 'handover-right-left-released-table-v1'),
        destination=('left_hand_after_right_release' if env_id == HANDOVER_SIM_ENV else 'original_table_top'),
        native_container_present=False)


class SimpleHandoverEvaluator(SimplePlacementEvaluator):
    """A physical milestone never authorizes exposing privileged progress to actor.

    Uses the existing contact sampler/host recording boundary. The actor receives
    only configured completion outcome; all samples/phase flags remain host-only.
    """
    task_uid = 'g1_wholebody_handover_teleop'
    completion_contract = HANDOVER_CONTRACT

    def __init__(self, env_id=HANDOVER_ENV):
        self.completion_contract = handover_contract(env_id)
        self.env_id = env_id
        self.task_uid = {HANDOVER_ENV:'g1_wholebody_handover_teleop',
            HANDOVER_SIM_ENV:'g1_wholebody_handover_sim_to_real_teleop',
            HANDOVER_BACK_ENV:'g1_wholebody_handover_place_back_sim_to_real_teleop',
            BEND_HANDOVER_ENV:'g1_wholebody_bend_handover_teleop'}[env_id]

    def reset(self, backend):
        import mujoco
        # Reuse the existing host-only sampler, with a separate exact-task reset.
        # Do not alter the running box-placement evaluator's task scope.
        task,model=backend.env.task,backend.model
        if task.uid != self.task_uid:
            raise ValueError('Handover gate requires its exact native task')
        self.target=int(model.body(str(task.target.asset.label)).id)
        if self.env_id in (HANDOVER_ENV, BEND_HANDOVER_ENV):
            self.container=int(model.body(str(task.container.asset.label)).id)
        elif self.env_id == HANDOVER_BACK_ENV:
            table=task.layout.actors.get('table')
            if table is None:raise ValueError('PlaceBack requires its native table')
            self.container=int(model.body('table').id)
            self._table_top_z=float(table.pose.position[2]+.5*table.size[2])
        else:
            self.container=-1  # This exact native task has no container.

        self.robot={int(model.body('pelvis').id)}
        self.hands={int(model.body(f'{side}_wrist_yaw_link').id) for side in ('left','right')}
        for body in range(1,model.nbody):
            for group in (self.robot,self.hands):
                if int(model.body_parentid[body]) in group:group.add(body)
        self.initial_z=float(backend.data.xpos[self.target,2])
        self._outcome='in_progress';self._last_sample=None
        backend.placement_evaluator=self
        self._parts = []
        for g in range(backend.model.ngeom):
            m = backend.model
            if int(m.geom_bodyid[g]) != self.target or not (m.geom_contype[g] or m.geom_conaffinity[g]):
                continue
            if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
                raise ValueError('Handover requires reviewed native target collision meshes')
            mesh = int(m.geom_dataid[g]); start = int(m.mesh_vertadr[mesh]); n = int(m.mesh_vertnum[mesh])
            self._parts.append((g, m.mesh_vert[start:start+n].copy()))
        if not self._parts:
            raise ValueError('Missing native target collision geometry')
        self._initial_bottom = self._bottom(backend)
        self._right = self._left = False
        self._right_since = self._left_since = self._release_since = self._gap_since = None
        self._settle_position = self._settle_quaternion = None
        self._native_seen = False; self._native_first_sim_s = None
        self._last_time = None; self._host_error = None
        self._backend_identity = id(backend)
        self._reset_id = backend.scene_setup['reset_provenance']['reset_id']
        # Parent registers self as placement_evaluator for existing host-only trace.

    def _bottom(self, backend):
        vertices = np.concatenate([v @ backend.data.geom_xmat[g].reshape(3,3).T
                                   + backend.data.geom_xpos[g] for g,v in self._parts])
        return float(vertices[:,2].min())

    def sample(self, backend):
        import mujoco
        s = super().sample(backend)
        fingers={'left':set(),'right':set()};touch=set();table_top_contact=False
        for i in range(backend.data.ncon):
            c=backend.data.contact[i]
            a,b=(int(backend.model.geom_bodyid[g]) for g in (c.geom1,c.geom2))
            if self.target not in (a,b):continue
            name=backend.model.body(b if a==self.target else a).name or ''
            force=np.zeros(6);mujoco.mj_contactForce(backend.model,backend.data,i,force)
            if (self.env_id == HANDOVER_BACK_ENV and self.container in (a,b)
                    and force[0]>.01 and abs(float(c.pos[2])-self._table_top_z)<=.02):
                table_top_contact=True
            for side in fingers:
                if name.startswith(side+'_hand_') or name==side+'_wrist_yaw_link':touch.add(side)
                if force[0]>.01:
                    for finger in ('thumb','index','middle'):
                        if name.startswith(f'{side}_hand_{finger}_'):fingers[side].add(finger)
        if self.env_id == HANDOVER_BACK_ENV:s['container_contact']=table_top_contact
        closure=backend.gripper_command_at(backend.data.time)
        s['grasped_sides']=[side for side,fs in fingers.items() if 'thumb' in fs and bool(fs&{'index','middle'}) and closure[side]>.1]
        s['touching_hands']=sorted(touch)
        s.update(bottom_clearance_m=self._bottom(backend)-self._initial_bottom,
                 target_position_m=backend.data.xpos[self.target].tolist(),
                 target_quaternion_wxyz=backend.data.xquat[self.target].tolist())
        return s

    def update(self, backend):
        if id(backend) != self._backend_identity or backend.scene_setup['reset_provenance']['reset_id'] != self._reset_id:
            self._host_error='backend_or_reset_changed'; self._outcome='failure'; return
        self.update_sample(self.sample(backend), backend.reason)

    def update_sample(self, s, reason=None):
        self._last_sample = dict(s)
        if reason:
            self._outcome='failure'; return
        now = float(s['time']); pos=np.asarray(s['target_position_m'],dtype=float)
        quat=np.asarray(s['target_quaternion_wxyz'],dtype=float)
        if (pos.shape != (3,) or quat.shape != (4,) or not np.isfinite([now,s['bottom_clearance_m'],*pos,*quat]).all()
                or abs(np.linalg.norm(quat)-1) > .01 or (self._last_time is not None and now < self._last_time)):
            self._host_error='invalid_or_regressed_host_sample'; self._outcome='failure'; return
        self._last_time=now
        if s['native_success']:
            if not self._native_seen: self._native_first_sim_s=now
            self._native_seen=True
        if self._outcome != 'in_progress': return
        grasp=set(s['grasped_sides']); touch=set(s['touching_hands'])
        clear=s['bottom_clearance_m'] > HANDOVER_CONTRACT['full_object_clearance_m'] and not s['nonhand_support']
        right_only=clear and grasp=={'right'} and 'left' not in touch
        left_only=clear and grasp=={'left'} and 'right' not in touch
        if right_only:
            if self._right_since is None: self._right_since=now
            if now-self._right_since >= HANDOVER_CONTRACT['right_only_hold_s']: self._right=True
            self._left=False
        else: self._right_since=None
        if self._right and left_only:
            if self._left_since is None: self._left_since=now
            if now-self._left_since >= HANDOVER_CONTRACT['left_only_hold_s']: self._left=True
        else: self._left_since=None
        if self.env_id == HANDOVER_SIM_ENV and self._left and left_only and self._native_seen:
            self._outcome='success'
            return
        placed=(self._native_seen and s['container_contact'] and not s['robot_contact']
                and not s['other_support'] and not touch and not grasp)
        if s['other_support']:
            self._right=self._left=False
        if not grasp and not placed:
            if self._gap_since is None: self._gap_since=now
            if now-self._gap_since > HANDOVER_CONTRACT['unsupported_release_grace_s']:
                self._right=self._left=False
        else: self._gap_since=None
        if self._left and placed:
            if self._release_since is not None:
                translation=float(np.linalg.norm(pos-self._settle_position))
                rotation=2*np.arccos(np.clip(abs(float(quat @ self._settle_quaternion)),0,1))
                if translation>HANDOVER_CONTRACT['settled_translation_m'] or rotation>HANDOVER_CONTRACT['settled_rotation_rad']:
                    self._release_since=None
            if self._release_since is None:
                self._release_since=now; self._settle_position=pos.copy(); self._settle_quaternion=quat.copy()
            if now-self._release_since >= HANDOVER_CONTRACT['released_support_s']:
                self._outcome='success'
        else: self._release_since=None

    def host_audit_state(self):
        return dict(contract=self.completion_contract['id'],sample=self._last_sample,
                    native_milestone_seen=self._native_seen,native_first_sim_s=self._native_first_sim_s,
                    right_only_retained=self._right,left_only_retained=self._left,
                    right_since=self._right_since,left_since=self._left_since,
                    release_since=self._release_since,gap_since=self._gap_since,
                    outcome=self._outcome,error=self._host_error,reset_id=self._reset_id)
