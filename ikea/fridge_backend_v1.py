"""Next-task candidate backend; never imported by in-flight apple-0001."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime-apple-v1'))
import mujoco
import numpy as np
from rsi.live import LiveSim
from rsi.scalebfm import METADATA,MODEL_SHA256

SCENE=ROOT/'scenes/usd-aligned-fridge-hinged-no-gasket-v1/scene.xml'


def create_backend(*,settle_ticks=250,scene=SCENE):
    model=mujoco.MjModel.from_xml_path(str(scene))
    collisions=[]
    for i in range(model.ngeom):
        name=model.geom(i).name or ''
        if 'collision' in name and not name.startswith('collision_'):
            model.geom_contype[i]=4;model.geom_conaffinity[i]=3;collisions.append(name)
    data=mujoco.MjData(model);meta=json.loads(METADATA.read_text());mapping=[]
    for name,value in zip(meta['joint_names'],meta['default_dof_pos']):
        joint=model.joint(name);data.qpos[joint.qposadr[0]]=value
        mapping.append(dict(name=name,qpos=int(joint.qposadr[0]),dof=int(joint.dofadr[0]),actuator=model.actuator(name).id))
    data.qpos[:7]=[-1.72,-3.035,.755,0,0,0,1]
    for name in ('ikea_door_hinge','ikea_fridge_left_hinge','ikea_fridge_right_hinge'):
        data.qpos[model.joint(name).qposadr[0]]=0.
    data.qvel[:]=0;data.ctrl[:]=0;mujoco.mj_forward(model,data)
    backend=LiveSim(model=model,data=data,wrist_pi=True,workspace_radius_m=3.)
    backend.continuous_chunks_enabled=True
    backend.scene_setup=dict(backend='MuJoCo',variant=SCENE.parent.name,original_usd=False,
        joint_mapping=mapping,collision_mapping=collisions,model_38000_sha256=MODEL_SHA256,
        scene_sha256=hashlib.sha256(Path(scene).read_bytes()).hexdigest(),
        reset='Independent closed source door poses and original apple; robot(-1.72,-3.035,.755) yaw=pi',
        fridge='New mass4kg and vertical hinge per upper door; source plain slabs; no added handle, seal or latch',
        source_geometry='Source case collision partition preserves original interior; original mesh visuals unchanged')
    for _ in range(settle_ticks):
        backend.tick()
        if backend.reason:raise RuntimeError('Fridge reset unstable: '+backend.reason)
    backend.reset_provenance=dict(backend.scene_setup,settle_ticks=settle_ticks,sim_s=float(data.time),
        independent_physical_reset=True,robot_initial_qpos=data.qpos[:7].tolist(),
        fridge_angles_after_settle=[float(data.qpos[model.joint(f'ikea_fridge_{s}_hinge').qposadr[0]]) for s in ('left','right')])
    return backend
