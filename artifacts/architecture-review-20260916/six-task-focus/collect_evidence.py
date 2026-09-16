"""Bounded read-only extraction; no simulator imports or API calls."""
from pathlib import Path
import ast,collections,datetime,hashlib,json,shutil
R=Path(__file__).resolve().parent; RSI=R.parents[2]; A=RSI/'artifacts/R019'; (R/'review-evidence').mkdir(exist_ok=True);(R/'snapshots').mkdir(exist_ok=True)
files=['ref/USER_UPDATE_20260916_SIX_TASK_FOCUS.md','artifacts/R019/task-inventory.json','artifacts/R019/native-task-criteria.json','artifacts/R019/PROGRESS.md','artifacts/R018/audit_summary.json','artifacts/architecture-review-20260916/status-evidence.json','artifacts/R019/door-campaign/ten-success-milestone.json','artifacts/R019/robot-stability-integration-20260916/status.json','rsi/skill_learning.py','tools/learn_grasp_skill.py','rsi/codex_app_server.py','tools/learn_simple_task.py','skills/loco-manip-simple/SKILL.md']
for fam,ep in [('xmovepick',3),('xmovepicksim',1),('bendpick',6),('xmovebendpick',1),('bendpicksim',1)]:
 for name in ('result.json','success_review.json','failure_review.json','SKILL.md','policy_instruction_budget.json'):
  rel=f'artifacts/R019/{fam}-campaign/episode-{ep:04d}/{name}'
  if (RSI/rel).exists():files.append(rel)
 for name in ('SKILL.md',f'memory/versions/{ep:04d}.md','memory/experience.jsonl'):
  rel=f'artifacts/R019/{fam}-campaign/{name}'
  if (RSI/rel).exists():files.append(rel)
for file in ['simple-xmove-pick','simple-xmove-pick-sim-to-real','simple-bend-pick','simple-bend-pick-sim-to-real','simple-xmove-bend-pick','simple-mobile-pick-place-cheezit']:
 files.append('ref/tasks/'+file+'.json')
manifest={}
for rel in files:
 p=RSI/rel;dest=R/'snapshots'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 manifest[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'snapshot':str(dest.relative_to(R))}
(R/'source-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
metrics={}
for fam in ('xmovebendpick','bendpicksim'):
 p=A/(fam+'-campaign')/'episode-0001/rollout/history.jsonl';rows=[json.loads(s) for s in p.read_text().splitlines()];actions=[r for r in rows if r['tool']=='scalebfm_act']
 status=collections.Counter(e['status'] for r in actions for e in (r.get('execution') or []))
 closed=sum(any(any(v>0 for v in w['grippers'].values()) for w in r['arguments']['response']['trajectory']) for r in actions)
 metrics[fam]={'episode':'episode-0001','actions':len(actions),'receipt_status_counts':dict(status),'actions_with_positive_closure_command':closed,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'classification':'physical_budget; phase-specific evidence, not model cutoff or repeated independent grasp failures'}
(R/'review-evidence/phase-timeouts.json').write_text(json.dumps(metrics,indent=2)+'\n')
status={}
for fam in ('xmovepick','xmovepicksim','bendpick','bendpicksim','xmovebendpick','mobilecheezit'):
 campaign=A/(fam+'-campaign');episodes=sorted(campaign.glob('episode-*'));current=episodes[-1];successes=[];closed=0
 for ep in episodes:
  if (ep/'result.json').exists():closed+=1
  if (ep/'success_review.json').exists():
   review=json.loads((ep/'success_review.json').read_text())
   if review.get('audited_task_success'):
    result=json.loads((ep/'result.json').read_text());successes.append({'episode':ep.name,'human_feedback_used':result.get('human_feedback_used','historically_not_recorded'),
     'result':str(ep/'result.json'),'review':str(ep/'success_review.json'),'skill_sha256':result.get('starting_skill_sha256'),
     'reset_id':review.get('reset',{}).get('reset_id'),'video':result.get('video'),'actions':result.get('actions')})
 public=json.loads((current/'public-progress.json').read_text()) if (current/'public-progress.json').exists() else None
 if public:(R/'review-evidence'/f'{fam}-progress.json').write_text(json.dumps(public,indent=2)+'\n')
 status[fam]={'campaign':str(campaign),'registered_episode_directories':len(episodes),'result_files':closed,'audited_successes':successes,'latest_episode':current.name,'latest_result_exists':(current/'result.json').exists(),'public_progress_snapshot':public}
(R/'review-evidence/task-status.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tasks':status},indent=2)+'\n')
print(json.dumps({'phase_metrics':metrics,'task_counts':{k:{'audited_successes':len(v['audited_successes']),'latest':v['latest_episode'],'ended':v['latest_result_exists']} for k,v in status.items()}},indent=2))
