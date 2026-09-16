"""Isolated ground-to-table setting and host-only physical audit."""
import hashlib
import itertools
import json
import os
import uuid
from datetime import datetime,timezone
from pathlib import Path

import mujoco
import numpy as np

from rsi.live import LiveSim, tabletop_model
from rsi.scalebfm import MODEL, MODEL_SHA256, SCENE, METADATA

ROOT = Path(__file__).resolve().parent
CRITERIA = dict(pelvis_travel_m=.20, support_travel_m=.12,
                foot_step_m=.06, foot_unloaded_s=.10, foot_landed_s=.10,
                ground_grasp_height_m=.05, grasp_hold_s=.50,
                carried_horizontal_m=.15, table_hold_s=2.,
                hand_clearance_m=.04, object_speed_m_s=.03,
                object_angular_speed_rad_s=.20)


def model_digest(m):
    h = hashlib.sha256()
    for name in ('body_pos','body_quat','body_mass','body_inertia','geom_pos',
                 'geom_quat','geom_size','geom_friction','geom_contype','geom_conaffinity',
                 'jnt_type','jnt_range','dof_damping','dof_frictionloss','dof_armature',
                 'eq_data','eq_active0','actuator_gear','actuator_gainprm','actuator_biasprm',
                 'pair_friction','pair_solref','pair_solimp'):
        h.update(np.asarray(getattr(m, name)).tobytes())
    h.update(np.asarray([m.opt.timestep,*m.opt.gravity]).tobytes())
    return h.hexdigest()


class GroundSim(LiveSim):
    """Same UMI-4 + WristPI runtime; seal scene/state at every physics boundary."""
    def __init__(self):
        m = tabletop_model(table_only_offset_x=.55)
        d = mujoco.MjData(m)
        qadr = int(m.joint('diagnostic_cube_free').qposadr[0])
        # Reset-only task layout, before the first physics tick.
        d.qpos[qadr:qadr+3] = [.65, .20, .026]
        d.qpos[2] = .755
        metadata = json.loads(METADATA.read_text())
        # Match LiveSim's float32 default joint targets before storing in qpos64.
        for name, value in zip(metadata['joint_names'], np.asarray(metadata['default_dof_pos'],dtype=np.float32)):
            d.qpos[int(m.joint(name).qposadr[0])] = value
        super().__init__(model=m, data=d, wrist_pi=True, physics_dt=.004,
                         workspace_radius_m=2.)
        self.integrity_failure = None
        self._model_seal = model_digest(m)
        self._seal()
        self._foot_geometry = {}
        for side in ('left','right'):
            link=side+'_ankle_roll_link';bid=m.body(link).id
            origin=self.data.xpos[bid];rotation=self.data.xmat[bid].reshape(3,3)
            points=[];capsules=[]
            for gid in np.flatnonzero(m.geom_bodyid==bid):
                if 'collision' not in (m.geom(int(gid)).name or ''):continue
                if m.geom_type[gid]==mujoco.mjtGeom.mjGEOM_CAPSULE:
                    radius,half_length=m.geom_size[gid,:2]
                    endpoints=np.array([[0.,0.,-half_length],[0.,0.,half_length]])
                    world=endpoints@self.data.geom_xmat[gid].reshape(3,3).T+self.data.geom_xpos[gid]
                    capsules.append({'name':m.geom(int(gid)).name,
                        'endpoints_ankle_m':((world-origin)@rotation).tolist(),
                        'radius_m':float(radius)})
                    # Accurate geom-frame enclosing box, not a radius sphere.
                    extent=np.array([radius,radius,half_length+radius])
                elif m.geom_type[gid]==mujoco.mjtGeom.mjGEOM_BOX:
                    extent=m.geom_size[gid]
                else:
                    extent=np.full(3,m.geom_rbound[gid])
                corners=np.array(list(itertools.product((-1,1),repeat=3)))*extent
                world=corners@self.data.geom_xmat[gid].reshape(3,3).T+self.data.geom_xpos[gid]
                points.extend(((world-origin)@rotation).tolist())
            self._foot_geometry[link]={'collision_bound_vertices_ankle_m':np.unique(np.round(points,9),axis=0).tolist(),
                'collision_capsules_ankle':capsules,
                'meaning':'Robot-only exact capsule endpoints/radii plus enclosing boxes. Capsule FK gives geometric bounds; it is not contact sensing.'}

    def observe(self):
        packet=super().observe()
        packet['foot_geometry']=self._foot_geometry
        return packet

    def _state_digest(self):
        h = hashlib.sha256()
        for a in (self.data.qpos, self.data.qvel, self.data.eq_active):
            h.update(np.asarray(a).tobytes())
        h.update(np.asarray([self.data.time]).tobytes())
        return h.hexdigest()

    def _seal(self):
        self._state_seal = self._state_digest()

    def tick(self):
        if self._state_digest() != self._state_seal:
            self.integrity_failure = 'external_state_write'
        elif model_digest(self.model) != self._model_seal:
            self.integrity_failure = 'model_or_dynamics_changed'
        elif np.any(self.data.xfrc_applied) or np.any(self.data.qfrc_applied):
            self.integrity_failure = 'external_force'
        if self.integrity_failure:
            self.reason = self.integrity_failure
            if self.active:
                self.commands[self.active]['status'] = 'aborted'
                self.active = None
            return
        super().tick()
        self._seal()


def create_backend(*, continuous=False):
    b = GroundSim()
    b.reset_provenance={'reset_uuid':str(uuid.uuid4()),'pid':os.getpid(),
        'utc':datetime.now(timezone.utc).isoformat(),'new_model_and_data_instance':True}
    for _ in range(250):
        b.tick()
    if b.reason:
        raise RuntimeError('Initial physical settling failed: '+b.reason)
    b.continuous_chunks_enabled = continuous
    b.reset_provenance['settled_state_sha256']=hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest()
    return b


class PhaseAudit:
    """State machine accepts physical audit samples; never exported to actor."""
    def __init__(self, initial):
        if initial['cube_bottom'] > .01 or not initial['floor_contact']:
            raise ValueError('Target must start on the floor')
        self.initial = initial
        self.previous = initial
        self.invalid = None
        self.phase = dict(locomotion=False, ground_grasp=False, transport=False,
                          table_release_hold=False)
        self.events = []
        self.air = [0., 0.]
        self.landed = [0., 0.]
        self.stepped = [False, False]
        self.grasp_dwell = self.release_dwell = self.carried = 0.
        self.grasp_anchor = None
        self.metrics = dict(max_pelvis_travel_m=0., max_support_travel_m=0.,
                            max_foot_step_m=[0.,0.],max_foot_clearance_m=[0.,0.],
                            max_cube_bottom_m=initial['cube_bottom'])

    def update(self, s):
        dt = s['t']-self.previous['t']
        if s.get('invalid') or not s['standing'] or not 0 < dt <= .021:
            self.invalid = s.get('invalid') or ('robot_stability_stop' if not s['standing'] else 'audit_time_discontinuity')
            return
        pelvis = float(np.linalg.norm(np.array(s['pelvis'])[:2]-np.array(self.initial['pelvis'])[:2]))
        support = float(np.linalg.norm(np.mean(np.array(s['feet'])[:,:2],axis=0)-np.mean(np.array(self.initial['feet'])[:,:2],axis=0)))
        self.metrics['max_pelvis_travel_m'] = max(self.metrics['max_pelvis_travel_m'], pelvis)
        self.metrics['max_support_travel_m'] = max(self.metrics['max_support_travel_m'], support)
        self.metrics['max_cube_bottom_m'] = max(self.metrics['max_cube_bottom_m'],s['cube_bottom'])
        for i in range(2):
            displacement = float(np.linalg.norm(np.array(s['feet'][i])[:2]-np.array(self.initial['feet'][i])[:2]))
            self.metrics['max_foot_step_m'][i] = max(self.metrics['max_foot_step_m'][i],displacement)
            self.metrics['max_foot_clearance_m'][i] = max(self.metrics['max_foot_clearance_m'][i],s['foot_clearance'][i])
            if not s['foot_contact'][i] and s['foot_clearance'][i] > .005:
                self.air[i] += dt
                self.landed[i] = 0.
            elif s['foot_contact'][i]:
                if self.air[i]+1e-9 >= CRITERIA['foot_unloaded_s'] and displacement >= CRITERIA['foot_step_m']:
                    self.landed[i] += dt
                    if self.landed[i]+1e-9 >= CRITERIA['foot_landed_s']:
                        self.stepped[i] = True
                else:
                    self.air[i] = self.landed[i] = 0.
            else:
                self.air[i] = self.landed[i] = 0.
        self._mark('locomotion', all(self.stepped) and pelvis >= CRITERIA['pelvis_travel_m'] and support >= CRITERIA['support_travel_m'], s)
        grasp = (s['grasped'] and not s['floor_contact'] and not s['table_contact']
                 and not s.get('external_support',False)
                 and s['cube_bottom'] >= CRITERIA['ground_grasp_height_m'])
        self.grasp_dwell = self.grasp_dwell+dt if grasp and self.phase['locomotion'] else 0.
        if self.grasp_dwell >= CRITERIA['grasp_hold_s'] and not self.phase['ground_grasp']:
            self.grasp_anchor = np.array(s['cube'])[:2]
            self._mark('ground_grasp',True,s)
        if self.phase['ground_grasp'] and grasp:
            self.carried = max(self.carried,float(np.linalg.norm(np.array(s['cube'])[:2]-self.grasp_anchor)))
        elif self.phase['ground_grasp'] and not s['table_contact']:
            # A dropped/pushed target cannot bridge disconnected carries.
            self.phase['ground_grasp'] = self.phase['transport'] = False
            self.grasp_anchor = None
            self.carried = 0.
        self._mark('transport',self.carried >= CRITERIA['carried_horizontal_m'],s)
        placed = (self.phase['transport'] and s['table_contact'] and s['inside_table']
                  and not s['floor_contact'] and not s['hand_contact']
                  and s['hand_clearance'] >= CRITERIA['hand_clearance_m']
                  and s['cube_speed'] < CRITERIA['object_speed_m_s']
                  and s['cube_angular_speed'] < CRITERIA['object_angular_speed_rad_s'])
        self.release_dwell = self.release_dwell+dt if placed else 0.
        if not placed:
            self.phase['table_release_hold'] = False
        self._mark('table_release_hold', self.release_dwell >= CRITERIA['table_hold_s'], s)
        self.previous = s

    def _mark(self, key, condition, sample):
        if condition and not self.phase[key]:
            self.phase[key] = True
            self.events.append({'phase':key,'sim_s':sample['t']})

    def result(self):
        return dict(phase_results=self.phase, overall_success=all(self.phase.values()) and not self.invalid,
                    invalid=self.invalid, events=self.events, metrics=self.metrics,
                    carried_horizontal_m=self.carried, release_hold_s=self.release_dwell,
                    completed_foot_steps=self.stepped)


class GroundEvaluator:
    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True,exist_ok=True)
        self.stream = None
        self.audit = None

    def reset(self, b):
        m=b.model
        self.cube = m.body('diagnostic_cube').id
        self.cube_geom = m.geom('diagnostic_cube_geom').id
        self.table = m.geom('diagnostic_table').id
        self.feet = [m.body(n+'_ankle_roll_link').id for n in ('left','right')]
        self.foot_geoms = [[i for i in range(m.ngeom) if int(m.geom_bodyid[i]) == f and 'collision' in (m.geom(i).name or '')] for f in self.feet]
        self.hands = [i for i in range(m.ngeom) if any((m.geom(i).name or '').startswith(s+'_hand_') for s in ('left','right')) and 'collision' in (m.geom(i).name or '')]
        self.floor = {i for i in range(m.ngeom) if m.geom_type[i] == mujoco.mjtGeom.mjGEOM_PLANE}
        if m.neq or int(m.joint('diagnostic_cube_free').type[0]) != mujoco.mjtJoint.mjJNT_FREE:
            raise ValueError('Welded or constrained target is forbidden')
        self.stream=(self.output/'audit.jsonl').open('w',buffering=1)
        first=self.sample(b)
        self.audit=PhaseAudit(first)
        self.stream.write(json.dumps(first)+'\n')
        self.save()

    def sample(self,b):
        m,d=b.model,b.data
        fingers={'left':set(),'right':set()}
        foot_contact=[False,False]
        floor_contact=table_contact=hand_contact=external_support=False
        for i in range(d.ncon):
            c=d.contact[i]; pair={int(c.geom1),int(c.geom2)}
            force=np.zeros(6);mujoco.mj_contactForce(m,d,i,force)
            if force[0] <= .01: continue
            for j,gs in enumerate(self.foot_geoms):
                if pair & set(gs) and pair & self.floor: foot_contact[j]=True
            if self.cube_geom not in pair: continue
            other=next((g for g in pair if g!=self.cube_geom),self.cube_geom)
            floor_contact |= other in self.floor
            table_contact |= other == self.table
            hand_contact |= other in self.hands
            external_support |= other not in self.hands
            name=m.geom(other).name or ''
            for side in fingers:
                for f in ('thumb','index','middle'):
                    if name.startswith(f'{side}_hand_{f}_'): fingers[side].add(f)
        R=d.geom_xmat[self.cube_geom].reshape(3,3)
        corners=np.array(list(itertools.product((-1,1),repeat=3)))*m.geom_size[self.cube_geom]
        corners=corners@R.T+d.geom_xpos[self.cube_geom]
        table_local=(corners-d.geom_xpos[self.table])@d.geom_xmat[self.table].reshape(3,3)
        inside=bool(np.all(np.abs(table_local[:,:2]) <= m.geom_size[self.table,:2]-.003)
                    and abs(np.min(table_local[:,2])-m.geom_size[self.table,2]) < .006)
        clearance=min(float(mujoco.mj_geomDistance(m,d,self.cube_geom,g,10.,None)) for g in self.hands)
        foot_clearance=[]
        for gs in self.foot_geoms:
            foot_clearance.append(min(float(mujoco.mj_geomDistance(m,d,g,f,10.,None)) for g in gs for f in self.floor))
        velocity=np.zeros(6);mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,self.cube,velocity,0)
        closure=b.gripper_command_at(d.time)
        return dict(t=float(d.time),cube=d.xpos[self.cube].tolist(),cube_bottom=float(corners[:,2].min()),
                    pelvis=d.qpos[:3].tolist(),feet=d.xpos[self.feet].tolist(),foot_contact=foot_contact,
                    foot_clearance=foot_clearance, floor_contact=bool(floor_contact), table_contact=bool(table_contact),
                    hand_contact=bool(hand_contact),grasped=any(len(v)>=2 and closure[s]>.1 for s,v in fingers.items()),
                    external_support=bool(external_support),
                    finger_contacts={s:sorted(v) for s,v in fingers.items()},inside_table=inside,
                    hand_clearance=clearance,cube_speed=float(np.linalg.norm(velocity[3:])),
                    cube_angular_speed=float(np.linalg.norm(velocity[:3])),
                    standing=b.reason is None,invalid=b.integrity_failure)

    def update(self,b):
        s=self.sample(b)
        self.audit.update(s)
        self.stream.write(json.dumps(s)+'\n')
        self.save()

    def save(self):
        if self.audit:
            (self.output/'evaluation.json').write_text(json.dumps(self.audit.result(),indent=2))

    def outcome(self,b):
        if self.audit.invalid: return 'failure'
        return 'success' if self.audit.result()['overall_success'] else 'in_progress'

    def close(self):
        if self.stream: self.stream.close()


def setting_manifest(b):
    m=b.model
    return dict(backend='MuJoCo', contract_version='ground-task-v1/UMI-4-fixed-WristPI',
        source_thread='codex://threads/01a0a090-ddb2-73a3-9dd9-ce1a85f36f34',
        source_thread_access='User-supplied complete available-turn transcript SOURCE_THREAD.md; direct thread connector unavailable',
        setting='free-standing G1 + two DEX3, original model_38000, real contact',
        layout_changes_from_tabletop_seed={
            'cube_reset_position_m':{'old':[.33,-.22,.656],'new':[.65,.20,.026]},
            'table_and_four_legs_translation_m':[.55,0,0],
            'robot_reset_changed':False},
        task_adapter_changes={'workspace_radius_m':{'old':.25,'new':2.,'purpose':'Permit locomotion and ground reach; no dynamics change'},
                              'per_step_m':.03,'per_step_rad':.10,'unchanged_stability_stop':'pelvis z<.55 m or tilt>25 deg'},
        cube_mass_kg=float(m.body_mass[m.body('diagnostic_cube').id]),
        cube_friction=m.geom('diagnostic_cube_geom').friction.tolist(),
        table_top_m=.630,tracker_hz=50,pd_hz=250,physics_dt=.004,
        wrist_pi='Existing locomanip WristPI, active components only; gains unmodified',
        model_path=str(MODEL),model_sha256=MODEL_SHA256,scene_path=str(SCENE),
        scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        compiled_dynamics_sha256=model_digest(m),criteria=CRITERIA,
        physical_episode_budget_s=180,action_timeout='duration + 2 s',
        model_reasoning_timeout=None,simulation_pauses_during_planning=True,
        actor_inputs=['head/right-wrist RGB','camera calibration','named robot proprioception','public three-state outcome'],
        forbidden_actor_inputs=['object pose','contact truth','hidden reward','host audit','development generated action'],
        learning_and_frozen_evaluation_separate=True)
