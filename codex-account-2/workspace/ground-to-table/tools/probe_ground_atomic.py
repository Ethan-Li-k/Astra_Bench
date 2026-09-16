"""Physical three-second boundary verification, no model actor/task credit."""
import json
from pathlib import Path
from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.four_point import FourPointPose
from rsi.episode_video import EpisodeVideo


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=ROOT/'artifacts/continuous-atomic-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(continuous=True);e=GroundEvaluator(out/'host_audit');e.reset(b)
    v=EpisodeVideo(b,out/'video',label='DEVELOPMENT 3s transaction boundary | NO TASK CREDIT')
    try:
        # Reach the failure's clock value by real physics, never by setting time.
        for _ in range(472):
            b.tick();e.update(b);v.record_tick('development_no_task_credit')
        assert not b.reason
        obs=b.observe();pose=FourPointPose.from_mapping(obs['four_point_world'])
        rows=[{'target':pose.copy(),'duration_s':.6,
            'active':{'position':[],'orientation':[]},'grippers':{'left':0.,'right':0.}}
            for _ in range(5)]
        start=float(b.data.time)
        receipt=b.move_four_point_sequence(obs['observation_id'],'exact-three-seconds',rows)
        b.set_grippers(0.,0.,duration=receipt['duration_s'])
        while b.active and not b.reason:
            b.tick();e.update(b);v.record_tick('development_no_task_credit')
        result={'backend':'MuJoCo','physics_start_s':start,'duration_s':receipt['duration_s'],
            'elapsed_s':float(b.data.time)-start,'final_status':receipt['status'],
            'stopped':b.reason,'pending_reference':b.active,
            'new_task_successes':0,'actor_input':False,'gpt_calls':0,
            'audit':e.audit.result()}
        (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
        assert not b.reason and not b.active and receipt['duration_s']==3.
    finally:v.close();e.close()

if __name__=='__main__':main()
