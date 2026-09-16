"""Derive explicit MuJoCo physics, preserving source world-space visual meshes."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'artifacts/R023/ikea-door/preview-05'
ROBOT = Path('/home/galbot/lizekai/Loco_manip/locomanip/assets/unitree_g1_5010/scene_mjx_track_dex3.xml')
VERSION = 'fbx-door-west-no-latch-v1'

def numbers(x):
    return ' '.join(format(float(v), '.10g') for v in np.asarray(x).ravel())

def build():
    out = ROOT / 'scenes' / VERSION
    out.mkdir(parents=True, exist_ok=False)
    original = ET.parse(SOURCE/'scene.xml').getroot()
    xml = ET.Element('mujoco', model=VERSION)
    ET.SubElement(xml, 'include', file=str(ROBOT))
    ET.SubElement(xml, 'compiler', angle='radian', meshdir=str(ROBOT.parent/'assets'))
    ET.SubElement(xml, 'option', timestep='.004', gravity='0 0 -9.81')
    asset = ET.SubElement(xml, 'asset')
    for item in original.find('asset'):
        asset.append(copy.deepcopy(item))
    world = ET.SubElement(xml, 'worldbody')
    ET.SubElement(world, 'light', pos='2 -2 4', dir='0 0 -1', diffuse='.8 .8 .8', ambient='.4 .4 .4')
    hinge = np.array([.00000038, -.13499997, .01])
    moving = ET.SubElement(world, 'body', name='ikea_door_west', pos=numbers(hinge))
    ET.SubElement(moving, 'joint', name='ikea_door_hinge', type='hinge', axis='0 0 1',
                  range='-1.745329252 0', damping='1.0', frictionloss='.15', armature='.01')
    mass = 20.
    size = np.array([.05, 1., 2.1])
    inertia = mass/12*np.array([size[1]**2+size[2]**2, size[0]**2+size[2]**2, size[0]**2+size[1]**2])
    ET.SubElement(moving, 'inertial', pos='.025 -.5 1.05', mass=str(mass), diaginertia=numbers(inertia))
    meshes = {m.get('name'):m for m in asset.findall('mesh')}
    collision_manifest = []
    def box(name, lo, hi):
        lo,hi=np.asarray(lo),np.asarray(hi)
        ET.SubElement(world,'geom',name=name,type='box',pos=numbers((lo+hi)/2),size=numbers((hi-lo)/2),
                      rgba='0 0 0 0',group='3',contype='1',conaffinity='6',friction='.7 .005 .0001')
        collision_manifest.append(dict(name=name,kind='source-axis-aligned-box',lo=lo.tolist(),hi=hi.tolist()))
    for geom in original.find('worldbody').findall('geom'):
        g=copy.deepcopy(geom); name=g.get('name')
        if name in ('mesh38','mesh39','mesh40'):
            # Mesh vertices remain original world positions: offset geom in hinged local frame.
            g.set('pos',numbers(-hinge)); moving.append(g)
            c=copy.deepcopy(g);c.set('name','collision_'+name);c.set('rgba','0 0 0 0');c.set('group','3')
            c.set('contype','2');c.set('conaffinity','5');c.set('friction','.7 .005 .0001');moving.append(c)
            collision_manifest.append(dict(name=c.get('name'),kind='convex-source-mesh',source=name))
        else:
            world.append(g)
            if name in ('mesh0','mesh7','mesh34'):
                continue  # The source planar floor stays visual; existing robot safety ground provides collision.
            if name in ('mesh15','mesh19'):
                x=.055 if name=='mesh19' else 5.755
                box('collision_'+name+'_side1',[x,-1.14,0],[x+.05,-1.13,2.11])
                box('collision_'+name+'_side2',[x,-.14,0],[x+.05,-.13,2.11])
                box('collision_'+name+'_header',[x,-1.14,2.11],[x+.05,-.13,2.12])
                continue
            c=copy.deepcopy(g);c.set('name','collision_'+name);c.set('rgba','0 0 0 0');c.set('group','3')
            c.set('contype','1');c.set('conaffinity','6');world.append(c)
            collision_manifest.append(dict(name=c.get('name'),kind='convex-source-mesh',source=name))
    scene=out/'scene.xml';ET.ElementTree(xml).write(scene,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(scene))
    manifest=dict(variant=VERSION,backend='MuJoCo',original_usd=False,source_read_only=True,
        geometry_source=str(SOURCE/'scene.xml'),source_sha256=hashlib.sha256((SOURCE/'scene.xml').read_bytes()).hexdigest(),
        scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),axis_mapping='(x,-z,y)*0.01',
        original_physics='unknown; original USD22.11 parser rejected Unicode prim paths',
        hinge_hypothesis=hinge.tolist(),hinge_axis=[0,0,1],hinge_range_rad=[-1.745329252,0],
        latch_mode='no latch; handle rigidly attached to leaf; opening is not unlocking',
        leaf_mass_kg=mass,gravity=[0,0,-9.81],damping=1.,frictionloss=.15,
        geometry_changes=['Visual meshes and world coordinates preserved from FBX conversion.',
            'Door and handle grouped on a new hinge; handle has no independent joint.',
            'Frame lip meshes15/19 decomposed into three boxes preserving rectangular aperture.',
            'Static object collisions and moving meshes use convex source hulls.',
            'Infinite robot collision floor replaces planar FBX floor collision; original floor visual remains.'],
        collision_manifest=collision_manifest,nq=model.nq,nv=model.nv,ngeom=model.ngeom,
        validation_status='compiled_only_not_physics_validated',success_credit=0)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'scene':str(scene),'ngeom':model.ngeom,'nq':model.nq}))

if __name__=='__main__':build()
