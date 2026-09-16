"""Derive robot-only COM from archived public proprioception, never host truth."""
import argparse
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT,GroundSim


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--episode',required=True);args=parser.parse_args()
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'campaign'/args.episode
    if not (source/'result.json').is_file():raise ValueError('Only completed episodes may be enriched')
    b=GroundSim();m=b.model;d=mujoco.MjData(m);rows=[];hashes={};max_error=0.
    for path in sorted((source/'rollout/episode/observations').glob('*/observation.json')):
        obs=json.loads(path.read_text());hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        root=obs['pelvis_world'];d.qpos[:3]=root['position_world_m'];d.qpos[3:7]=root['quaternion_wxyz']
        for names,values in [('joint_names','joint_position_rad'),('finger_names','finger_position_rad')]:
            for name,value in zip(obs[names],obs[values]):d.qpos[m.joint(name).qposadr[0]]=value
        mujoco.mj_forward(m,d) # scratch FK only; no mj_step or robot action
        for name,pose in obs['four_point_world'].items():
            max_error=max(max_error,float(np.max(np.abs(d.xpos[m.body(name).id]-pose['position_world_m']))))
        com=np.average(d.xipos[b.robot_com_bodies],axis=0,weights=b.robot_com_masses)
        feet=np.array([obs['four_point_world'][s+'_ankle_roll_link']['position_world_m'] for s in ('left','right')])
        middle=feet.mean(axis=0);q=np.array(root['quaternion_wxyz'])
        rows.append({'observation_path':str(path),'sim_s':obs['sim_s'],
            'robot_com_world_m':com.tolist(),'ankle_midpoint_world_m':middle.tolist(),
            'com_minus_ankle_midpoint_m':(com-middle).tolist(),
            'pelvis_minus_ankle_midpoint_m':(np.array(root['position_world_m'])-middle).tolist(),
            'pelvis_tilt_deg':float(np.rad2deg(np.arccos(np.clip(1-2*(q[1]**2+q[2]**2),-1,1))))})
    assert max_error<1e-9
    out=ROOT/'campaign/memory'/('balance_'+args.episode+'.json')
    if out.exists():raise FileExistsError(out)
    report={'scope':'Robot inertial-model FK derived solely from own completed public proprioception. No host audit, object/contact/reward state, reference generation or new physics.',
        'exclusions':'Objects and carried loads excluded; ankle midpoint is a geometric reference, not a measured support center; COM projection does not prove dynamic stability.',
        'max_public_four_point_reconstruction_error_m':max_error,'source_hashes':hashes,'rows':rows}
    out.write_text(json.dumps(report,indent=2))
    print(json.dumps({'output':str(out),'samples':len(rows),'max_fk_error_m':max_error,
        'last_com_minus_midpoint_m':rows[-1]['com_minus_ankle_midpoint_m'],
        'last_pelvis_minus_midpoint_m':rows[-1]['pelvis_minus_ankle_midpoint_m']}),flush=True)

if __name__=='__main__':main()
