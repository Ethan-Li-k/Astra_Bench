"""Host-only mechanical audit of exact Variant1; independent RGB review still required."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from rsi.simple_grasp_mp import ENV,CONTRACT,RetainedGraspEvaluator
from tools.audit_simple_campaigns import episode_status

def review(episode):
    episode=Path(episode)
    result=json.loads((episode/'result.json').read_text())
    scene=json.loads((episode/'video/scene_setup.json').read_text())
    if scene.get('env_id')!=ENV or result.get('completion_contract')!=CONTRACT or scene.get('completion_contract')!=CONTRACT:
        raise ValueError('Exact task/completion contract mismatch')
    if not episode_status(episode)['host_success_complete']:
        raise ValueError('Complete successful actor terminal/skill update required')
    reset=scene['reset_provenance']['reset_id']
    evaluator=RetainedGraspEvaluator();evaluator.reset_history(reset)
    count=0;last_time=None;last_phase=None
    trace=episode/'video/robot_trace.jsonl'
    for line in trace.read_text().splitlines():
        row=json.loads(line);phase=row.get('host_render_state',{}).get('placement_completion_host_only')
        if phase is None:
            if count:raise ValueError('Missing completion sample after control began')
            continue  # Recorded reset/preparation/standing precede evaluator.reset().
        sample=phase.get('sample')
        if (phase.get('contract')!=CONTRACT['id'] or phase.get('reset_id')!=reset
                or not isinstance(sample,dict) or sample.get('time')!=row.get('sim_s')):
            raise ValueError('Sample contract/reset/time mismatch')
        if last_time is not None and abs(sample['time']-last_time-.02)>1e-7:
            raise ValueError('Missing, duplicate or reordered physics sample')
        evaluator.update_sample(sample,phase.get('error'))
        if evaluator.outcome(None)!=phase.get('outcome'):
            raise ValueError('Recorded gate differs from replay')
        last_time=sample['time'];last_phase=phase;count+=1
    if not count or evaluator.outcome(None)!='success' or last_phase!=result.get('completion_host_state'):
        raise ValueError('Final complete retained hold does not match result')
    video=episode/'video/episode.mp4'
    media=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=nb_frames,duration','-of','json',str(video)]))
    streams=media.get('streams',[])
    if len(streams)!=1 or int(streams[0].get('nb_frames','0'))<2 or float(streams[0].get('duration',0))<=0:
        raise ValueError('Sealed video frames required')
    return dict(mechanical_gate_passed=True,actor_access=False,env_id=ENV,reset_id=reset,
        completion_contract=CONTRACT['id'],physics_samples=count,final_hold=evaluator.host_audit_state(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [trace,video,episode/'result.json']},
        independent_rgb_review_required=True,audited_task_success=None,
        limitation='This replay checks existing host measurements, not independent visual grasp quality; supervisor must review synchronized final RGB/hold and preserve feedback tier before writing success_review.json.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--episode',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:receipt=review(a.episode)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as e:
        receipt=dict(mechanical_gate_passed=False,actor_access=False,error=type(e).__name__+': '+str(e),audited_task_success=False)
    with a.output.open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt));return not receipt['mechanical_gate_passed']
if __name__=='__main__':raise SystemExit(main())
