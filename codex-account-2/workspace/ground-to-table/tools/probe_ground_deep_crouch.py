"""DEVELOPMENT deep-crouch feasibility, no actor input or task credit.

Replays own public state preparation then executes synthetic bounded references
with expanded stop limits. Never changes physical state, assets or dynamics.
"""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.policy_harness import LocalFourPointHarness
from rsi.episode_video import EpisodeVideo
from rsi.four_point import FOUR_POINT_NAMES,FourPointPose
from tools.learn_grasp_skill import finger_geometry


def hand_floor_gap(b):
    geometry=finger_geometry(b);gaps=[]
    for side in ('left','right'):
        bid=b.model.body(side+'_wrist_yaw_link').id;R=b.data.xmat[bid].reshape(3,3)
        values=[]
        for g in geometry[side].values():
            world=np.array(g['capsule_endpoints_wrist_m'])@R.T+b.data.xpos[bid]
            values.append(float(world[:,2].min()-g['radius_m']))
        gaps.append(min(values))
    return gaps


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'campaign/episode-0007'
    actions=[json.loads(x)['arguments']['response'] for x in (source/'rollout/history.jsonl').read_text().splitlines()
        if json.loads(x)['tool']=='scalebfm_act'][:23]
    out=ROOT/'artifacts/deep-crouch-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(continuous=True,diagnostic_stability_limits=(.20,70.))
    feet={b.model.body(s+'_ankle_roll_link').id for s in ('left','right')}
    original_tick=b.tick;monitor=[]
    def monitored_tick():
        original_tick()
        if b.reason:return
        d,m=b.data,b.model;q=d.qpos[3:7]
        tilt=float(np.rad2deg(np.arccos(np.clip(1-2*(q[1]**2+q[2]**2),-1,1))))
        reason=None
        if d.qpos[2]<.30 or tilt>45.:reason='development_posture_boundary'
        for i,c in enumerate(d.contact):
            a,z=int(c.geom1),int(c.geom2)
            if m.geom_type[a]==mujoco.mjtGeom.mjGEOM_PLANE:a,z=z,a
            if m.geom_type[z]!=mujoco.mjtGeom.mjGEOM_PLANE:continue
            bid=int(m.geom_bodyid[a])
            if bid not in b.robot_com_bodies or bid in feet:continue
            force=np.zeros(6);mujoco.mj_contactForce(m,d,i,force)
            if force[0]>.01:reason='development_nonfoot_ground_contact'
        if reason:
            monitor.append({'sim_s':float(d.time),'reason':reason,'pelvis_z':float(d.qpos[2]),'tilt_deg':tilt})
            b.reason=reason
            if b.active:b.commands[b.active]['status']='aborted';b.active=None
    b.tick=monitored_tick
    c=mujoco.MjvCamera();c.type=mujoco.mjtCamera.mjCAMERA_FREE
    c.distance=2.1;c.azimuth=235;c.elevation=-18;c.lookat[:]=[.4,0.,.5]
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT deep crouch | SYNTHETIC CONTINUATION | NO TASK CREDIT',
        video_cameras=(c,'head_cam'),extra_trace=lambda s:{'qpos':s.data.qpos.tolist(),'qvel':s.data.qvel.tolist()})
    e=GroundEvaluator(out/'host_audit');h=LocalFourPointHarness(b,out/'private_replay',image_capture=v,evaluator=e)
    packet=h.start('Development reference feasibility only');summaries=[];deep_start=None
    def brief(label):
        d=b.data;q=d.qpos[3:7]
        row={'stage':label,'sim_s':float(d.time),'pelvis_m':d.qpos[:3].tolist(),
            'tilt_deg':float(np.rad2deg(np.arccos(np.clip(1-2*(q[1]**2+q[2]**2),-1,1)))),
            'finger_gap_m':hand_floor_gap(b),'foot_contact':e.audit.previous['foot_contact'],'stop':b.reason}
        summaries.append(row);print(json.dumps(row),flush=True)
        (out/'progress.json').write_text(json.dumps(summaries,indent=2))
    try:
        for i,action in enumerate(actions):
            action['request_id']=f'dev-prepare-{i}'
            packet=h.scalebfm_act(packet['observation_path'],action)
            if b.reason:break
        deep_start=float(b.data.time);brief('replayed_public_preparation')
        floor_z=FourPointPose.from_mapping(packet['observation']['four_point_world']).positions[2:,2].copy()
        for number in range(7):
            if b.reason or hand_floor_gap(b)[0]<.04:break
            start=FourPointPose.from_mapping(packet['observation']['four_point_world']);rows=[]
            for phase in (.5,1.):
                pose=start.copy();pose.positions[0,2]-=.04*phase;pose.positions[1,2]-=.02*phase
                pose.positions[2:,2]=start.positions[2:,2]+phase*(floor_z+.08+.03*number-start.positions[2:,2])
                rows.append({'target':pose.to_mapping(),'duration_s':.5,
                    'active':{'position':list(FOUR_POINT_NAMES),'orientation':[]},'grippers':{'left':0.,'right':0.}})
            packet=h.scalebfm_act(packet['observation_path'],{'mode':'four_point','request_id':f'dev-deeper-{number}',
                'trajectory':rows,'reason':'Synthetic development continuation, no actor experience or task credit'})
            brief(f'synthetic_descent_{number}')
        # Try bounded return toward the public pre-probe wrist height; never
        # resume physics after an explicit development stop.
        if not b.reason:
            desired=np.array(json.loads((source/'rollout/episode/observations/0023/observation.json').read_text())['four_point_world']['left_wrist_yaw_link']['position_world_m'])
            for number in range(8):
                if b.reason:break
                start=FourPointPose.from_mapping(packet['observation']['four_point_world'])
                if start.positions[0,2]>=desired[2]-.01:break
                rows=[]
                for phase in (.5,1.):
                    pose=start.copy();pose.positions[:2,2]+=.04*phase
                    pose.positions[2:,2]=start.positions[2:,2]+phase*(floor_z-start.positions[2:,2])
                    rows.append({'target':pose.to_mapping(),'duration_s':.5,
                        'active':{'position':list(FOUR_POINT_NAMES),'orientation':[]},'grippers':{'left':0.,'right':0.}})
                packet=h.scalebfm_act(packet['observation_path'],{'mode':'four_point','request_id':f'dev-return-{number}',
                    'trajectory':rows,'reason':'Synthetic developer recovery, no task credit'})
                brief(f'synthetic_recovery_{number}')
    finally:e.close();v.close()
    old=[json.loads(x) for x in (source/'video/robot_trace.jsonl').read_text().splitlines()]
    new=[json.loads(x) for x in (out/'video/robot_trace.jsonl').read_text().splitlines()]
    pairs=[(a,z) for a,z in zip(old,new) if a['sim_s']<=deep_start+1e-9]
    delta=max(float(np.max(np.abs(np.array(a['host_render_state']['qpos'])-z['host_render_state']['qpos']))) for a,z in pairs)
    result={'backend':'MuJoCo','original_model_mode_pd_wrist_pi':True,'formal_limits_unchanged':[.55,25.],
        'developer_limits':'root>=.30m, tilt<=45deg, no nonfoot-floor force>.01N; outer runtime guard .20m/70deg',
        'public_preparation_prefix_samples':len(pairs),'max_qpos_delta_on_preparation':delta,
        'deep_start_sim_s':deep_start,'monitor_stops':monitor,'summaries':summaries,
        'synthetic_continuation':True,'actor_input':False,'new_task_successes':0,'gpt_calls':0,
        'source_actions_sha256':hashlib.sha256((source/'rollout/history.jsonl').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='summaries'}),flush=True)

if __name__=='__main__':main()
