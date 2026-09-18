"""Fresh breadth rounds and evidenced terminal attempts; no inference deadline."""
import json,subprocess
from pathlib import Path

def read(path,default=None):
    return json.loads(path.read_text()) if path.exists() else default


def classify(episode,started_at,plan_id='simple-60x5-24h-20260917'):
    e=Path(episode);result=read(e/'result.json');registration=read(e/'protocol-registration.json',{})
    if result is None:return {'complete':False,'state':'active','reason':'No terminal result'}
    if (e/'user_stop.json').exists() or result.get('error') or result.get('actions',0)<1:
        return {'complete':False,'state':'excluded','reason':'Infrastructure/user interruption or no physical action'}
    reset=read(e/'reset-receipt.json',{})
    if (reset.get('recorded_at',0)<started_at or registration.get('plan_id')!=plan_id
            or registration.get('task_id')!=reset.get('env_id') or not registration.get('episode')
            or Path(registration['episode']).resolve()!=e.resolve()):
        return {'complete':False,'state':'excluded','reason':'Outside new plan'}
    obs=read(e/'rollout/episode/observations/0000/observation.json',{})
    if not obs.get('reset_id') or not list((e/'rollout/episode').glob('execution*.json')):
        return {'complete':False,'state':'excluded','reason':'Fresh reset/action evidence absent'}
    if obs['reset_id']!=reset.get('reset_id'):
        return {'complete':False,'state':'excluded','reason':'Reset identity mismatch'}
    from tools.audit_simple_campaigns import turn_completeness
    terminal_ok, terminal_reason=turn_completeness(e,result)
    if not terminal_ok:
        return {'complete':False,'state':'pending_evidence','reason':'Final model/tool ACK absent: '+terminal_reason}
    video=e/'video/episode.mp4'
    if not video.exists():return {'complete':False,'state':'pending_evidence','reason':'Video not sealed'}
    check=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(video)],capture_output=True,text=True)
    if check.returncode or float(json.loads(check.stdout).get('format',{}).get('duration',0))<=0:
        return {'complete':False,'state':'pending_evidence','reason':'Video seal invalid'}
    binding=result.get('curriculum_contract')
    if binding:
        from rsi.curriculum import verify_contract
        try:verify_contract(binding)
        except (KeyError, ValueError):return {'complete':False,'state':'excluded','reason':'Changed curriculum contract'}
        if binding['goal_scope']=='curriculum_stage' and result.get('configured_goal_success'):
            return {'complete':False,'curriculum_complete':bool(result.get('skill_updated') and result.get('configured_goal_success')),
                'curriculum_success':bool(result.get('curriculum_success')),'audited_curriculum_success':False,
                'curriculum_level':binding['level'],'curriculum_spec_sha256':binding['spec_sha256'],
                'state':'pending_curriculum_review','reason':'Stage evidence; no full-task or official credit',
                'success':False,'configured_success':False,'audited_success':False,
                'reset_id':obs['reset_id'],'actions':result['actions'],'stop_reason':result.get('stop_reason'),
                'video':str(video),'formal_credit':False}
    reason=result.get('stop_reason');success=result.get('success') is True
    substantive=False;explanation=None
    if success:substantive=True;explanation='Configured task terminal; independent success audit separately retained'
    elif reason in ('actor_learning_deferral','progress_actor_stall'):
        p=e/'rollout/policy_stall.jsonl';stalls=[json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
        if len(stalls)>=2:
            first,last=stalls[0],stalls[-1];changed=last.get('actions_so_far',0)>first.get('actions_so_far',0)
            paths=[Path(x) for x in last.get('evidence_paths',[])];hypothesis=bool(first.get('next_hypothesis','').strip())
            executions=[read(p) for p in sorted((e/'rollout/episode').glob('execution*.json'))]
            corrected=executions[first.get('actions_so_far',0):last.get('actions_so_far',0)]
            previous={json.dumps(x['response']['trajectory'],sort_keys=True) for x in executions[:first.get('actions_so_far',0)]}
            novel=any(json.dumps(x['response']['trajectory'],sort_keys=True) not in previous for x in corrected)
            substantive=changed and novel and hypothesis and bool(last.get('reason','').strip()) and bool(paths) and all(p.is_file() and e.resolve() in p.resolve().parents for p in paths) and result.get('skill_updated') is True
            explanation=last.get('reason') if substantive else None
        elif stalls and stalls[-1].get('disposition')=='defer_outside_workspace':
            last=stalls[-1];substantive=False  # outside-workspace claim requires separate terminal review
            explanation=last.get('reason')
    elif reason in ('native_failure','task_failure','progress_stall') or (reason or '').startswith('diagnostic_stability'):
        substantive=False;explanation='Candidate physical failure requires its terminal evidence review: '+reason
    row={'complete':bool(substantive),'state':'complete' if substantive else 'needs_failure_review',
        'reason':explanation or 'No sufficiently explained corrected failure; do not count a bare deferral',
        'success':success,'configured_success':success,'audited_success':False,'reset_id':obs['reset_id'],'actions':result['actions'],'stop_reason':reason,'video':str(video),'formal_credit':False}
    if binding and binding['goal_scope']=='curriculum_stage':
        row.update(complete=False,curriculum_complete=bool(substantive),curriculum_success=False,
            audited_curriculum_success=False,curriculum_level=binding['level'],
            curriculum_spec_sha256=binding['spec_sha256'],state='pending_curriculum_review',
            configured_success=False,audited_success=False,success=False)
    return row


def select_next(tasks,active,blocked,goal=5):
    eligible=[r for r in tasks if r['ready'] and r['env_id'] not in active|blocked and r['complete_attempts']<goal]
    return min(eligible,key=lambda r:(r['complete_attempts'],r['rank'])) if eligible else None
