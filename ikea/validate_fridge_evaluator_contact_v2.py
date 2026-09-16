"""Actual contact/closed reset diagnostic, not an actor task attempt."""
import hashlib
import json
import xml.etree.ElementTree as E
import numpy as np
import mujoco
from PIL import Image
from fridge_backend_v1 import ROOT,SCENE,create_backend
from rsi.episode_video import EpisodeVideo
from fridge_evaluator_v2 import FridgeEvaluator
from review_fridge_physics_v2 import physical_audit


def main():
    out=ROOT/'diagnostics/fridge-evaluator-contact-001';out.mkdir(parents=True,exist_ok=False)
    tree=E.parse(SCENE)
    body=E.SubElement(tree.getroot().find('worldbody'),'body',name='fridge_probe',mocap='true',pos='-2.48 -3.12 1.08')
    E.SubElement(body,'geom',name='fridge_probe_geom',type='sphere',size='.018',rgba='.2 .5 1 1',contype='4',conaffinity='2')
    path=out/'diagnostic-scene.xml';tree.write(path,encoding='unicode')
    b=create_backend(settle_ticks=0,scene=path);m,d=b.model,b.data
    probe=int(m.body('fridge_probe').mocapid)
    addresses=[int(m.joint(f'ikea_fridge_{s}_hinge').qposadr[0]) for s in ('left','right')]
    leaf=m.body('ikea_fridge_left').id;probe_geom=m.geom('fridge_probe_geom').id
    camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:]=[-2.3,-3.15,1.05];camera.distance=2.4;camera.azimuth=20;camera.elevation=-15
    video=EpisodeVideo(b,out/'video',label='Fridge engineering sphere contact | NOT policy success',video_cameras=(camera,'head_cam'))
    evaluator=FridgeEvaluator(out/'native-evaluator');evaluator.reset(b)
    initial_time=float(d.time)
    rows=[]
    try:
        for tick in range(500):
            t=tick*.02
            if t<3:
                p=np.array([-2.48,-3.12,1.08])
            elif t<4:
                p=np.array([-2.48+.045*(t-3),-3.12,1.08])
            elif t<8:
                theta=np.deg2rad(65)*(t-4)/4
                local=np.array([-.025,.33]);c,s=np.cos(theta),np.sin(theta)
                p=np.array([-2.41+c*local[0]+s*local[1],-3.45-s*local[0]+c*local[1],1.08])
            else:
                p=np.array([-2.8,-3.12,1.08])
            d.mocap_pos[probe]=p;b.tick();evaluator.update(b);video.record_tick('diagnostic_not_scored')
            forces=[];others=[]
            for i in range(d.ncon):
                contact=d.contact[i];geoms=(contact.geom1,contact.geom2)
                if leaf not in (int(m.geom_bodyid[g]) for g in geoms):continue
                if probe_geom in geoms:
                    force=np.zeros(6);mujoco.mj_contactForce(m,d,i,force)
                    if force[0]>.01:forces.append(float(force[0]))
                elif contact.dist<0:
                    others.append(dict(geoms=[m.geom(g).name for g in geoms],depth=float(contact.dist)))
            rot=d.xmat[m.body('pelvis').id].reshape(3,3)
            rows.append(dict(t=float(d.time),angles_rad=d.qpos[addresses].tolist(),probe=p.tolist(),
                probe_normal_forces_n=forces,other_leaf_contacts=others,base_z=float(d.qpos[2]),
                tilt_rad=float(np.arccos(np.clip(rot[2,2],-1,1))),reason=b.reason))
            if b.reason:break
        video.renderer.update_scene(d,camera=camera);Image.fromarray(video.renderer.render()).save(out/'final-diagnostic-view.png')
    finally:
        video.close();evaluator.close()
    initial=[r for r in rows if r['t']<=3]
    terminal=[r for r in rows if r['t']>=9]
    report=dict(backend='MuJoCo',variant=SCENE.parent.name,kind='engineering_contact_diagnostic',
        actor_calls=0,physical_policy_attempts=0,task_success_credit=0,sim_s=float(d.time),
        closed_max_drift_rad=max(abs(x) for r in initial for x in r['angles_rad']),
        max_left_open_deg=float(np.rad2deg(-min(r['angles_rad'][0] for r in rows))),
        terminal_min_left_open_deg=float(np.rad2deg(-max(r['angles_rad'][0] for r in terminal))) if terminal else None,
        right_max_drift_rad=max(abs(r['angles_rad'][1]) for r in rows),
        contact_ticks=sum(bool(r['probe_normal_forces_n']) for r in rows),
        unrelated_leaf_contact_ticks=sum(bool(r['other_leaf_contacts']) for r in rows),
        min_base_z=min(r['base_z'] for r in rows),max_tilt_deg=float(np.rad2deg(max(r['tilt_rad'] for r in rows))),
        robot_safety_stop=b.reason,scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        diagnostic_diff='Visible .018m kinematic sphere behind source door, removed for terminal hold; no actor and no robot opening claim.',
        no_gasket=True,original_usd=False)
    report['passed']=bool(report['closed_max_drift_rad']<1e-4 and report['contact_ticks']>0 and
        report['terminal_min_left_open_deg'] is not None and report['terminal_min_left_open_deg']>30 and
        not report['unrelated_leaf_contact_ticks'] and b.reason is None and report['min_base_z']>.55 and report['max_tilt_deg']<35)
    native_rows=[json.loads(line) for line in (out/'native-evaluator/audit.jsonl').read_text().splitlines()]
    independent=physical_audit(native_rows,initial_time)
    report.update(evaluator_contract=FridgeEvaluator.contract,native_evaluator_outcome=evaluator.outcome(b),
        evaluator_samples=len(native_rows),independent_task_pass=independent['passed'],
        synthetic_probe_correctly_excluded=all(not row['contacts'] for row in native_rows),
        inherited_contact_diagnostic_pass=report['passed'],minimum_hand_driven_open_deg=2.,
        diagnostic_purpose='Real native evaluator integration: probe opens door but must not earn robot-hand task success.')
    report['passed']=bool(report['passed'] and len(native_rows)==len(rows) and evaluator.outcome(b)=='in_progress'
        and not independent['passed'] and report['synthetic_probe_correctly_excluded'])
    (out/'independent-task-review.json').write_text(json.dumps(independent,indent=2)+'\n')
    (out/'host-physics.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
