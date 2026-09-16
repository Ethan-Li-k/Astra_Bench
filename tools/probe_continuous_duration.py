"""Replay the faucet duration regression in an isolated diagnostic, without GPT."""
import argparse
from functools import partial
import json
from pathlib import Path

from rsi.evaluator import SimpleNativeEvaluator
from rsi.simple_environment import create_native_task_backend
from rsi.simple_recording import simple_video
from tools.learn_grasp_skill import LearningHost


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root=args.output.resolve();root.mkdir(exist_ok=False,parents=True)
    source=Path('artifacts/R019/faucet-campaign/episode-0005/agent/rpc_calls')
    plan={'hypothesis':'Relative duration summation avoids the 3.0000000000000018 s gripper rejection at the same clock origin.',
          'criterion':'Both saved requests complete through LearningHost, second duration exactly3s, no execution_error, backend active cleared and physical clock advances.',
          'source_requests':[str(source/'0003_request.json'),str(source/'0004_request.json')],
          'model_calls':0,'physical_attempt_credit':False,'task_success_credit':False,
          'next':'If passed, new formal resets use the fix; this replay is never counted as an autonomous attempt.'}
    (root/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    def backend_factory():
        b=create_native_task_backend('simple/G1WholebodyOpenFaucetTeleop-v0',seed=5)
        b.continuous_chunks_enabled=True
        return b
    host=LearningHost(root,None,'duration-diagnostic',0,backend_factory=backend_factory,
        evaluator_factory=SimpleNativeEvaluator,
        geometry_provider=None,
        image_capture_factory=lambda b:simple_video(b,root/'video'))
    packets=[]
    try:
        packet=host.dispatch('loco_start',{'task':'Isolated duration regression; no task-success credit.',
                                          'output_dir':str(host.rollout_root/'episode')})
        for i,request in enumerate(('0003_request.json','0004_request.json'),1):
            response=json.loads((source/request).read_text())['arguments']['response']
            packet=host.dispatch('scalebfm_act',{'observation_path':packet['observation_path'],
                'response':response,'output_dir':str(host.rollout_root/f'call_{i:04d}')})
            packets.append(packet)
            assert host.execution_error is None,host.execution_error
        durations=[x['execution'][-1]['duration_s'] for x in packets]
        assert durations[-1]==3. and host.backend.active is None
        result={'passed':True,'durations_s':durations,'sim_s':host.backend.data.time-host.episode_start_sim_s,
            'recorded_diagnostic_actions':host.actions,'active_after':host.backend.active,
            'model_calls':0,'physical_attempt_credit':False,'task_success_credit':False,
            'source':'Saved action1 and previously rejected action2; independent same-seed diagnostic, not a new learning attempt.'}
        (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:host.close()


if __name__=='__main__':main()
