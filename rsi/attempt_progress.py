"""Per-task progress telemetry at completed tool boundaries; never a model timer."""
import json,time
from pathlib import Path
from rsi.actor_transport import atomic

def configuration(env_id,spec):
    return {'id':'per-task-reward-progress-v1','env_id':env_id,
        'reward_model':{'id':(spec.get('completion_contract') or {}).get('id','native-task-criterion'),
            'task_success':1,'otherwise':0,'raw_native_reward':'host-only diagnostic; not task completion'},
        'progress_model':{'id':(spec.get('progress_contract') or {}).get('id','public-stage-and-command-tracking-v1'),
            'advisory_only': bool(spec.get('native_terminal_contract')),
            'stage_progress_contract':spec.get('stage_progress_contract'),'grasp_gate_required':(spec.get('progress_contract') or {}).get('grasp_gate_required',True),'stage_order':(spec.get('progress_contract') or {}).get('stage_order',[]),'phases':spec.get('phase_guidance') or ['approach','open_enclosure','closure','probe_lift','separate_hold'],'required_completion':spec['completion'],
            'stagnation_check':'completed_tool_boundary_only','inference_timeout':None,
            'stage_claims_are_not_verified_acquisition':True,'failure_evidence_required':True}}


def record(host,claim=None):
    cfg=getattr(host,'attempt_progress_config',None)
    if not cfg or host.backend is None:return
    now=time.time();status=host.backend.status();outcome=host.harness.evaluator.outcome(host.backend)
    row={'updated_at':now,'env_id':cfg['env_id'],'actions':host.actions,'sim_s':float(host.backend.data.time),
        'current_stage':claim.get('currently_attempting') if claim else None,
        'actor_claim':claim,'claim_not_audit':True,'stage_verification':'actor_claim_only; configured terminal is independently checked by existing evaluator','command_status':status.get('status'),
        'tracking_error_m':status.get('actual_error_m'),'reward':int(outcome=='success'),
        'raw_native_reward_host_only':getattr(host.backend,'_native_task_reward',None),
        'outcome':outcome,'finished':host.finished,'stop_reason':host.stop_reason,
        'reward_model':cfg['reward_model'],'progress_model':cfg['progress_model']}
    prior=Path(host.output)/'task-progress.json'
    if prior.exists() and row['current_stage'] is None:row['current_stage']=json.loads(prior.read_text()).get('current_stage')
    with (Path(host.output)/'task-progress-history.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    atomic(prior,row)


def admit_claim(host,claim):
    if not getattr(host,'attempt_progress_config',None) or not claim:return
    config=host.attempt_progress_config['progress_model']
    if config.get('advisory_only'):
        return
    if not config.get('grasp_gate_required',True):
        order=config.get('stage_order',[])
        stage=claim['currently_attempting']
        if stage not in order:raise ValueError('Use this task stage_order: '+', '.join(order))
        return
    completed=set(claim['verified_completed'])
    required={'closure':'open_enclosure','probe_lift':'closure','separate_hold':'probe_lift',
              'loaded_travel':'separate_hold','hands_clear_supported':'release'}
    prerequisite=required.get(claim['currently_attempting'])
    if prerequisite and prerequisite not in completed:
        raise ValueError('Progress prerequisite claim missing: '+prerequisite+' before '+claim['currently_attempting']+'; no physical action executed')
