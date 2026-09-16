"""IKEA-only G1 model_38000 UMI-4 backend; original assets stay read-only."""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from rsi.live import LiveSim
from rsi.scalebfm import METADATA, MODEL_SHA256

ROOT=Path(__file__).resolve().parent
SCENE=ROOT/'scenes/usd-aligned-door-west-no-latch-v3/scene.xml'

def create_backend(*, settle_ticks=250, scene=SCENE):
    model=mujoco.MjModel.from_xml_path(str(scene))
    # Existing G1 collision geoms are pair-only. Enable named collisions with the new scene.
    robot_collisions=[]
    for i in range(model.ngeom):
        name=model.geom(i).name or ''
        if 'collision' in name and not name.startswith('collision_'):
            model.geom_contype[i]=4;model.geom_conaffinity[i]=3;robot_collisions.append(name)
    data=mujoco.MjData(model)
    metadata=json.loads(METADATA.read_text())
    mapping=[]
    for name,value in zip(metadata['joint_names'],metadata['default_dof_pos']):
        joint=model.joint(name);data.qpos[joint.qposadr[0]]=value
        mapping.append(dict(name=name,qpos=int(joint.qposadr[0]),dof=int(joint.dofadr[0]),actuator=model.actuator(name).id))
    # Independent closed-door reset. Facing west in original FBX world coordinates.
    data.qpos[:7]=[-2.405,2.26,.755,0,0,0,1]
    data.qpos[model.joint('ikea_door_hinge').qposadr[0]]=0.
    data.qvel[:]=0;data.ctrl[:]=0
    mujoco.mj_forward(model,data)
    backend=LiveSim(model=model,data=data,wrist_pi=True,workspace_radius_m=3.)
    backend.continuous_chunks_enabled=True
    backend.scene_setup=dict(backend='MuJoCo',variant='usd-aligned-door-west-no-latch-v3',original_usd=False,
        joint_mapping=mapping,collision_mapping=robot_collisions,model_38000_sha256=MODEL_SHA256,
        scene_sha256=hashlib.sha256(Path(scene).read_bytes()).hexdigest(),
        reset='independent closed hinge at zero; checkpoint standing; robot faces west',
        latch='not modeled; handle rigid on door; not an unlocking task')
    for _ in range(settle_ticks):
        backend.tick()
        if backend.reason:raise RuntimeError('Initial stability failed: '+backend.reason)
    backend.reset_provenance=dict(backend.scene_setup,settle_ticks=settle_ticks,sim_s=float(data.time),
        independent_physical_reset=True,robot_initial_qpos=data.qpos[:7].tolist(),
        door_angle_after_settle=float(data.qpos[model.joint('ikea_door_hinge').qposadr[0]]))
    return backend

class DoorEvaluator:
    """Host-only contact/opening/dwell/stability; never exposes truth to actor."""
    contract='ikea-west-no-latch-contact-open30-hold1-stable-v1'
    def __init__(self,output):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.stream=(self.output/'audit.jsonl').open('x',buffering=1)
    def reset(self,b):
        m=b.model;self.q=int(m.joint('ikea_door_hinge').qposadr[0]);self.initial=float(b.data.qpos[self.q])
        self.door=m.body('ikea_door_west').id
        self.hands={m.body(f'{s}_wrist_yaw_link').id for s in ('left','right')}
        for i in range(m.nbody):
            if m.body_parentid[i] in self.hands:self.hands.add(i)
        self._outcome='in_progress';self.contact_seen=False;self.since=None
        self.max_open=0.;self.max_hold=0.;self.min_base=100.;self.max_tilt=0.;self.contacts=0
    def update(self,b):
        angle=-(float(b.data.qpos[self.q])-self.initial)
        contact=False
        for i in range(b.data.ncon):
            c=b.data.contact[i];bodies={int(b.model.geom_bodyid[g]) for g in (c.geom1,c.geom2)}
            if self.door in bodies and bodies&self.hands:
                f=np.zeros(6);mujoco.mj_contactForce(b.model,b.data,i,f)
                contact|=f[0]>.01
        self.contact_seen|=contact;self.contacts+=int(contact)
        base=float(b.data.qpos[2]);rot=b.data.xmat[b.model.body('pelvis').id].reshape(3,3)
        tilt=float(np.arccos(np.clip(rot[2,2],-1,1)))
        stable=base>.55 and tilt<np.deg2rad(35) and b.reason is None
        if self.contact_seen and angle>=np.pi/6 and stable:
            if self.since is None:self.since=float(b.data.time)
            dwell=float(b.data.time)-self.since;self.max_hold=max(self.max_hold,dwell)
            if dwell>=1.:self._outcome='success'
        else:self.since=None
        if b.reason:self._outcome='failure'
        self.max_open=max(self.max_open,angle);self.min_base=min(self.min_base,base);self.max_tilt=max(self.max_tilt,tilt)
        self.stream.write(json.dumps(dict(sim_s=float(b.data.time),door_open_rad=angle,hand_contact=contact,
            base_z=base,tilt_rad=tilt,stable=stable,outcome=self._outcome))+'\n')
    def outcome(self,b):return self._outcome
    def close(self):
        if self.stream.closed:return
        self.stream.close()
        report=dict(contract=self.contract,outcome=self._outcome,hand_contact_seen=self.contact_seen,
            contact_ticks=self.contacts,max_open_deg=float(np.rad2deg(self.max_open)),max_hold_s=self.max_hold,
            minimum_base_z_m=self.min_base,maximum_tilt_deg=float(np.rad2deg(self.max_tilt)))
        (self.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
