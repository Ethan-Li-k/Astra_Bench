"""Incremental status ledger; zero-action records and diagnostics earn no credit."""
import argparse
import datetime
import json
from pathlib import Path


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
    native_success=bool(result and result.get('success') and result.get('native_outcome')=='success'
                        and actions>0 and full_turn and revision and not result.get('error'))
    review_path=episode/'success_review.json'
    review=json.loads(review_path.read_text()) if review_path.exists() else {}
    scene_path=episode/'video/scene_setup.json'
    scene=json.loads(scene_path.read_text()) if scene_path.exists() else {}
    return {'episode_id':episode.name,'state':'finished' if result is not None else 'running',
        'physical_attempt':actions>0,'actions':actions,'full_turn_completed':full_turn,
        'skill_updated':revision,'native_success_complete':native_success,
        'audited_task_success':native_success and review.get('audited_task_success') is True,
        'native_outcome':result.get('native_outcome') if result else (history[-1].get('native_outcome') if history else 'not_started'),
        'error':result.get('error') if result else None,
        'frame_collision_revision':scene.get('frame_collision_override',{}).get('id','original'),
        'reset_id':scene.get('reset_provenance',{}).get('reset_id'),
        'sim_s':result.get('sim_s') if result else None,
        'video':str(episode/'video/episode.mp4'),'video_exists':(episode/'video/episode.mp4').is_file(),
        'result_path':str(result_path) if result else None,
        'failure_review_exists':(episode/'failure_review.json').is_file() or (episode/'infrastructure_review.json').is_file()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('artifacts/R019'))
    args=p.parse_args(); campaigns=[]
    mapping={'door-campaign':'SIMPLE asset003 push-open variant',
             'apple-campaign':'simple/G1WholebodyPickAndPlaceAppleTeleop-v0',
             'faucet-campaign':'simple/G1WholebodyOpenFaucetTeleop-v0',
             'bendpick-campaign':'simple/G1WholebodyBendPickTeleop-v0'}
    for folder in sorted(args.root.glob('*-campaign')):
        episodes=[episode_status(e) for e in sorted(folder.glob('episode-*')) if e.is_dir()]
        campaigns.append({'campaign':str(folder),'task':mapping.get(folder.name,'unmapped'),
            'required_successes':10 if folder.name=='door-campaign' else 1,
            'physical_attempts':sum(e['physical_attempt'] for e in episodes),
            'finished_physical_attempts':sum(e['physical_attempt'] and e['state']=='finished' for e in episodes),
            'zero_action_finished_records':sum(not e['physical_attempt'] and e['state']=='finished' for e in episodes),
            'complete_native_successes':sum(e['native_success_complete'] for e in episodes),
            'audited_task_successes':sum(e['audited_task_success'] for e in episodes),'episodes':episodes})
    report={'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'all_goals_complete':False,'unresolved_scope':'All 91 registered entries remain in task-inventory and task-compatibility reports; unaudited or unattempted tasks are not treated as complete.',
        'diagnostics_and_replays_counted':False,'campaigns':campaigns}
    (args.root/'campaign_audit.json').write_text(json.dumps(report,indent=2))
    for c in campaigns:print(json.dumps({k:v for k,v in c.items() if k!='episodes'}))


if __name__=='__main__':main()
