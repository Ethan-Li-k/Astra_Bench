"""Candidate closer robot spawn; original apple/table unchanged; next boundary only."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"runtime-apple-v1"))
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from rsi.live import LiveSim
from rsi.scalebfm import METADATA, MODEL_SHA256

ROOT=Path("/home/galbot/lizekai/RSI/ikea")
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
    # Independent closed-door reset. Robot approach reset faces south toward the original apple/table; source object poses unchanged.
    data.qpos[:7]=[-.79,-1.55,.755,2**-.5,0,0,-2**-.5]
    data.qpos[model.joint('ikea_door_hinge').qposadr[0]]=0.
    data.qvel[:]=0;data.ctrl[:]=0
    mujoco.mj_forward(model,data)
    backend=LiveSim(model=model,data=data,wrist_pi=True,workspace_radius_m=3.)
    backend.continuous_chunks_enabled=True
    backend.scene_setup=dict(backend='MuJoCo',variant='source-aligned-apple-convex-close-robot-v2',original_usd=False,
        source_scene_variant='usd-aligned-door-west-no-latch-v3',
        joint_mapping=mapping,collision_mapping=robot_collisions,model_38000_sha256=MODEL_SHA256,
        scene_sha256=hashlib.sha256(Path(scene).read_bytes()).hexdigest(),
        reset='independent source apple/table; robot at (-.79,-1.55) yaw=-pi/2; door at source closed pose; 0.25m closer than apple-0001, no approach credit',
        latch='not modeled; handle rigid on door; not an unlocking task')
    for _ in range(settle_ticks):
        backend.tick()
        if backend.reason:raise RuntimeError('Initial stability failed: '+backend.reason)
    backend.reset_provenance=dict(backend.scene_setup,settle_ticks=settle_ticks,sim_s=float(data.time),
        independent_physical_reset=True,robot_initial_qpos=data.qpos[:7].tolist(),
        spawn_change_m=[0,-.25,0],spawn_scope='Different robot reset only; not uninterrupted continuation of apple-0001',
        source_apple_initial_center=model.body('ikea_apple').pos.tolist(),
        door_angle_after_settle=float(data.qpos[model.joint('ikea_door_hinge').qposadr[0]]))
    return backend


def apple_geometry(b):
    """Host only: use compiled mesh transform, not a guessed spherical radius."""
    geom = b.model.geom('ikea_apple_geom').id
    mesh = int(b.model.geom_dataid[geom])
    start, count = int(b.model.mesh_vertadr[mesh]), int(b.model.mesh_vertnum[mesh])
    local = b.model.mesh_vert[start:start + count]
    points = local @ b.data.geom_xmat[geom].reshape(3, 3).T + b.data.geom_xpos[geom]
    return dict(center=b.data.xpos[b.model.body('ikea_apple').id].copy(),
                bottom=float(points[:, 2].min()), top=float(points[:, 2].max()))


def apple_contacts(b):
    target = b.model.body('ikea_apple').id
    fingers = {side: set() for side in ('left', 'right')}
    external = []
    rows = []
    for i in range(b.data.ncon):
        contact = b.data.contact[i]
        bodies = [int(b.model.geom_bodyid[g]) for g in (contact.geom1, contact.geom2)]
        if target not in bodies:
            continue
        force = np.zeros(6)
        mujoco.mj_contactForce(b.model, b.data, i, force)
        if float(force[0]) <= .01:
            continue
        other = bodies[1] if bodies[0] == target else bodies[0]
        name = b.model.body(other).name or 'world'
        for side in fingers:
            for finger in ('thumb', 'index', 'middle'):
                if name.startswith(f'{side}_hand_{finger}_'):
                    fingers[side].add(finger)
        root = other
        while b.model.body_parentid[root] != 0:
            root = int(b.model.body_parentid[root])
        if b.model.body(root).name != 'pelvis':
            external.append(name)
        other_geom = int(contact.geom2 if bodies[0] == target else contact.geom1)
        rows.append(dict(other_body=name, other_geom=b.model.geom(other_geom).name,
                         normal_force_n=float(force[0])))
    opposition = any('thumb' in names and bool(names & {'index', 'middle'}) for names in fingers.values())
    return dict(fingers={k: sorted(v) for k, v in fingers.items()},
                loaded_opposition=bool(opposition), external_support=external, contacts=rows)


class AppleEvaluator:
    """Host-only lift and retained opposing-finger support; no object truth to actor."""
    contract = 'ikea-source-apple-lift8cm-opposed-fingers-free-support-hold1-stable-v1'

    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.stream = (self.output / 'audit.jsonl').open('x', buffering=1)

    def reset(self, b):
        g = apple_geometry(b)
        self.initial_center = g['center']
        self.initial_bottom = g['bottom']
        self._outcome = 'in_progress'
        self.since = None
        self.max_hold = self.max_lift = 0.
        self.min_base, self.max_tilt = float('inf'), 0.
        self.contact_ticks = 0
        self.last = None

    def update(self, b):
        g, contacts = apple_geometry(b), apple_contacts(b)
        lift = float(g['center'][2] - self.initial_center[2])
        clearance = float(g['bottom'] - self.initial_bottom)
        base = float(b.data.qpos[2])
        rot = b.data.xmat[b.model.body('pelvis').id].reshape(3, 3)
        tilt = float(np.arccos(np.clip(rot[2, 2], -1, 1)))
        stable = bool(base > .55 and tilt < np.deg2rad(35) and b.reason is None)
        qualified = bool(lift >= .08 and clearance >= .04 and stable and
                         contacts['loaded_opposition'] and not contacts['external_support'])
        t = float(b.data.time)
        if qualified:
            if self.since is None:
                self.since = t
            dwell = t - self.since
            self.max_hold = max(self.max_hold, dwell)
            self._outcome = 'success' if dwell >= 1. else 'in_progress'
        else:
            self.since = None
            dwell = 0.
            self._outcome = 'in_progress'
        if b.reason:
            self._outcome = 'failure'
        self.max_lift = max(self.max_lift, lift)
        self.min_base = min(self.min_base, base)
        self.max_tilt = max(self.max_tilt, tilt)
        self.contact_ticks += int(contacts['loaded_opposition'])
        self.last = dict(sim_s=t, apple_center=g['center'].tolist(), apple_bottom=g['bottom'],
                         lift_m=lift, bottom_rise_m=clearance, base_z=base, tilt_rad=tilt,
                         stable=stable, qualified=qualified, qualified_dwell_s=dwell,
                         outcome=self._outcome, **contacts)
        self.stream.write(json.dumps(self.last) + '\n')

    def outcome(self, b):
        return self._outcome

    def close(self):
        if self.stream.closed:
            return
        self.stream.close()
        report = dict(actor_access=False, contract=self.contract, outcome=self._outcome,
                      initial_center=self.initial_center.tolist(), initial_bottom=self.initial_bottom,
                      max_lift_m=self.max_lift, max_hold_s=self.max_hold,
                      opposed_contact_ticks=self.contact_ticks, min_base_z_m=self.min_base,
                      max_tilt_deg=float(np.rad2deg(self.max_tilt)), last=self.last)
        (self.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
