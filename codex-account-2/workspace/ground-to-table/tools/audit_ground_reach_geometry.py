"""Inspect existing robot-only IK candidates; no policy/physics/demo credit."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from ground_task import ROOT,GroundSim
from tools.probe_ground_deep_crouch import hand_floor_gap


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'artifacts/reach-tilt-boundary-01/results.json'
    out=ROOT/'artifacts/reach-hand-geometry-01';out.mkdir(exist_ok=False)
    b=GroundSim();m=b.model;d=mujoco.MjData(m);rows=[]
    for item in json.loads(source.read_text()):
        d.qpos[:]=b.data.qpos;d.qpos[:3]=item['pelvis_m']
        q=Rotation.from_euler('y',item['pelvis_pitch_deg'],degrees=True).as_quat()
        d.qpos[3:7]=q[[3,0,1,2]]
        for name,value in zip(item['joint_names'],item['joint_angles_rad']):
            d.qpos[m.joint(name).qposadr[0]]=value
        mujoco.mj_forward(m,d) # Scratch data only, never mj_step.
        com=np.average(d.xipos[b.robot_com_bodies],axis=0,weights=b.robot_com_masses)
        feet=np.array([d.xpos[m.body(side+'_ankle_roll_link').id] for side in ('left','right')])
        contacts=[]
        for c in d.contact:
            a,z=int(c.geom1),int(c.geom2)
            if not (m.geom_bodyid[a] in b.robot_com_bodies or m.geom_bodyid[z] in b.robot_com_bodies):continue
            contacts.append({'geoms':[m.geom(a).name,m.geom(z).name],'distance_m':float(c.dist),
                'scope':'geometric overlap/proximity, no physical force/stability claim'})
        tips=[]
        for name in ('left_hand_thumb_2_collision','left_hand_index_1_collision','left_hand_middle_1_collision'):
            g=m.geom(name);axis=d.geom_xmat[g.id].reshape(3,3)[:,2]*g.size[1]
            tips.append({'name':name,'center_world_m':d.geom_xpos[g.id].tolist(),
                'endpoint_world_m':[(d.geom_xpos[g.id]-axis).tolist(),(d.geom_xpos[g.id]+axis).tolist()],
                'radius_m':float(g.size[0])})
        rows.append({'pelvis_tilt_limit_deg':item['pelvis_tilt_limit_deg'],'seed':item['seed'],
            'pelvis_m':item['pelvis_m'],'pelvis_pitch_deg':item['pelvis_pitch_deg'],
            'wrist_goal_error_m':item['wrist_error_m'],'actual_wrist_m':item['actual_wrist_m'],
            'foot_position_error_m':item['max_foot_position_error_m'],'foot_rotation_error_rad':item['max_foot_rotation_error_rad'],
            'distal_finger_floor_gap_m':hand_floor_gap(SimpleNamespace(model=m,data=d)),
            'left_distal_finger_capsules':tips,'robot_com_world_m':com.tolist(),
            'com_minus_ankle_midpoint_m':(com-feet.mean(axis=0)).tolist(),'scratch_contacts':contacts})
    result={'scope':'Original robot FK audit of existing local IK solutions; no new solution or reference generated.',
        'actor_input':False,'candidate_physics_executed':False,'gpt_calls':0,'task_success_credit':0,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':rows,
        'limitations':'Distal finger height alone cannot establish an opposed grasp; local IK, geometric overlaps and COM are not a dynamically stable achievable pose.'}
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k not in ('left_distal_finger_capsules','scratch_contacts')} for r in rows]),flush=True)

if __name__=='__main__':main()
