"""Align FBX-derived visuals to successfully read source USD; add source apple."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'compat-usd'))
from pxr import Usd,UsdGeom,Gf
import mujoco
from build_scene import numbers

def main():
    old=ROOT/'scenes/fbx-door-west-no-latch-v1';out=ROOT/'scenes/usd-aligned-door-west-no-latch-v3'
    out.mkdir(parents=True,exist_ok=False)
    tree=E.parse(old/'scene.xml');xml=tree.getroot();xml.set('model',out.name)
    shift=np.array([-3.105,3.02,0.])
    for item in xml.find('worldbody'):
        p=np.fromstring(item.get('pos','0 0 0'),sep=' ')
        item.set('pos',numbers(p+shift))
    source=Path('/home/galbot/Downloads/APA/IKEA_LivingRoom_Mesh_0915')
    stage=Usd.Stage.Open(str(source/'IKEA_LivingRoom_Mesh_0915_Props_Flatten.usd'))
    path='/World/Origin/SceneOffset/apple/pingguo_straightened/pingguo_straightened'
    mesh=UsdGeom.Mesh(stage.GetPrimAtPath(path))
    transform=mesh.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    points=np.array([list(transform.Transform(Gf.Vec3d(*p))) for p in mesh.GetPointsAttr().Get()])
    counts=list(mesh.GetFaceVertexCountsAttr().Get());indices=list(mesh.GetFaceVertexIndicesAttr().Get())
    faces=[];faceuv=[];offset=0
    for n in counts:
        for j in range(1,n-1):faces.extend([indices[offset],indices[offset+j],indices[offset+j+1]]);faceuv.extend([offset,offset+j,offset+j+1])
        offset+=n
    center=(points.min(0)+points.max(0))/2
    props=dict(name='usd_apple_mesh',vertex=numbers(points-center),face=' '.join(map(str,faces)))
    primvar=UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st')
    if primvar and primvar.HasValue():
        uv=np.array(primvar.ComputeFlattened())
        props['texcoord']=numbers(uv)
        if str(primvar.GetInterpolation())=='faceVarying':
            props['vertex']=numbers((points-center)[np.asarray(faces)])
            props['face']=' '.join(map(str,range(len(faces))))
            props['texcoord']=numbers(uv[np.asarray(faceuv)])
    asset=xml.find('asset');E.SubElement(asset,'mesh',**props)
    png=out/'apple-color.png'
    with Image.open(source/'Props/apple/textures/pingguo_Color.jpg') as im:im.convert('RGB').save(png)
    E.SubElement(asset,'texture',name='usd_apple_texture',type='2d',file=str(png))
    E.SubElement(asset,'material',name='usd_apple_material',texture='usd_apple_texture',rgba='1 1 1 1')
    body=E.SubElement(xml.find('worldbody'),'body',name='ikea_apple',pos=numbers(center))
    E.SubElement(body,'freejoint',name='ikea_apple_free')
    E.SubElement(body,'geom',name='ikea_apple_geom',type='mesh',mesh='usd_apple_mesh',material='usd_apple_material',
        mass='.18',contype='2',conaffinity='7',friction='.7 .005 .0001')
    scene=out/'scene.xml';tree.write(scene,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(scene))
    m=json.loads((old/'manifest.json').read_text());m.update(variant=out.name,
        scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),parent_scene=str(old/'scene.xml'),
        usd_audit=str(ROOT/'source-usd-audit/report.json'),original_usd=False,
        original_physics='Flatten USD26.8 fully opened, zero UsdPhysics joints; target door has no rigid/collision schema.',
        fbx_world_to_usd_translation_m=shift.tolist(),hinge_hypothesis=(np.array(m['hinge_hypothesis'])+shift).tolist(),
        apple=dict(source=str(source/'IKEA_LivingRoom_Mesh_0915_Props_Flatten.usd'),prim=path,
            original_bounds=[points.min(0).tolist(),points.max(0).tolist()],
            source_dynamic=True,source_collision='sdf',derived_collision='convex original mesh',
            mass_kg=.18,mass_source='engineering assumption; no authored USD mass value'),
        source_initial_pose='Door closed source mesh; exact source apple world geometry and position',
        validation_status='compiled; contact sweep pending',nq=model.nq,nv=model.nv,ngeom=model.ngeom)
    m['geometry_changes']+=['Global FBX translation aligned to source USD (-3.105,3.02,0) m.',
        'Source apple vertex/face/UV geometry added at authored world pose; mass .18kg and convex collision explicitly differ from unspecified mass/SDF.']
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps(dict(scene=str(scene),nq=model.nq,apple_vertices=len(points))))

if __name__=='__main__':main()
