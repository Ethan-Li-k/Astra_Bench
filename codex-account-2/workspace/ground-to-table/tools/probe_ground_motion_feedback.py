"""Verify public sensor snapshots leave the same diagnostic physics unchanged."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.episode_video import EpisodeVideo
from rsi.policy_harness import LocalFourPointHarness

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='public-motion-feedback-01')
    args=parser.parse_args()
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'artifacts/continuous-original-g1-01'
    old=json.loads((source/'result.json').read_text())
    out=ROOT/'artifacts'/args.output;out.mkdir(parents=True,exist_ok=False)
    b=create_backend(continuous=True)
    state_sha=hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest()
    assert state_sha==old['initial_state_sha256']
    video=EpisodeVideo(b,out/'video',label='DEVELOPMENT sensor-path parity | NO TASK CREDIT',
        extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist()})
    evaluator=GroundEvaluator(out/'host_audit')
    harness=LocalFourPointHarness(b,out/'public',image_capture=video,evaluator=evaluator)
    packet=harness.start('Public sensor feedback development test; not actor experience')
    action={'request_id':'sensor-parity','mode':'four_point','reason':'Same reference, verify sensor-only changes',
        'trajectory':[{'target':p,'duration_s':.5,'active':{'position':list(old['final_status']['active_position_links']),'orientation':[]},
                       'grippers':{'left':0.,'right':0.}}
                      for p in old['final_status']['approved_knots'][1:]]}
    try:result=harness.scalebfm_act(packet['observation_path'],action)
    finally:evaluator.close();video.close()
    original=[json.loads(x) for x in (source/'video/robot_trace.jsonl').read_text().splitlines()]
    current=[json.loads(x) for x in (out/'video/robot_trace.jsonl').read_text().splitlines()]
    assert len(original)==len(current)
    delta=max(float(np.max(np.abs(np.array(a['host_render_state']['qpos'])-c['host_render_state']['qpos']))) for a,c in zip(original,current))
    motion=json.loads(Path(result['motion_evidence']['proprioception_path']).read_text())
    control=all(len(s['robot_control_feedback']['joint_target_before_wrist_pi_rad'])==29
        and abs(s['sim_s']-s['robot_control_feedback']['interval_end_sim_s'])<1e-8
        for s in motion['samples'])
    report={'physics_backend':'MuJoCo','new_task_successes':0,'actor_input':False,
        'matched_initial_state':True,'physics_samples':len(current),'max_qpos_delta':delta,
        'public_proprio_samples':len(motion['samples']),'rgb_snapshots':len(motion['snapshots']),
        'control_feedback_present_and_aligned':control,
        'robot_com_present':all('robot_com_model' in s for s in motion['samples']),
        'robot_upper_body_present':all(len(s.get('robot_upper_body_world',{}))==7 for s in motion['samples']),
        'only_head_and_right_wrist':all(i['camera'] in ('head_cam','right_wrist_cam') for s in motion['snapshots'] for i in s['images']),
        'motion_evidence':result['motion_evidence'],'audit':evaluator.audit.result()}
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='motion_evidence'}),flush=True)
    assert delta<1e-9
    assert control
    assert report['robot_upper_body_present']

if __name__=='__main__':main()
