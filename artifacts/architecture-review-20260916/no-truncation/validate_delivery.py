import hashlib,json,subprocess,shutil,ast,datetime
from pathlib import Path
B=Path(__file__).resolve().parent;R=Path('/home/galbot/lizekai/RSI');tree=B/'compatibility-tree';tree.mkdir(exist_ok=True)
prior=B.parent/'memory-priority/combined-compatible.patch';ours=B/'continuity.patch'
paths=['rsi/codex_app_server.py','rsi/skill_learning.py','tools/audit_simple_campaigns.py','tools/learn_grasp_skill.py','tools/learn_simple_task.py','tools/learn_door_skill.py']
original=[]
for name in paths:
 p=R/name;d=tree/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
 original.append({'path':str(p),'sha256':hashlib.sha256(d.read_bytes()).hexdigest()})
checks=[]
for patch in (prior,ours):
 args=['patch','--batch','--fuzz=0','--dry-run','-p1','-d',str(tree)]
 dry=subprocess.run(args,input=patch.read_text(),text=True,capture_output=True)
 checks.append({'patch':str(patch),'sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'dry_run_returncode':dry.returncode,'output':dry.stdout+dry.stderr})
 if dry.returncode:break
 apply=subprocess.run([x for x in args if x!='--dry-run'],input=patch.read_text(),text=True,capture_output=True)
 assert apply.returncode==0,apply.stdout+apply.stderr
 for name in paths:ast.parse((tree/name).read_text())
snapshot=json.loads((B/'snapshot-manifest.json').read_text())
drift=[{'path':r['path'],'snapshot_sha256':r['sha256'],'current_sha256':hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()} for r in snapshot['files']]
for r in drift:r['changed']=r['snapshot_sha256']!=r['current_sha256']
(B/'evidence/compatibility.json').write_text(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'live_baselines':original,'checks':checks,'all_passed':len(checks)==2 and all(x['dry_run_returncode']==0 for x in checks),'live_edits':False},indent=2))
(B/'evidence/snapshot-drift.json').write_text(json.dumps(drift,indent=2))
print(json.dumps({'compatibility':checks,'drift':drift},indent=2))
