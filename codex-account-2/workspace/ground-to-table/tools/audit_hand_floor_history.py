"""Offline FK audit of archived real robot states and one synthetic counterexample."""
import argparse
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from ground_task import ROOT,create_backend,CRITERIA,model_digest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--episode');parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=args.output_dir or ROOT/'artifacts/hand-floor-audit-01'
    if ROOT not in out.resolve().parents:raise ValueError('Output must remain in task root')
    out.mkdir(exist_ok=False)
    b=create_backend();m=b.model;d=mujoco.MjData(m);seal=model_digest(m)
    hands=[i for i in range(m.ngeom) if (m.geom(i).name or '').startswith(('left_hand_','right_hand_')) and 'collision' in (m.geom(i).name or '')]
    floors=[i for i in range(m.ngeom) if m.geom_type[i]==mujoco.mjtGeom.mjGEOM_PLANE]
    def gap():
        return min((float(mujoco.mj_geomDistance(m,d,g,f,10.,None)),m.geom(g).name) for g in hands for f in floors)
    rows=[]
    for result in sorted((ROOT/'campaign').glob('episode-*/result.json')):
        if args.episode and result.parent.name!=args.episode:continue
        path=result.parent/'video/robot_trace.jsonl';minimum=(10.,None);at=None;count=0
        with path.open() as stream:
            for line in stream:
                row=json.loads(line);d.qpos[:]=row['host_render_state']['qpos'];mujoco.mj_forward(m,d)
                current=gap();count+=1
                if current[0]<minimum[0]:minimum=current;at=row['sim_s']
        r={'episode':result.parent.name,'samples':count,'minimum_hand_floor_clearance_m':minimum[0],
            'geom':minimum[1],'sim_s':at,'exceeds_5mm_penetration':minimum[0]<-.005,
            'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        rows.append(r);print(json.dumps(r),flush=True)
    # This pose never runs mj_step; it deliberately demonstrates why disabled
    # contact generation must not imply valid geometry.
    old=json.loads((ROOT/'artifacts/reach-tilt-boundary-01/results.json').read_text())[2]
    d.qpos[:]=b.data.qpos;d.qpos[:3]=old['pelvis_m'];q=Rotation.from_euler('y',old['pelvis_pitch_deg'],degrees=True).as_quat();d.qpos[3:7]=q[[3,0,1,2]]
    for name,value in zip(old['joint_names'],old['joint_angles_rad']):d.qpos[m.joint(name).qposadr[0]]=value
    mujoco.mj_forward(m,d);counter=gap()
    contacts=sum(bool({int(c.geom1),int(c.geom2)}&set(hands) and {int(c.geom1),int(c.geom2)}&set(floors)) for c in d.contact)
    assert counter[0]<-.005 and contacts==0 and model_digest(m)==seal
    report={'backend':'MuJoCo scratch FK; no new candidate physics','actor_input':False,'gpt_calls':0,'task_success_credit':0,
        'robot_dynamics_unchanged':True,'hand_collision_geom_count':len(hands),'criteria':CRITERIA,
        'counterexample':{'minimum_signed_distance_m':counter[0],'geom':counter[1],'generated_hand_floor_contacts':contacts,'correctly_rejected_by_new_criterion':True},
        'archived_real_episodes':rows,'source_masks':[{ 'name':m.geom(i).name,'contype':int(m.geom_contype[i]),'conaffinity':int(m.geom_conaffinity[i])} for i in hands+floors]}
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['counterexample']),flush=True)

if __name__=='__main__':main()
