"""Local original-asset verification of the imported bounded UMI-4 interface.

Synthetic robot-only reference stays supervisor-only and earns no task credit.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.four_point import FOUR_POINT_NAMES,FourPointPose
from rsi.episode_video import EpisodeVideo

def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=ROOT/'artifacts/continuous-original-g1-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(continuous=True)
    initial=FourPointPose.from_mapping(b.observe()['four_point_world'])
    poses=[initial.copy() for _ in range(5)]
    for i,x in enumerate((0.,.03,.06,.12,.18)):poses[i].positions[:2,0]+=x
    poses[1].positions[2]+=[.06,0,.20]
    for i in (2,3,4):poses[i].positions[2,0]+=.12
    poses[3].positions[3]+=[.12,0,.20]
    poses[4].positions[3,0]+=.24
    rows=[{'target':p,'duration_s':.5,
           'active':{'position':list(FOUR_POINT_NAMES),'orientation':[]},
           'grippers':{'left':0.,'right':0.}} for p in poses[1:]]
    e=GroundEvaluator(out/'host_audit');e.reset(b)
    video=EpisodeVideo(b,out/'video',label='DEVELOPMENT continuous UMI-4 | original G1 | NO TASK CREDIT',
                      extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist()})
    initial_state=hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest()
    obs=b.observe();b.move_four_point_sequence(obs['observation_id'],'continuous-validation',rows)
    b.set_grippers(0.,0.,duration=2.)
    air=[0.,0.];maxair=[0.,0.];peak=[0.,0.];t0=float(b.data.time)
    try:
        while b.active and not b.reason:
            b.tick();e.update(b);video.record_tick('development_no_task_credit')
            s=e.audit.previous
            for i in range(2):
                air[i]=air[i]+.02 if not s['foot_contact'][i] else 0.
                maxair[i]=max(maxair[i],air[i]);peak[i]=max(peak[i],s['feet'][i][2]-initial.positions[i+2,2])
        result={'backend':'MuJoCo','original_asset':True,'tracker_mode':'UMI-4','original_weight':True,
                'wrist_pi':'unchanged','pd_hz':250,'synthetic_reference':True,'actor_input':False,
                'gpt_calls':0,'new_task_successes':0,'sim_s':float(b.data.time)-t0,
                'initial_state_sha256':initial_state,'max_no_force_contact_s':maxair,
                'peak_ankle_height_gain_m':peak,'audit':e.audit.result(),'stop_reason':b.reason,
                'final_status':b.status(),'reference_provenance':'Shared probe_continuous_reference, local validation only'}
        (out/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k!='final_status'}),flush=True)
    finally:e.close();video.close()

if __name__=='__main__':main()
