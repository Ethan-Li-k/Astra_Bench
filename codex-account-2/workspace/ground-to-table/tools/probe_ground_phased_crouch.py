"""DEVELOPMENT finite-cue depth test; never actor input or task success."""
import argparse
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.policy_harness import LocalFourPointHarness
from rsi.episode_video import EpisodeVideo
from rsi.four_point import FOUR_POINT_NAMES,FourPointPose


def main():
    p=argparse.ArgumentParser();p.add_argument('--retract-m',type=float,choices=(0.,.02),required=True)
    p.add_argument('--tilt-limit-deg',type=float,choices=(45.,65.),default=45.)
    p.add_argument('--label',required=True);args=p.parse_args()
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'campaign/episode-0009';out=ROOT/'artifacts'/args.label
    if ROOT not in out.resolve().parents:raise ValueError('Output outside task root')
    out.mkdir(exist_ok=False)
    b=create_backend(continuous=True,diagnostic_stability_limits=(.20,70.));m=b.model
    feet={m.body(s+'_ankle_roll_link').id for s in ('left','right')}
    original_tick=b.tick;stops=[];stage={'name':'preparation'};external_contacts={}
    def monitored_tick():
        original_tick()
        if b.reason:return
        q=b.data.qpos[3:7];tilt=float(np.rad2deg(np.arccos(np.clip(1-2*(q[1]**2+q[2]**2),-1,1))))
        reason=None
        if b.data.qpos[2]<.30 or tilt>args.tilt_limit_deg:reason='development_posture_boundary'
        for i,c in enumerate(b.data.contact):
            a,z=int(c.geom1),int(c.geom2)
            ba,bz=int(m.geom_bodyid[a]),int(m.geom_bodyid[z])
            # Every external robot contact must be a foot-floor contact.
            robot_a=ba in b.robot_com_bodies;robot_z=bz in b.robot_com_bodies
            if robot_a==robot_z:continue
            if robot_z:a,z,ba,bz=z,a,bz,ba
            if ba in feet and m.geom_type[z]==mujoco.mjtGeom.mjGEOM_PLANE:continue
            force=np.zeros(6);mujoco.mj_contactForce(m,b.data,i,force)
            if force[0]>.01:
                key=(stage['name'],m.geom(a).name,m.geom(z).name)
                row=external_contacts.setdefault(key,{'stage':stage['name'],'geoms':[m.geom(a).name,m.geom(z).name],
                    'first_sim_s':float(b.data.time),'last_sim_s':float(b.data.time),'max_normal_force_n':0.,'samples':0})
                row['last_sim_s']=float(b.data.time);row['max_normal_force_n']=max(row['max_normal_force_n'],float(force[0]));row['samples']+=1
                if stage['name']!='preparation':reason='development_nonfoot_external_contact'
        if reason:
            stops.append({'sim_s':float(b.data.time),'reason':reason})
            b.reason=reason
            if b.active:b.commands[b.active]['status']='aborted';b.active=None
    b.tick=monitored_tick
    c=mujoco.MjvCamera();c.type=mujoco.mjtCamera.mjCAMERA_FREE;c.distance=2.1;c.azimuth=235;c.elevation=-18;c.lookat[:]=[.4,0,.5]
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT finite crouch | SYNTHETIC CONTINUATION | NO TASK CREDIT',
        video_cameras=(c,'head_cam'),extra_trace=lambda s:{'qpos':s.data.qpos.tolist(),'qvel':s.data.qvel.tolist()})
    e=GroundEvaluator(out/'host_audit');h=LocalFourPointHarness(b,out/'private_replay',image_capture=v,evaluator=e)
    packet=h.start('Development finite-cue depth only');summaries=[]
    def brief(label):
        s=e.sample(b);q=b.data.qpos[3:7]
        r={'stage':label,'sim_s':s['t'],'pelvis_m':s['pelvis'],'hand_floor_gap_m':s['hand_floor_clearance'],
            'tilt_deg':float(np.rad2deg(np.arccos(np.clip(1-2*(q[1]**2+q[2]**2),-1,1)))),
            'feet_contact':s['foot_contact'],'waist_pitch_rad':float(b.data.qpos[m.joint('waist_pitch_joint').qposadr[0]]),
            'stop':b.reason,'audit_invalid':e.audit.invalid}
        summaries.append(r);(out/'progress.json').write_text(json.dumps(summaries,indent=2));print(json.dumps(r),flush=True)
    def action(rows,name):
        nonlocal packet
        packet=h.scalebfm_act(packet['observation_path'],{'mode':'four_point','request_id':name,'trajectory':rows,
            'reason':'Development synthetic continuation, no actor experience or task credit'})
    try:
        old=[json.loads(x) for x in (source/'rollout/history.jsonl').read_text().splitlines()]
        actions=[r['arguments']['response'] for r in old if r['tool']=='scalebfm_act'][:11]
        preparation_actions=0
        for i,a in enumerate(actions):
            a['request_id']=f'dev-replay-{i}';packet=h.scalebfm_act(packet['observation_path'],a)
            preparation_actions+=1
            if b.reason or e.audit.invalid:break
        prefix_end=float(b.data.time);brief('replayed_public_preparation')
        stage['name']='finite_crouch'
        initial_wrist_height=FourPointPose.from_mapping(packet['observation']['four_point_world']).positions[:2,2].copy()
        for number in range(7):
            if b.reason or e.audit.invalid or summaries[-1]['hand_floor_gap_m']<.06:break
            start=FourPointPose.from_mapping(packet['observation']['four_point_world']);rows=[]
            for i,(foot_z,hand_z) in enumerate(zip((.04,.04,.04,.02,0.),(0.,-.02,-.04,-.06,-.06))):
                target=start.copy();target.positions[:2,2]+=hand_z;target.positions[2:,2]+=foot_z
                target.positions[:2,0]-=args.retract_m*(i+1)/5
                rows.append({'duration_s':.6,'target':target.to_mapping(),'active':{'position':list(FOUR_POINT_NAMES),'orientation':list(FOUR_POINT_NAMES[:2])},'grippers':{'left':0.,'right':0.}})
            action(rows,f'dev-finite-{number}');brief(f'finite_crouch_{number}')
        if not b.reason and not e.audit.invalid:
            # Measured-pose hold tests retention without resetting physical state.
            stage['name']='retention'
            start=FourPointPose.from_mapping(packet['observation']['four_point_world'])
            rows=[{'duration_s':1.,'target':start.to_mapping(),'active':{'position':list(FOUR_POINT_NAMES),'orientation':list(FOUR_POINT_NAMES[:2])},'grippers':{'left':0.,'right':0.}} for _ in range(2)]
            action(rows,'dev-retention');brief('measured_pose_retention')
            stage['name']='recovery'
            for number in range(12):
                if b.reason or e.audit.invalid:break
                start=FourPointPose.from_mapping(packet['observation']['four_point_world'])
                if np.all(start.positions[:2,2]>=initial_wrist_height-.01):break
                rows=[]
                for phase in (.5,1.):
                    target=start.copy();target.positions[:2,2]+=.04*phase
                    rows.append({'duration_s':.5,'target':target.to_mapping(),'active':{'position':list(FOUR_POINT_NAMES[:2]),'orientation':list(FOUR_POINT_NAMES[:2])},'grippers':{'left':0.,'right':0.}})
                action(rows,f'dev-recovery-{number}');brief(f'recovery_{number}')
    finally:e.close();v.close()
    old=[json.loads(x) for x in (source/'video/robot_trace.jsonl').read_text().splitlines()]
    new=[json.loads(x) for x in (out/'video/robot_trace.jsonl').read_text().splitlines()]
    pairs=[(a,z) for a,z in zip(old,new) if a['sim_s']<=prefix_end+1e-9]
    delta=max(float(np.max(np.abs(np.array(a['host_render_state']['qpos'])-z['host_render_state']['qpos']))) for a,z in pairs)
    report={'backend':'MuJoCo','original_model_mode_pd_wrist_pi':True,'formal_limits_unchanged':[.55,25.],
        'developer_boundary':f'root>=.30m,tilt<={args.tilt_limit_deg}deg,hand penetration<=5mm; all preparation external contacts logged, no nonfoot external contact permitted during tested crouch/retention/recovery',
        'developer_tilt_limit_deg':args.tilt_limit_deg,
        'wrist_retraction_m_per_chunk':args.retract_m,'prefix_end_sim_s':prefix_end,'prefix_samples':len(pairs),'prefix_qpos_max_delta':delta,
        'preparation_actions':preparation_actions,'preparation_complete':preparation_actions==11 and prefix_end>50.,
        'external_contacts':list(external_contacts.values()),
        'summaries':summaries,'stops':stops,'actor_input':False,'synthetic_continuation':True,'gpt_calls':0,'new_task_successes':0,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_actions_sha256':hashlib.sha256((source/'rollout/history.jsonl').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='summaries'}),flush=True)

if __name__=='__main__':main()
