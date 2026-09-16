"""Single-factor quarter-second reference diagnostic, not actor experience.

Bypasses ONLY the public minimum segment duration in an isolated developer
instance. Original scene, model, UMI-4, WristPI and250Hz PD remain unchanged.
"""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.four_point import FourPointPose
from rsi.reference_sequence import ReferenceSequence
from rsi.episode_video import EpisodeVideo


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'artifacts/continuous-original-g1-01/result.json'
    baseline=json.loads(source.read_text())
    out=ROOT/'artifacts/continuous-quarter-second-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(continuous=True)
    state_sha=hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest()
    assert state_sha==baseline['initial_state_sha256']
    poses=[FourPointPose.from_mapping(p) for p in baseline['final_status']['approved_knots']]
    rows=[{'target':p,'duration_s':.5,
        'active':{'position':list(baseline['final_status']['active_position_links']),'orientation':[]},
        'grippers':{'left':0.,'right':0.}} for p in poses[1:]]
    obs=b.observe();record=b.move_four_point_sequence(obs['observation_id'],'development-quarter-second',rows)
    start=float(b.data.time);sequence=ReferenceSequence(start+np.arange(len(poses))*.25,poses)
    b._reference_sequence=sequence;b.duration=1.
    record.update(duration_s=1.,knot_sim_s=sequence.times.tolist(),
        developer_only_override='0.25s segments; no public contract/actor change')
    b.set_grippers(0.,0.,duration=1.)
    e=GroundEvaluator(out/'host_audit');e.reset(b)
    camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance=2.1;camera.azimuth=145;camera.elevation=-18;camera.lookat[:]=[0.,0.,.45]
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT quarter-second timing | NO TASK CREDIT',
        video_cameras=(camera,'head_cam'),extra_trace=lambda s:{'qpos':s.data.qpos.tolist(),'qvel':s.data.qvel.tolist()})
    peak=np.zeros(2);air=np.zeros(2);longest=np.zeros(2)
    try:
        while b.active and not b.reason:
            b.tick();e.update(b);v.record_tick('development_no_task_credit')
            sample=e.audit.previous
            peak=np.maximum(peak,np.array(sample['feet'])[:,2]-poses[0].positions[2:,2])
            for i in range(2):air[i]=air[i]+.02 if not sample['foot_contact'][i] else 0.
            longest=np.maximum(longest,air)
        report={'backend':'MuJoCo','model':'original model_38000','mode':'UMI-4','pd_hz':250,
            'wrist_pi':'unchanged','changed_variable':'segment duration0.5s to0.25s',
            'baseline_source':str(source),'baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'initial_state_sha256':state_sha,'matched_initial_qpos_qvel':True,
            'synthetic_reference':True,'public_contract_changed':False,'actor_input':False,'new_task_successes':0,
            'sim_s':float(b.data.time)-start,'peak_ankle_height_gain_m':peak.tolist(),
            'max_no_force_contact_s':longest.tolist(),'audit':e.audit.result(),'stop_reason':b.reason,
            'final_status':record['status']}
        (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    finally:e.close();v.close()

if __name__=='__main__':main()
