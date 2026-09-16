"""DEVELOPMENT matched own-recovery replay, orientation active/inactive."""
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
    p=argparse.ArgumentParser();p.add_argument('--orientation',choices=('active','inactive'),required=True);args=p.parse_args()
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'campaign/episode-0010';assert json.loads((source/'rollout/policy_stop.json').read_text())['rollout_finished']
    out=ROOT/'artifacts'/('wrist-orientation-constraint-'+args.orientation+'-01');out.mkdir(exist_ok=False)
    b=create_backend(continuous=True);c=mujoco.MjvCamera();c.type=mujoco.mjtCamera.mjCAMERA_FREE
    c.distance=2.1;c.azimuth=235;c.elevation=-18;c.lookat[:]=[.4,0,.5]
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT matched wrist constraint | NO TASK CREDIT',video_cameras=(c,'head_cam'),
        extra_trace=lambda s:{'qpos':s.data.qpos.tolist(),'qvel':s.data.qvel.tolist(),
            'wrist_pi_integral':s.wrist_pi.e_int.tolist(),'wrist_pi_torque_nm':s.wrist_pi_tau.tolist()})
    e=GroundEvaluator(out/'host_audit');h=LocalFourPointHarness(b,out/'private_replay',image_capture=v,evaluator=e)
    packet=h.start('Development orientation-constraint A/B only');executed=0
    try:
        lines=(source/'rollout/history.jsonl').read_text().splitlines()
        actions=[json.loads(x)['arguments']['response'] for x in lines if json.loads(x)['tool']=='scalebfm_act']
        assert len(actions)==17
        for i,a in enumerate(actions):
            a['request_id']=f'dev-replay-{i}';packet=h.scalebfm_act(packet['observation_path'],a);executed+=1
            if b.reason or e.audit.invalid:break
        prefix_end=float(b.data.time);start=FourPointPose.from_mapping(packet['observation']['four_point_world'])
        before_integral=b.wrist_pi.e_int.copy();rows=[]
        for fraction in (.5,1.):
            target=start.copy();target.positions[:2,2]-=.02*fraction
            rows.append({'duration_s':.5,'target':target.to_mapping(),
                'active':{'position':list(FOUR_POINT_NAMES[:2]),'orientation':list(FOUR_POINT_NAMES[:2]) if args.orientation=='active' else []},
                'grippers':{'left':0.,'right':0.}})
        if not b.reason and not e.audit.invalid:
            packet=h.scalebfm_act(packet['observation_path'],{'mode':'four_point','request_id':'dev-orientation-ab','trajectory':rows,
                'reason':'Development A/B of actor-proposed hypothesis; not actor experience or task credit'})
        end=FourPointPose.from_mapping(packet['observation']['four_point_world'])
    finally:e.close();v.close()
    old=[json.loads(x) for x in (source/'video/robot_trace.jsonl').read_text().splitlines()]
    new=[json.loads(x) for x in (out/'video/robot_trace.jsonl').read_text().splitlines()]
    pairs=[(a,z) for a,z in zip(old,new) if a['sim_s']<=prefix_end+1e-9]
    delta=max(float(np.max(np.abs(np.array(a['host_render_state']['qpos'])-z['host_render_state']['qpos']))) for a,z in pairs)
    report={'backend':'MuJoCo','orientation_active':args.orientation=='active','original_controller_gains_and_stops':True,
        'source_physical_actions_replayed':executed,'prefix_samples':len(pairs),'prefix_end_sim_s':prefix_end,'prefix_qpos_max_delta':delta,
        'before_wrist_integral':before_integral.tolist(),'after_wrist_integral':b.wrist_pi.e_int.tolist(),
        'actual_descent_m':(start.positions[:2,2]-end.positions[:2,2]).tolist(),'probe_sim_s':float(b.data.time)-prefix_end,
        'final_status':b.status(),'audit':e.audit.result(),'actor_input':False,'gpt_calls':0,'new_task_successes':0,
        'comparison_rule':'Compare states at identical times while both commands remain active; endpoint durations can differ because orientation changes arrival criteria.',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
