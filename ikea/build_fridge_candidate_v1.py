"""Independent derived candidate; do not change any in-flight scene."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as E

import mujoco
import numpy as np

from build_scene import numbers

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'scenes/usd-aligned-door-west-no-latch-v3/scene.xml'
REPORT = ROOT / 'engineering-evidence/fridge-source-geometry-v1/report.json'
OUT = ROOT / 'scenes/usd-aligned-fridge-hinged-no-gasket-v1'


def main():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    info = json.loads(REPORT.read_text())
    assert source_hash == info['source_scene_sha256']
    OUT.mkdir(parents=True, exist_ok=False)
    xml = E.parse(SOURCE).getroot()
    xml.set('model', OUT.name)
    world = xml.find('worldbody')
    for index in (124,125):
        world.remove(world.find(f"geom[@name='collision_mesh{index}']"))
    for i, box in enumerate(info['collision_boxes_usd_m']):
        lo, hi = np.array(box['min']), np.array(box['max'])
        E.SubElement(world, 'geom', name=f'fridge_case_partition_{i:02d}',type='box',
            pos=numbers((lo+hi)/2),size=numbers((hi-lo)/2),rgba='0 0 0 0',
            group='3',contype='1',conaffinity='6',friction='.7 .005 .0001')
    moving = []
    for row in info['doors']:
        tag='left' if row['source_mesh']=='mesh126' else 'right'
        hinge=np.array(row['proposed_hinge_usd_m'])
        lo,hi=np.array(row['bounds_usd_m']);size=hi-lo;mass=4.
        body=E.SubElement(world,'body',name=f'ikea_fridge_{tag}',pos=numbers(hinge))
        low,high=((-1.745329252,0) if row['proposed_opening_sign']<0 else (0,1.745329252))
        E.SubElement(body,'joint',name=f'ikea_fridge_{tag}_hinge',type='hinge',axis='0 0 1',
            range=numbers([low,high]),damping='.3',frictionloss='.1',armature='.01')
        inertia=mass/12*np.array([size[1]**2+size[2]**2,size[0]**2+size[2]**2,size[0]**2+size[1]**2])
        E.SubElement(body,'inertial',pos=numbers((lo+hi)/2-hinge),mass=str(mass),diaginertia=numbers(inertia))
        for name in (row['source_mesh'],'collision_'+row['source_mesh']):
            geom=world.find(f"geom[@name='{name}']")
            world.remove(geom)
            geom.set('pos',numbers(np.fromstring(geom.get('pos','0 0 0'),sep=' ')-hinge))
            if name.startswith('collision_'):
                geom.set('contype','2');geom.set('conaffinity','7')
                geom.set('friction','.7 .005 .0001')
            body.append(geom)
        moving.append(dict(**row,body=f'ikea_fridge_{tag}',joint=f'ikea_fridge_{tag}_hinge',
            mass_kg=mass,hinge_range_rad=[low,high],damping=.3,frictionloss=.1,armature=.01))
    scene=OUT/'scene.xml';E.ElementTree(xml).write(scene,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(scene));data=mujoco.MjData(model)
    # Move only the unused robot away for static engineering clearance analysis.
    data.qpos[:3]=[10,10,.755];mujoco.mj_forward(model,data)
    old=mujoco.MjModel.from_xml_path(str(SOURCE));olddata=mujoco.MjData(old)
    mujoco.mj_forward(old,olddata)
    max_visual_delta=0.
    for i in range(141):
        name=f'mesh{i}'
        a=mujoco.mj_name2id(old,mujoco.mjtObj.mjOBJ_GEOM,name)
        b=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,name)
        assert a>=0 and b>=0
        max_visual_delta=max(max_visual_delta,float(abs(olddata.geom_xpos[a]-data.geom_xpos[b]).max()),
                             float(abs(olddata.geom_xmat[a]-data.geom_xmat[b]).max()))
    assert max_visual_delta<1e-7
    sweeps=[]
    for side in ('left','right'):
        jid=model.joint(f'ikea_fridge_{side}_hinge').id
        address=model.jnt_qposadr[jid]
        gid=model.geom('collision_mesh126' if side=='left' else 'collision_mesh127').id
        for deg in (0,15,30,45,60,90,100):
            data.qpos[address]=np.deg2rad(deg)*(-1 if side=='left' else 1)
            mujoco.mj_forward(model,data)
            collisions=[]
            for c in data.contact:
                if gid in (c.geom1,c.geom2) and c.dist<0:
                    other=c.geom2 if c.geom1==gid else c.geom1
                    collisions.append(dict(other=model.geom(other).name,distance=float(c.dist)))
            sweeps.append(dict(door=side,angle_deg=deg,penetrating_contacts=collisions))
        data.qpos[address]=0
    manifest=dict(variant=OUT.name,backend='MuJoCo',original_usd=False,source_read_only=True,
        parent_scene=str(SOURCE),parent_sha256=source_hash,scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),
        source_analysis=str(REPORT),source_analysis_sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),
        all_141_visual_geom_reset_transform_max_delta=max_visual_delta,apple_geometry_and_initial_pose='unchanged',
        doors=moving,gasket='not modeled; no magnetic seal/latch/opening breakaway linkage',
        handle='No handle added: source upper doors are plain slabs; use source edges.',
        case_collision='Twelve disjoint axis-aligned boxes from closed source shell, preserving its three cavities; snap <=1.83 micrometres.',
        drawers='Remain fixed with original visuals and existing convex collisions; no drawer-opening claim.',
        physical_assumptions='New vertical hinges, per-door mass4kg, damping0.3, frictionloss0.1, limits100deg. Not authored source physics.',
        physical_validation='not yet run',policy_attempts=0,success_credit=0,
        static_sweep=sweeps,static_sweep_all_clear=all(not r['penetrating_contacts'] for r in sweeps),
        frozen_current_actor='apple-0001 untouched')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
    print(json.dumps(dict(scene=str(scene),visual_reset_error=max_visual_delta,static_sweep_all_clear=manifest['static_sweep_all_clear'],nq=model.nq,ngeom=model.ngeom)))


if __name__=='__main__':main()
