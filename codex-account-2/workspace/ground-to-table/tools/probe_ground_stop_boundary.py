"""Replay own actor references with explicit DEVELOPMENT stop thresholds.

This does not change the formal default or earn task success credit.
"""
import hashlib
import json
from pathlib import Path
import mujoco
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.policy_harness import LocalFourPointHarness
from rsi.episode_video import EpisodeVideo


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'campaign/episode-0006'
    actions=[json.loads(x)['arguments']['response'] for x in (source/'rollout/history.jsonl').read_text().splitlines()
        if json.loads(x)['tool']=='scalebfm_act']
    out=ROOT/'artifacts/stop-boundary-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(continuous=True,diagnostic_stability_limits=(.20,70.))
    c=mujoco.MjvCamera();c.type=mujoco.mjtCamera.mjCAMERA_FREE
    c.distance=2.2;c.azimuth=235;c.elevation=-18;c.lookat[:]=[.25,0.,.5]
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT stop-boundary replay | NO TASK CREDIT',
        video_cameras=(c,'head_cam'),extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist()})
    e=GroundEvaluator(out/'host_audit');h=LocalFourPointHarness(b,out/'private_replay',image_capture=v,evaluator=e)
    packet=h.start('Developer replay only; actor must not read this folder')
    try:
        for i,action in enumerate(actions):
            action['request_id']=f'development-replay-{i}'
            packet=h.scalebfm_act(packet['observation_path'],action)
            print(json.dumps({'replayed_action':i+1,'sim_s':b.data.time,'status':b.status()['status'],'stop':b.reason}),flush=True)
            if b.reason:break
        # Observe continued closed-loop hold after the original action deadline.
        for _ in range(100):
            if b.reason:break
            b.tick();e.update(b);v.record_tick('development_hold_no_task_credit')
    finally:e.close();v.close()
    old=[json.loads(x) for x in (source/'video/robot_trace.jsonl').read_text().splitlines()]
    new=[json.loads(x) for x in (out/'video/robot_trace.jsonl').read_text().splitlines()]
    n=min(len(old),len(new))
    delta=max(float(np.max(np.abs(np.array(a['host_render_state']['qpos'])-z['host_render_state']['qpos']))) for a,z in zip(old[:n],new[:n]))
    qp=np.array([x['host_render_state']['qpos'] for x in new])
    tilt=np.rad2deg(np.arccos(np.clip(1-2*(qp[:,4]**2+qp[:,5]**2),-1,1)))
    result={'backend':'MuJoCo','formal_default_unchanged':[.55,25.],
        'development_stability_limits':[.20,70.],'changed_variable':'stop thresholds only; references replay own real actor proposals',
        'original_prefix_samples_compared':n,'max_qpos_difference_on_original_prefix':delta,
        'first_original_limit_crossing_s':next((x['sim_s'] for x,t in zip(new,tilt) if t>25),None),
        'last_sim_s':float(b.data.time),'max_tilt_deg':float(max(tilt)),'final_tilt_deg':float(tilt[-1]),
        'min_pelvis_height_m':float(qp[:,2].min()),'final_pelvis_m':b.data.qpos[:3].tolist(),
        'final_wrist_heights_m':b.data.xpos[b.adapter.body_ids[b.four[:2]],2].tolist(),
        'stop_reason':b.reason,'new_task_successes':0,'actor_input':False,'gpt_calls':0,
        'source_actions_sha256':hashlib.sha256((source/'rollout/history.jsonl').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

if __name__=='__main__':main()
