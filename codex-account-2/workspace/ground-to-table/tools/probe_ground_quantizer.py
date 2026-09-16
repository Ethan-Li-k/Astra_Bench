"""Paired diagnosis: does FSQ rounding prevent a known foot lift reference?

No GPT, no task success credit, no actor-visible generated references.
Both instances settle with ORIGINAL ONNX before the one changed factor.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import mujoco
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.diagnostic_latent import DiagnosticLatentPolicy
from rsi.episode_video import EpisodeVideo
from rsi.four_point import FourPointPose,FOUR_POINT_NAMES

def run(label):
    out=ROOT/'artifacts/quantizer-foot-01'/label;out.mkdir(parents=True,exist_ok=False)
    b=create_backend()
    initial_hash=hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()+b.adapter.policy_history.tobytes()+b.adapter.action_history.tobytes()).hexdigest()
    diagnostic=DiagnosticLatentPolicy(b.adapter,'continuous' if label=='no_round' else 'torch_raw')
    original=b.adapter._run_policy
    rows=[]
    def run_policy(task):
        raw=original(task)
        alternate=diagnostic(task)
        rows.append({'time':float(b.data.time),'original_action':raw.tolist(),
                     'diagnostic_action':alternate.tolist(),'raw_code':diagnostic.raw_code.tolist(),
                     'used_code':diagnostic.used_code.tolist()})
        return alternate if label=='no_round' else raw
    b.adapter._run_policy=run_policy
    b.translation_limit_m_by_link[FOUR_POINT_NAMES[2]]=.081
    e=GroundEvaluator(out/'host_audit');e.reset(b)
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT ONLY | FSQ '+label+' | no task credit',
        extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist(),'ctrl':sim.data.ctrl.tolist()})
    try:
        o=b.observe();target=FourPointPose.from_mapping(o['four_point_world'])
        target.positions[2,2]+=.08
        b.move_four_points(o['observation_id'],'diagnostic-left-foot-up',target.to_mapping(),2.,
                          position_names=[FOUR_POINT_NAMES[2]],orientation_names=[])
        for _ in range(250):
            b.tick();e.update(b);v.record_tick('development_no_success_credit')
            if b.reason:break
        report={'label':label,'changed_inference_semantics':label=='no_round','gpt_calls':0,'new_task_successes':0,
                'initial_state_and_history_sha256':initial_hash,'parity_error':diagnostic.parity_error,
                'audit':e.audit.result(),'status':b.status(),'stop_reason':b.reason,
                'original_model_weight_unchanged':True,'backend':'MuJoCo','sim_s':float(b.data.time)-5}
        (out/'result.json').write_text(json.dumps(report,indent=2))
        (out/'model_response.json').write_text(json.dumps(rows))
        print(json.dumps({'event':'quantizer_probe_case',**report}),flush=True)
        return report
    finally:e.close();v.close()

def main():
    update=Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_bytes()
    root=ROOT/'artifacts/quantizer-foot-01';root.mkdir(parents=True,exist_ok=False)
    (root/'protocol.json').write_text(json.dumps({'hypothesis':'FSQ rounding may suppress useful leg response despite a nonzero encoded command',
        'reason_for_repeated_baseline':'Known failed foot target only provides matched control for a new inference ablation; not another blind foot reference search',
        'change':'rounding only after matched original-policy settling',
        'frozen_weights':True,'formal_policy':False,'actor_input':False,'user_update_sha256':hashlib.sha256(update).hexdigest()},indent=2))
    a=run('original');b=run('no_round')
    assert a['initial_state_and_history_sha256']==b['initial_state_and_history_sha256']
    (root/'comparison.json').write_text(json.dumps({'initial_state_and_history_match':True,'cases':[a,b]},indent=2))

if __name__=='__main__':main()
