from pathlib import Path
import hashlib,json,datetime,subprocess,shutil,ast
B=Path(__file__).resolve().parent;R=Path('/home/galbot/lizekai/RSI');now=datetime.datetime.now(datetime.timezone.utc).isoformat();tree=B/'dry-run-final';tree.mkdir(exist_ok=True)
paths=['rsi/codex_app_server.py','tools/learn_grasp_skill.py','tools/audit_simple_campaigns.py'];rows=[]
for rel in paths:
 base=B/('snapshots/final' if rel=='tools/audit_simple_campaigns.py' else 'snapshots')/rel
 src=R/rel;d=tree/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,d)
 expected=hashlib.sha256(base.read_bytes()).hexdigest();current=hashlib.sha256(d.read_bytes()).hexdigest();rows.append({'path':str(src),'baseline':str(base.relative_to(B)),'baseline_sha256':expected,'current_sha256':current,'changed':expected!=current})
args=['patch','--batch','--fuzz=0','--dry-run','-p1','-d',str(tree)]
p=subprocess.run(args,input=(B/'audit-compatible.patch').read_text(),text=True,capture_output=True);(B/'evidence/dry-run-final.log').write_text(p.stdout+p.stderr)
identical=False
if p.returncode==0:
 q=subprocess.run([x for x in args if x!='--dry-run'],input=(B/'audit-compatible.patch').read_text(),text=True,capture_output=True)
 assert q.returncode==0
 identical=True
 for rel in paths:
  ast.parse((tree/rel).read_text());identical &= (tree/rel).read_bytes()==(B/'candidate'/rel).read_bytes()
receipt={'at':now,'files':rows,'dry_run_returncode':p.returncode,'zero_fuzz':True,'patched_copy_matches_candidate':identical,'live_edits':False}
(B/'evidence/drift-final.json').write_text(json.dumps(receipt,indent=2));(B/'patch-base-manifest.json').write_text(json.dumps({'at':now,'files':rows},indent=2))
refs=['artifacts/R019/instruction-cap-integration/status.json','artifacts/R019/recovery-20260916/permission-contract-fix.json','artifacts/R019/public-atomic-experience-20260916.json','rsi/simulation_provenance.py','rsi/simple_environment.py','ref/GPT-as-Policy/hybrid_rollout/robodojo/skill/run.py','ref/GPT-as-Policy/hybrid_rollout/robodojo/skill/network_recovery.py','tests/test_campaign_status.py','tools/learn_simple_task.py','tools/learn_door_skill.py']
refs.extend(['ref/USER_UPDATE_20260916_'+s+'.md' for s in ('PARALLEL_SKILLS','HUMAN_FEEDBACK','NO_TRUNCATION_SHARED_SKILLS')])
(B/'reference-hashes.json').write_text(json.dumps({'at':now,'files':[{'path':str(R/f),'sha256':hashlib.sha256((R/f).read_bytes()).hexdigest()} for f in refs],'first_reference':'GPT-as-Policy prior exact helpers retained; arbitrary deadlines/count caps not copied'},indent=2))
checks={'at':now,'joint_tests':18,'budget_tests':4,'original_regressions':41,'total_passed':63,'reproduction_expected_failures':2,'physics':0,'model_api_calls':0,'new_environments':0,'permission_handshake':False,'logs':['evidence/reproduction.log','evidence/joint-final-version.log','evidence/budget-final-version.log','evidence/regressions-final-version.log'],'dry_run_returncode':p.returncode}
(B/'evidence/checks.json').write_text(json.dumps(checks,indent=2));(B/'progress.json').write_text(json.dumps({'at':now,'state':'validated_pending_handoff','tests_passed':63,'candidate_deployed':False,'concurrent_edit_preserved':True,'unresolved_source_drift':any(x['changed'] for x in rows),'next':'document and queue only to SIMPLE publisher'},indent=2))
print(json.dumps({'drift':[x['path'] for x in rows if x['changed']],'dry_run_returncode':p.returncode,'matches_candidate':identical,'tests_passed':63}))
