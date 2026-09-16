"""Host-only recorded counterexamples plus fresh-backend integration, no actor."""
import argparse
import json
from pathlib import Path

from rsi.simple_placement import SimplePlacementEvaluator, PLACEMENT_CONTRACT


def counterexamples():
    results=[]
    for n in (1,2):
        p=Path(f'artifacts/R019/boxplace-campaign/episode-{n:04d}')
        rows=[json.loads(x) for x in (p/'video/robot_trace.jsonl').read_text().splitlines()]
        initial=rows[0]['host_render_state']['qpos_by_joint']['cracker_box_joint'][2]
        gate=SimplePlacementEvaluator()
        gate._lift_since=gate._release_since=gate._gap_since=None
        gate._acquired=False;gate._outcome='in_progress'
        for row in rows:
            state=row['host_render_state'];native=state['native_task_success']
            # Favorable contact assumptions deliberately overestimate acquisition.
            # The measured height alone rules out the required acquired lift.
            gate.update_sample({'time':row['sim_s'],
                'rise_m':state['qpos_by_joint']['cracker_box_joint'][2]-initial,
                'grasped':not native,'nonhand_support':False,'robot_contact':not native,
                'container_contact':native,'other_support':False,'native_success':native})
        assert gate.outcome(None)=='in_progress' and not gate._acquired
        results.append({'episode':str(p),'raw_native_true_ticks':sum(r['host_render_state']['native_task_success'] for r in rows),
            'new_gate_outcome':gate.outcome(None),'samples':len(rows),
            'limitation':'Frozen heights/time/native flags with favorable assumed contacts; not full dynamics replay or actual-contact reconstruction.'})
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(exist_ok=True,parents=True)
    result={'counterexamples':counterexamples(),'contract':PLACEMENT_CONTRACT,
            'new_actor_attempts':0,'success_credit':0}
    from rsi.simple_environment import create_native_task_backend
    from rsi.simple_recording import simple_video
    b=create_native_task_backend(PLACEMENT_CONTRACT['scope'],seed=3)
    recorder=None
    try:
        gate=SimplePlacementEvaluator();gate.reset(b)
        b.scene_setup['diagnostic_only']=True
        b.scene_setup['completion_contract']=PLACEMENT_CONTRACT
        recorder=simple_video(b,args.output/'video',label='Placement evaluator integration | diagnostic | no actor')
        start=b.physics_action_calls
        for _ in range(25):
            b.tick();gate.update(b)
            recorder.record_tick(gate.outcome(b))
        result['integration']={'ticks':b.physics_action_calls-start,'outcome':gate.outcome(b),
            'sample':gate.host_audit_state(),'target':b.model.body(gate.target).name,
            'container':b.model.body(gate.container).name}
        assert gate.outcome(b)=='in_progress' and not b.reason
    finally:
        if recorder is not None:recorder.close()
        b.close()
    (args.output/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
