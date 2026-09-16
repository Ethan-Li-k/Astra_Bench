"""Correct joint-angle interpretation using only own public robot history."""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT,GroundSim
from rsi.robot_kinematics import upper_body_world,upper_body_conventions


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    b=GroundSim();m=b.model;d=mujoco.MjData(m);rows=[];hashes={};error=0.
    for number in (16,17):
        p=ROOT/f'campaign/episode-0010/rollout/episode/observations/{number:04d}/observation.json'
        raw=p.read_bytes();o=json.loads(raw);hashes[str(p)]=hashlib.sha256(raw).hexdigest()
        d.qpos[:3]=o['pelvis_world']['position_world_m'];d.qpos[3:7]=o['pelvis_world']['quaternion_wxyz']
        for nk,vk in [('joint_names','joint_position_rad'),('finger_names','finger_position_rad')]:
            for name,value in zip(o[nk],o[vk]):d.qpos[m.joint(name).qposadr[0]]=value
        mujoco.mj_forward(m,d) # Scratch FK only, no mj_step or candidate action.
        landmarks=upper_body_world(m,d);arms={}
        for name,pose in o['four_point_world'].items():error=max(error,float(np.abs(d.xpos[m.body(name).id]-pose['position_world_m']).max()))
        for side in ('left','right'):
            points=np.array([landmarks[side+'_'+suffix+'_link']['position_world_m'] for suffix in ('shoulder_pitch','elbow','wrist_yaw')])
            vectors=np.diff(points,axis=0);lengths=np.linalg.norm(vectors,axis=1)
            arms[side]={'joint_scalar_rad':float(d.qpos[m.joint(side+'_elbow_joint').qposadr[0]]),
                'shoulder_elbow_wrist_polyline_angle_deg':float(np.rad2deg(np.arccos(np.clip(vectors[0]@vectors[1]/np.prod(lengths),-1,1)))),
                'angle_definition':'Angle between shoulder-to-elbow and elbow-to-wrist vectors;0deg means parallel/straight polyline. This is not a direct anatomical hinge angle.',
                'shoulder_to_wrist_distance_m':float(np.linalg.norm(points[2]-points[0])),
                'shoulder_to_wrist_vertical_drop_m':float(points[0,2]-points[2,2]),'segment_lengths_m':lengths.tolist()}
        rows.append({'source_observation':str(p),'sim_s':o['sim_s'],'robot_upper_body_world':landmarks,'arms':arms})
    assert error<1e-9
    out=ROOT/'campaign/memory/arm_geometry_episode-0010.json'
    if out.exists():raise FileExistsError(out)
    report={'scope':'Robot-only FK reconstructed solely from own already-public measured pelvis pose and named policy/finger joints,plus known original robot geometry. No host audit/object/contact/reward state,IK solution,generated reference or new physics.',
        'source_hashes':hashes,'max_public_four_point_reconstruction_error_m':error,'original_robot_upper_chain_conventions':upper_body_conventions(m),'rows':rows,
        'correction':'Own0010 observation16 to17 had decreasing elbow scalars while the shoulder-elbow-wrist polylines became MORE folded,not straighter. Earlier language calling that recovery arm extension was not established. Do not infer anatomical flexion/extension solely from scalar sign; inspect FK geometry and actual hand clearance.',
        'causal_limit':'Other joints and pelvis changed too; these are two actual measured configurations,not a single-joint ablation or a new action recommendation.'}
    out.write_text(json.dumps(report,indent=2));print(json.dumps({'output':str(out),'max_fk_error_m':error,'rows':[{'sim_s':r['sim_s'],'arms':r['arms']} for r in rows]}),flush=True)

if __name__=='__main__':main()
