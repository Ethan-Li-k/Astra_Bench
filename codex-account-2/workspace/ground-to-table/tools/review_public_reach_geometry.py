"""Historical robot FK interpretation audit. No new physics or action proposal."""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT, GroundSim
from rsi.robot_kinematics import upper_body_world


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=ROOT/'artifacts/episode-0011-public-reach-geometry'
    out.mkdir(exist_ok=False)
    b=GroundSim();m=b.model;d=mujoco.MjData(m);rows=[];hashes={};error=0.
    for p in sorted((ROOT/'campaign/episode-0011/rollout/episode/observations').glob('*/observation.json')):
        raw=p.read_bytes();o=json.loads(raw);hashes[str(p)]=hashlib.sha256(raw).hexdigest()
        d.qpos[:3]=o['pelvis_world']['position_world_m'];d.qpos[3:7]=o['pelvis_world']['quaternion_wxyz']
        for nk,vk in [('joint_names','joint_position_rad'),('finger_names','finger_position_rad')]:
            for name,value in zip(o[nk],o[vk]):d.qpos[m.joint(name).qposadr[0]]=value
        mujoco.mj_forward(m,d)
        landmarks=upper_body_world(m,d);arms={}
        for name,pose in o['four_point_world'].items():
            error=max(error,float(np.abs(d.xpos[m.body(name).id]-pose['position_world_m']).max()))
        for side in ('left','right'):
            points=np.array([landmarks[side+'_'+s+'_link']['position_world_m'] for s in ('shoulder_pitch','elbow','wrist_yaw')])
            vectors=np.diff(points,axis=0)
            arms[side]={'elbow_scalar_rad':float(d.qpos[m.joint(side+'_elbow_joint').qposadr[0]]),
                'polyline_angle_deg':float(np.rad2deg(np.arccos(np.clip(vectors[0]@vectors[1]/np.prod(np.linalg.norm(vectors,axis=1)),-1,1)))),
                'shoulder_to_wrist_distance_m':float(np.linalg.norm(points[2]-points[0])),
                'wrist_height_m':float(points[2,2]),'shoulder_height_m':float(points[0,2])}
        rows.append({'observation':p.parent.name,'sim_s':o['sim_s'],'pelvis_height_m':float(d.qpos[2]),'arms':arms})
    assert error<1e-9
    report={'source_scope':'Own public robot observations plus original known robot geometry only. No object/contact truth or IK.',
        'new_physics':False,'actor_input':False,'gpt_calls':0,'new_task_successes':0,
        'max_four_point_fk_error_m':error,'source_sha256':hashes,'rows':rows,
        'angle_definition':'Angle between shoulder-pitch-to-elbow and elbow-to-wrist vectors;0deg is parallel. Other joints change too; not single-joint causality.',
        'interpretation':'Compare actual geometry before calling a scalar joint change flexion or extension. A lower wrist can be progress without a crouch; neither alone establishes floor grasp.'}
    (out/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'max_fk_error_m':error,'rows':rows}),flush=True)


if __name__=='__main__':main()
