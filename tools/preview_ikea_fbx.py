"""Static engineering preview from a read-only FBX dump; never a task rollout."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from PIL import Image


def numbers(values):
    return ' '.join(format(float(x), '.9g') for x in np.asarray(values).ravel())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    source=Path('artifacts/R023/ikea-door/fbx-scene.assxml')
    scene=ET.parse(source).getroot().find('Scene')
    meshes=list(scene.find('MeshList'));materials=list(scene.find('MaterialList'))
    xml=ET.Element('mujoco',model='IKEA FBX static geometry preview')
    ET.SubElement(xml,'compiler',angle='radian',inertiafromgeom='false')
    visual=ET.SubElement(xml,'visual');ET.SubElement(visual,'global',offwidth='1224',offheight='720',fovy='65')
    ET.SubElement(visual,'headlight',ambient='.5 .5 .5',diffuse='.6 .6 .6')
    asset=ET.SubElement(xml,'asset');world=ET.SubElement(xml,'worldbody')
    ET.SubElement(world,'light',pos='3 -3 5',dir='0 0 -1',diffuse='.8 .8 .8',ambient='.4 .4 .4')
    ET.SubElement(world,'light',pos='4 -1 2.5',dir='-1 0 -.3',diffuse='.6 .6 .6')
    source_dir=Path('/home/galbot/Downloads/APA/IKEA_LivingRoom_Mesh_0915')
    texture_paths=[]
    for i,mat in enumerate(materials):
        props=list(mat.find('MatPropertyList'))
        color=next((np.fromstring(x.text,sep=' ') for x in props if x.get('key')=='$clr.diffuse'),np.array([.7,.7,.7]))
        rgba=numbers([*color[:3],1.])
        m=ET.SubElement(asset,'material',name=f'mat{i}',rgba=rgba,specular='.1',shininess='.1')
        tex=next((x.text.strip().strip('"') for x in props if x.get('key')=='$tex.file' and x.get('tex_usage')=='Diffuse'),None)
        if tex:
            path=source_dir/tex.replace('\\','/')
            if path.is_file():
                # MuJoCo accepts PNG here; preserve decoded pixels in an RSI copy.
                converted=(a.output/'textures'/f'tex{i}.png').resolve()
                converted.parent.mkdir(exist_ok=True)
                with Image.open(path) as image:
                    image=image.convert('RGB');image.save(converted)
                    with Image.open(converted) as check:
                        assert np.array_equal(np.asarray(image),np.asarray(check))
                ET.SubElement(asset,'texture',name=f'tex{i}',type='2d',file=str(converted))
                m.set('texture',f'tex{i}');m.set('rgba','1 1 1 1')
                texture_paths.append({'source':str(path),'copy':str(converted),
                                      'decoded_rgb_identical':True})
    rows=[];axis=np.array([[1,0,0],[0,0,-1],[0,1,0.]])
    def visit(node,parent,path):
        transform=parent@np.fromstring(node.findtext('Matrix4'),sep=' ').reshape(4,4)
        name=node.get('name');path=path+'/'+name
        for index in [int(x) for x in (node.findtext('MeshRefs') or '').split()]:
            mesh=meshes[index];points=np.fromstring(mesh.findtext('Positions'),sep=' ').reshape(-1,3)
            points=((points@transform[:3,:3].T+transform[:3,3])@axis.T)*.01
            faces=[]
            for f in mesh.find('FaceList'):
                poly=[int(x) for x in f.text.split()]
                faces.extend((poly[0],poly[j],poly[j+1]) for j in range(1,len(poly)-1))
            meshname=f'mesh{len(rows)}'
            # Preserve planar visual faces while allowing convex-hull creation:
            # unused duplicate vertices are separated by 1 micrometre.
            centered=points-points.mean(0);_,sv,vh=np.linalg.svd(centered,full_matrices=False)
            planar=sv[-1]<1e-9
            uv=mesh.find('TextureCoords')
            attributes={'name':meshname,'vertex':numbers(points),'face':' '.join(str(x) for f in faces for x in f),
                        'inertia':'shell'}
            if planar:
                expanded=np.vstack([points,points+vh[-1]*1e-6])
                attributes['vertex']=numbers(expanded)
            if uv is not None and int(uv.get('num_components'))==2:
                coords=np.fromstring(uv.text,sep=' ').reshape(-1,2)
                coords[:,1]=1.-coords[:,1]
                if len(coords)==len(points):attributes['texcoord']=numbers(np.vstack([coords,coords]) if planar else coords)
            ET.SubElement(asset,'mesh',**attributes)
            ET.SubElement(world,'geom',name=meshname,type='mesh',mesh=meshname,
                material=f"mat{mesh.get('material_index')}",contype='0',conaffinity='0',group='0')
            rows.append({'name':name,'path':path,'source_mesh_index':index,'preview_mesh':meshname,
                         'planar_hull_duplicate_vertices_1um':bool(planar)})
        children=node.find('NodeList')
        if children is not None:
            for child in children:visit(child,transform,path)
    visit(scene.find('Node'),np.eye(4),'')
    path=a.output/'scene.xml';ET.ElementTree(xml).write(path,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(path.resolve()));data=mujoco.MjData(model);mujoco.mj_forward(model,data)
    renderer=mujoco.Renderer(model,width=1224,height=720)
    try:
        camera=mujoco.MjvCamera();mujoco.mjv_defaultFreeCamera(model,camera)
        camera.lookat[:]=[.15,-3.,1.05];camera.distance=3.7;camera.azimuth=180;camera.elevation=-12
        renderer.update_scene(data,camera=camera)
        Image.fromarray(renderer.render()).save(a.output/'west-wall.png')
    finally:renderer.close()
    report={'mode':'static geometry rendering, no physics steps or robot or actor',
        'source_assxml_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'axis_mapping':'FBX Y-up to Z-up: (x,y,z)->(x,-z,y)',
        'scale':'0.01 metres per FBX unit; UnitScaleFactor=1.0 means centimetres',
        'texture_coordinate_mapping':'v -> 1-v for FBX/MuJoCo texture origin conversion',
        'textures_read_only':texture_paths,'mesh_mapping':rows,'nmesh':model.nmesh,
        'limitations':['FBX state, not USD stage; no original USD articulation imported.',
            'Diffuse textures only; normals/roughness/lighting not equivalent to reference.',
            'Planar hull helper vertices have1um offset for compilation only; all collisions disabled.'],
        'success_credit':0,'physics_steps':0,'actor_access':False}
    (a.output/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps({'nmesh':model.nmesh,'output':str(a.output),'physics_steps':0}))


if __name__=='__main__':main()
