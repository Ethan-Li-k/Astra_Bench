from pathlib import Path
import ast,datetime,hashlib,json,shutil
R=Path(__file__).resolve().parent;RSI=R.parents[2];A=RSI/'artifacts/R019'
manifest=json.loads((R/'source-hashes.json').read_text())
paths=[RSI/'tools/audit_simple_campaigns.py',RSI/'ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md',RSI/'ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/eef_control.md',RSI/'ref/GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/context/teacher_context.md']
taskdir=Path('/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/src/simple/tasks')
paths += [taskdir/name for name in ('g1_wholebody_handover_teleop.py','g1_wholebody_bend_handover_teleop.py','g1_wholebody_teleop_efficiency_tasks.py','g1_tabletop_grasp_mp.py')]
for path in paths:
 rel=str(path.relative_to(RSI)) if path.is_relative_to(RSI) else 'external-task-definitions/'+path.name
 dst=R/'snapshots'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dst)
 manifest[str(path)]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'snapshot':str(dst.relative_to(R))}
(R/'source-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Native criteria are host-review material; only explicit task instructions go to actors.
criteria=json.loads((R/'snapshots/artifacts/R019/native-task-criteria.json').read_text())
selected=[x for x in criteria['tasks'] if any(k in x['env_id'] for k in ('Handover','MobilePick'))]
(R/'review-evidence/handover-mobile-native-criteria.json').write_text(json.dumps({'actor_access':False,'tasks':selected},indent=2)+'\n')
line_refs={}
for path in paths:
 if path.suffix=='.py':
  tree=ast.parse(path.read_text());line_refs[str(path)]={}
  for c in tree.body:
   if isinstance(c,ast.ClassDef) and ('Handover' in c.name or 'MobilePick' in c.name):
    line_refs[str(path)][c.name]={n.name:n.lineno for n in c.body if isinstance(n,ast.FunctionDef) and n.name in ('compute_reward','check_success','update_handover_progress','check_wether_handover_success')}
(R/'review-evidence/criterion-line-index.json').write_text(json.dumps(line_refs,indent=2)+'\n')
status=json.loads((R/'review-evidence/task-status.json').read_text())
for fam,row in status['tasks'].items():
 for success in row['audited_successes']:
  audit=json.loads(Path(success['review']).read_text())
  success['audit_human_feedback_used']=audit.get('human_feedback_used','not_recorded')
 if not row['latest_result_exists']:
  p=Path(row['campaign'])/row['latest_episode']/'rollout/history.jsonl'
  records=[json.loads(s) for s in p.read_text().splitlines()];acts=[s for s in records if s.get('tool')=='scalebfm_act']
  row['last_completed_public_action_count']=len(acts);row['history_mtime_utc']=datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()
  row['last_public_native_outcome']=acts[-1].get('native_outcome') if acts else 'not_started'
status['at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(R/'review-evidence/task-status.json').write_text(json.dumps(status,indent=2)+'\n')
# Native source hashes from the inventory are compared, not assumed current.
checks=[]
for row in selected:
 path=Path(row['source']);checks.append({'env_id':row['env_id'],'recorded_hash':row['source_sha256'],'current_hash':hashlib.sha256(path.read_bytes()).hexdigest()})
(R/'checks/native-source-hashes.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps({'line_refs':line_refs,'active_snapshot':{k:{x:v.get(x) for x in ['latest_episode','last_completed_public_action_count','history_mtime_utc']} for k,v in status['tasks'].items() if not v['latest_result_exists']}},indent=2))
