"""Incremental status ledger; zero-action records and diagnostics earn no credit."""
import argparse
import datetime
import json
from collections import Counter
from pathlib import Path


def termination_class(result):
    if result is None:return 'running'
    if result.get('error'):return 'infrastructure_interruption'
    if result.get('success') and result.get('native_outcome')=='success':return 'native_success'
    if result.get('backend_stop_reason'):return 'runtime_safety_stop'
    reason=result.get('stop_reason')
    if reason=='policy_declared_stall':return 'policy_early_stop'
    if reason=='episode_step_budget':return 'budget_truncation'
    if reason=='policy_safety_stop':return 'policy_safety_stop_requires_review'
    if result.get('native_outcome')=='failure':return 'native_failure_unspecified'
    return 'unfinished_terminal_record'


def episode_status(episode):
    result_path=episode/'result.json'
    result=json.loads(result_path.read_text()) if result_path.is_file() else None
    history_path=episode/'rollout/history.jsonl'
    history=[json.loads(s) for s in history_path.read_text().splitlines()] if history_path.exists() else []
    actions=sum(r.get('tool')=='scalebfm_act' for r in history)
    if result is not None: actions=result.get('actions',actions)
    turns=[json.loads(p.read_text()) for p in sorted(episode.glob('turn_*.json')) if p.is_file()]
    full_turn=bool(turns and turns[-1].get('status')=='completed')
    revision=bool(result and result.get('skill_updated'))
    host_success=bool(result and result.get('success') and result.get('native_outcome')=='success'
                        and actions>0 and full_turn and revision and not result.get('error'))
    review_path=episode/'success_review.json'
    review=json.loads(review_path.read_text()) if review_path.exists() else {}
    exposure_path=episode/'human_feedback_review.json'
    exposure=json.loads(exposure_path.read_text()) if exposure_path.exists() else {}
    scene_path=episode/'video/scene_setup.json'
    scene=json.loads(scene_path.read_text()) if scene_path.exists() else {}
    contract=((result or {}).get('completion_contract') or scene.get('completion_contract') or {}).get('id',
        'door-push-contact30deg-dwell1s-standing' if episode.parent.name=='door-campaign'
        else 'native_simple_criterion')
    return {'episode_id':episode.name,'state':'finished' if result is not None else 'running',
        'physical_attempt':actions>0,'actions':actions,'full_turn_completed':full_turn,
        'skill_updated':revision,'host_success_complete':host_success,
        'completion_contract':contract,
        'task_audit_status':('passed' if review.get('audited_task_success') is True
            else 'rejected' if review.get('audited_task_success') is False else 'unknown'),
        'audited_task_success':host_success and review.get('audited_task_success') is True,
        'native_outcome':result.get('native_outcome') if result else (history[-1].get('native_outcome') if history else 'not_started'),
        'error':result.get('error') if result else None,
        'termination_class':('native_success_rejected_by_task_audit'
            if host_success and review.get('audited_task_success') is False
            else 'verified_variant_success' if host_success and contract!='native_simple_criterion'
            else termination_class(result)),
        'human_feedback_used':bool((result and result.get('human_feedback_used',False))
                                   or exposure.get('human_feedback_used',False)),
        'frame_collision_revision':scene.get('frame_collision_override',{}).get('id','original'),
        'reset_id':scene.get('reset_provenance',{}).get('reset_id'),
        'sim_s':result.get('sim_s') if result else None,
        'video':str(episode/'video/episode.mp4'),'video_exists':(episode/'video/episode.mp4').is_file(),
        'result_path':str(result_path) if result else None,
        'failure_review_exists':(episode/'failure_review.json').is_file() or (episode/'infrastructure_review.json').is_file()}


def memory_success_review(campaign, completion_contract):
    """Host-only live projection; the supervisor's success_review.json is authoritative.

    Re-read on each memory request, including reviews published after skill_update.
    No copied audit ledger, actor file access, or historical experience rewrite.
    """
    campaign = Path(campaign)
    def lookup(episode_id):
        if (not isinstance(episode_id, str) or not episode_id.startswith('episode-')
                or not episode_id.removeprefix('episode-').isdigit()):
            return {}
        try:
            status = episode_status(campaign / episode_id)
        except (FileNotFoundError, json.JSONDecodeError):
            # A supervisor may still be publishing its review; do not pin on a
            # partial/missing read and do not cache a previous approval.
            return {}
        return {'task_audit_status': status['task_audit_status'],
                'completion_contract_matches': (isinstance(completion_contract, str)
                    and bool(completion_contract) and status['completion_contract'] == completion_contract),
                'audited_task_success': status['audited_task_success']}
    return lookup


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('artifacts/R019'))
    args=p.parse_args(); campaigns=[]
    mapping={'door-campaign':'SIMPLE asset003 push-open variant',
             'apple-campaign':'simple/G1WholebodyPickAndPlaceAppleTeleop-v0',
             'faucet-campaign':'simple/G1WholebodyOpenFaucetTeleop-v0',
             'boxplace-campaign':'simple/G1WholebodyBendPickAndPlaceTeleop-v0',
             'bendpick-campaign':'simple/G1WholebodyBendPickTeleop-v0'}
    for folder in sorted(args.root.glob('*-campaign')):
        episodes=[episode_status(e) for e in sorted(folder.glob('episode-*')) if e.is_dir()]
        campaigns.append({'campaign':str(folder),'task':mapping.get(folder.name,'unmapped'),
            'required_successes':10 if folder.name=='door-campaign' else 1,
            'physical_attempts':sum(e['physical_attempt'] for e in episodes),
            'finished_physical_attempts':sum(e['physical_attempt'] and e['state']=='finished' for e in episodes),
            'zero_action_finished_records':sum(not e['physical_attempt'] and e['state']=='finished' for e in episodes),
            'complete_host_successes':sum(e['host_success_complete'] for e in episodes),
            'complete_native_evaluator_successes':sum(e['host_success_complete'] and
                e['completion_contract']=='native_simple_criterion' for e in episodes),
            'audited_task_successes':sum(e['audited_task_success'] for e in episodes),'episodes':episodes})
        campaigns[-1]['termination_counts']=dict(Counter(e['termination_class'] for e in episodes))
        campaigns[-1]['autonomous_audited_successes']=sum(
            e['audited_task_success'] and not e['human_feedback_used'] for e in episodes)
        campaigns[-1]['human_assisted_audited_successes']=sum(
            e['audited_task_success'] and e['human_feedback_used'] for e in episodes)
        campaigns[-1]['audited_successes_by_contract']=dict(Counter(
            e['completion_contract'] for e in episodes if e['audited_task_success']))
    report={'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'all_goals_complete':False,'unresolved_scope':'All 91 registered entries remain in task-inventory and task-compatibility reports; unaudited or unattempted tasks are not treated as complete.',
        'diagnostics_and_replays_counted':False,'campaigns':campaigns}
    (args.root/'campaign_audit.json').write_text(json.dumps(report,indent=2))
    for c in campaigns:print(json.dumps({k:v for k,v in c.items() if k!='episodes'}))


if __name__=='__main__':main()
