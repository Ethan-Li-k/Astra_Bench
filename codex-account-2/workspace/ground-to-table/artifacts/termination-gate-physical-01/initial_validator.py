"""Replay own episode0006 to verify terminal host signaling, no policy credit."""
import hashlib
import json
from pathlib import Path
import numpy as np
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.episode_video import EpisodeVideo
from tools.learn_grasp_skill import LearningHost


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    source=ROOT/'campaign/episode-0006'
    history=source/'rollout/history.jsonl'
    actions=[json.loads(x)['arguments']['response'] for x in history.read_text().splitlines() if json.loads(x)['tool']=='scalebfm_act']
    out=ROOT/'artifacts/termination-gate-physical-01';out.mkdir(exist_ok=False)
    host=LearningHost(out,None,'own0006-termination-replay',0,
        backend_factory=lambda:create_backend(continuous=True),
        evaluator_factory=lambda:GroundEvaluator(out/'host_audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,out/'video',
            label='DEVELOPMENT own0006 replay | TERMINATION CHECK | NO TASK CREDIT',
            extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist(),'ctrl':sim.data.ctrl.tolist()}),
        max_episode_steps=9000,support_plane_z_m=None)
    packets=[]
    try:
        packet=host.dispatch('loco_start',{'task':'Developer replay of own references; no actor or formal credit.','output_dir':str(out/'rollout/episode')})
        for i,action in enumerate(actions):
            action['request_id']=f'termination-replay-{i+1}'
            packet=host.dispatch('scalebfm_act',{'observation_path':packet['observation_path'],
                'output_dir':str(out/f'rollout/action{i+1:02d}'),'response':action})
            packets.append({k:packet[k] for k in ('native_outcome','rollout_finished','stop_reason','backend_stop_reason','remaining_steps','next_call')})
            print(json.dumps({'action':i+1,**packets[-1]}),flush=True)
            if host.finished:break
    finally:host.close()
    old=[json.loads(x) for x in (source/'video/robot_trace.jsonl').read_text().splitlines()]
    new=[json.loads(x) for x in (out/'video/robot_trace.jsonl').read_text().splitlines()]
    assert len(old)==len(new)
    delta=max(float(abs(np.array(a['host_render_state']['qpos'])-b['host_render_state']['qpos']).max()) for a,b in zip(old,new))
    result={'backend':'MuJoCo','gpt_calls':0,'actor_input':False,'new_task_successes':0,
        'source_episode':'episode-0006','source_history_sha256':hashlib.sha256(history.read_bytes()).hexdigest(),
        'replayed_actions':host.actions,'physics_samples':len(new),'max_qpos_delta':delta,
        'formal_stops_unchanged':[.55,25.],'packets':packets,
        'meaning':'Exact own-reference replay validates host terminal signaling; not an independent policy success or new strategy.'}
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    assert delta<1e-9 and host.actions==5
    assert packets[-1]['rollout_finished'] and packets[-1]['stop_reason']=='runtime_safety_stop'
    assert packets[-1]['backend_stop_reason']=='diagnostic_stability_stop'
    assert all(not x['rollout_finished'] for x in packets[:-1])


if __name__=='__main__':main()
