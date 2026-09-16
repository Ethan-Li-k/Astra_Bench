"""Host engineering probe: a visible mocap sphere pushes the leaf via real contact."""
import json
import xml.etree.ElementTree as E
import numpy as np
import mujoco
from PIL import Image
from door_backend import ROOT,SCENE,create_backend
from rsi.episode_video import EpisodeVideo

def main():
    out=ROOT/'diagnostics/door-v3-contact-001';out.mkdir(parents=True,exist_ok=False)
    tree=E.parse(SCENE)
    body=E.SubElement(tree.getroot().find('worldbody'),'body',name='diagnostic_probe',mocap='true',pos='-2.875 2.12 1.2')
    E.SubElement(body,'geom',name='diagnostic_probe_geom',type='sphere',size='.04',rgba='0.1 0.5 1 1',
        contype='4',conaffinity='2')
    path=out/'diagnostic-scene.xml';tree.write(path,encoding='unicode')
    b=create_backend(settle_ticks=0,scene=path);m=b.model;d=b.data
    probe=int(m.body('diagnostic_probe').mocapid);q=int(m.joint('ikea_door_hinge').qposadr[0])
    leaf=m.body('ikea_door_west').id
    video=EpisodeVideo(b,out/'video',label='Engineering contact probe | source-aligned IKEA no latch')
    rows=[]
    try:
        for tick in range(550):
            t=tick*.02
            if t<3:x=-2.875
            elif t<7:x=-2.875-.8*(t-3)/4
            elif t<9:x=-3.675
            else:x=-3.675+.8*(t-9)/2
            d.mocap_pos[probe]=[x,2.12,1.2]
            b.tick();video.record_tick('diagnostic_not_scored')
            probe_contacts=0;leaf_static=[]
            for i in range(d.ncon):
                c=d.contact[i];names=[m.geom(g).name for g in (c.geom1,c.geom2)]
                if 'diagnostic_probe_geom' in names and leaf in [int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)]:probe_contacts+=1
                if leaf in [int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)] and 'diagnostic_probe_geom' not in names:
                    leaf_static.append(dict(names=names,depth=float(c.dist)))
            rows.append(dict(t=float(d.time),angle_rad=float(d.qpos[q]),probe_x=x,probe_contacts=probe_contacts,
                leaf_other_contacts=leaf_static,base_z=float(d.qpos[2]),reason=b.reason))
            if b.reason:break
        for camera in ('head_cam','track'):
            video.renderer.update_scene(d,camera=camera);Image.fromarray(video.renderer.render()).save(out/(camera+'.png'))
    finally:video.close()
    opened=-min(row['angle_rad'] for row in rows)
    report=dict(backend='MuJoCo',scene_variant='usd-aligned-door-west-no-latch-v3',mode='engineering_mocap_contact_probe',
        actor_calls=0,task_success_credit=0,sim_s=float(d.time),model_38000_controls=len(rows),
        no_latch=True,source_joint='none authored in composed Flatten; derived hinge assumption',
        initial_closed_drift_rad=max(abs(r['angle_rad']) for r in rows if r['t']<=3),
        max_open_deg=float(np.rad2deg(opened)),probe_contact_ticks=sum(r['probe_contacts']>0 for r in rows),
        safety_stop=b.reason,minimum_base_z=min(r['base_z'] for r in rows),
        passed=opened>np.pi/6 and any(r['probe_contacts'] for r in rows) and b.reason is None,
        diagnostic_diff='Added visible kinematic sphere, no actor or robot task credit. Uses identical scene collisions.')
    (out/'physics.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    manifest=json.loads((ROOT/'video-manifest.json').read_text());manifest['videos'].append(dict(path=str(out/'video/episode.mp4'),
        complete=True,kind='diagnostic',task='brown_bedroom_door',episode=out.name,backend='MuJoCo',
        title='真实接触推动与门框净空诊断（球形探针，无策略成绩）',sim_s=float(d.time)))
    (ROOT/'video-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
