"""Bounded R019 audited-success index; audit payload never enters public output."""
from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path('/home/galbot/lizekai/RSI');HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.audit_simple_campaigns import episode_status
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((HERE/'snapshots/artifacts/R019/campaign_audit.json').read_text())
public=HERE/'draft/public';public.mkdir(parents=True,exist_ok=True)
atomic=json.loads((HERE/'snapshots/artifacts/R019/public-atomic-experience-20260916.json').read_text())
old={}
for item in atomic['candidates']:
 path=item.get('public_rollout') or item.get('source_episode','')
 if path:old[str(Path(path).parent) if path.endswith('/rollout') else path]=item
control={'controller':'model_38000 UMI-4','pd_profile':'checkpoint','hand':'native Dex3 mesh','coordinates':'named world metres; unit wxyz','timing':'50Hz tracker/200Hz MuJoCo; physics paused for reasoning'}
phases={'door':['approach','support','articulated_contact'],'closedoor':['approach','support','articulated_contact'],'chair':['approach','support','push'],'faucet':['support','articulated_contact'],'oven':['approach','support','articulated_contact'],'trashcan':['support','articulated_contact'],'apple':['enclosure','retention','placement'],'bendpick':['low_reach','enclosure','retention'],'boxplace':['enclosure','retention','placement'],'xmovepick':['approach','enclosure','retention'],'xmovepicksim':['approach','enclosure','retention']}
rows=[];certificates=[];excluded=[];seen=set()
for campaign in audit['campaigns']:
 cp=Path(campaign['campaign']);cp=cp if cp.is_absolute() else ROOT/cp
 journal=cp/'memory/experience.jsonl'
 memories=[json.loads(s) for s in journal.read_text().splitlines()] if journal.exists() else []
 for entry in campaign['episodes']:
  if not entry['audited_task_success']:
   if entry.get('host_success_complete'):excluded.append({'campaign':cp.name,'episode':entry['episode_id'],'reason':'native/host success without passed independent task audit'})
   continue
  ep=cp/entry['episode_id'];status=episode_status(ep)
  if not status['audited_task_success']:raise ValueError(f'Audit qualification changed: {ep}')
  reset=status['reset_id'];assert reset and reset not in seen;seen.add(reset)
  matches=[m for m in memories if m['episode_id']==ep.name];assert len(matches)==1
  m=matches[0];version=cp/'memory/versions'/f"{m['version']:04d}.md";assert version.is_file()
  relative=str(ep.relative_to(ROOT));kind=cp.name.removesuffix('-campaign');sid=kind+'-'+ep.name
  # Only existing public source text and public robot/RGB observations are referenced.
  source=old.get(relative,{})
  if kind in ('door','closedoor'):
   principle='After visible support/hand clearance checks, separate empty-hand approach from bounded panel interaction. If reach saturates, withdraw/unload and reobserve before the next measured approach; follow actual panel motion.'
   precondition='Same four-point/checkpoint PD and native hand; current moving panel and free push side identified from RGB; stable stance and complete hand clearance.'
   exclusions='No copied coordinates, pulling/latch mechanics, loaded walking, universal gait or evidence of cross-task robustness. Push-open and closing directions/terminal contracts remain distinct.'
  elif kind=='xmovepick':
   principle='After actual approach and stable reachable stance, verify open opposing enclosure, then closure, short lift and a separate visible retention hold. Use achieved wrist attitude and whole-hand clearance; changed ankle references are not a crouch/gait proof.'
   precondition='Matched side-grasp context with supplied H001004 provenance, calibrated stereo, native mesh fingers and stable support.'
   exclusions='No copied poses/closure values, loaded walking or post-terminal dwell. Human-assisted source is not autonomous evidence.'
  else:
   principle=source.get('principle');precondition=source.get('preconditions') or source.get('prerequisites');exclusions=source.get('when_not_to_use')
   assert principle and precondition and exclusions,(kind,ep)
  obsroot=ep/'rollout/episode/observations';obs=sorted(p for p in obsroot.iterdir() if p.is_dir() and p.name.isdigit())
  assert len(obs)>=2
  refs=[]
  for ob in obs[-2:]:
   for name in ['head_stereo_left.png','head_stereo_right.png']:
    f=ob/name;assert f.is_file()
    rel=Path('evidence')/sid/ob.name/name;dest=public/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    refs.append({'path':str(rel),'sha256':sha(dest),'original_public_path':str(f)})
  # Compact reviewed memory; originals are preserved externally, never rewritten.
  row={'id':sid,'status':'audited_source','env_id':campaign['task'],'source_episode':relative,
       'source_access':'Original paths are provenance only; read only frozen files explicitly listed in workspace.', 'skill_version':m['version'],'source_skill':str(version),'source_skill_sha256':sha(version),
       'phases':phases[kind],'preconditions':precondition,'action_categories':phases[kind],
       'principle':principle,'exit_evidence':source.get('visible_evidence') or source.get('result') or 'Consult the referenced public final stereo pair and phase-specific public skill; host certification is separate from what each image proves.',
       'action_range':[1,status['actions']],'range_scope':'whole successful episode, not a claim that every action is an effective atomic skill',
       'public_observation_range':[obs[-2].name,obs[-1].name],'public_evidence':refs,
       'control_contract':control,'human_feedback_used':status['human_feedback_used'],
       'human_demonstration_used':False,'feedback_source':'H001004 (preserve source tier)' if status['human_feedback_used'] else None,
       'when_not_to_use':exclusions,'unverified':'No new cross-task outcome, loaded locomotion or true handover established by this index.',
       'completion_contract':status['completion_contract']}
  row['path']='atoms/'+sid+'.json';dest=public/row['path'];dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n');rows.append(row)
  host=HERE/'host-evidence'/sid;host.mkdir(parents=True,exist_ok=True)
  for file in ['success_review.json','result.json']:
   shutil.copy2(ep/file,host/file)
  certificates.append({'id':sid,'episode':relative,'reset_id':reset,'host_status':status,'audit_sha256':sha(ep/'success_review.json'),'result_sha256':sha(ep/'result.json'),'public_atom_sha256':sha(dest)})
# Preserve relevant failure exclusions, not successful retrieval priority.
for kind,eid,phase,principle in [
 ('xmovebendpick','episode-0001',['approach','low_reach','enclosure'],'Open-hand reach/attitude/enclosure remained unresolved; never call this tested closed-grasp friction. Check achieved motion and whole-hand sweep; relocalize displaced targets.'),
 ('bendpicksim','episode-0001',['low_reach','enclosure','retention'],'Closure probes and tracking/perception changes did not establish retention. Separate reach timeout, failed acquisition and physical-budget termination.'),
 ('mobilecheezit','episode-0001',['retention','loaded_travel','placement'],'Public actions025/026 show lift/hold; changed loaded posture028/029 was followed by visible loss onto the source table. No completed loaded route or destination placement. Recheck retention after each small loaded change; support and grasp attitude are coupled.'),
 ('boxplace','episode-0003',['enclosure','placement'],'Earlier native-contact triggers were not complete pickup-transport-release. Require visible enclosure and retained lift before placement; never prioritize rejected native labels.')]:
 ep=ROOT/f'artifacts/R019/{kind}-campaign/{eid}';status=episode_status(ep);assert not status['audited_task_success']
 row={'id':kind+'-'+eid+'-counterexample','status':'counterexample','env_id':next(c['task'] for c in audit['campaigns'] if Path(c['campaign']).name==kind+'-campaign'),'source_episode':str(ep.relative_to(ROOT)),'phases':phase,'preconditions':'Same stage/mechanism and comparable native hand/controller; check current observations.','action_categories':phase,'principle':principle,'exit_evidence':'No verified retained task completion; unresolved stages remain unresolved.','action_range':[1,status['actions']],'control_contract':control,'human_feedback_used':status['human_feedback_used'],'when_not_to_use':'Not a success recipe, MP score or proof of a common cause across unrelated attempts.','public_evidence':[{'original_public_path':str(ep/'rollout/history.jsonl')}], 'path':'atoms/'+kind+'-'+eid+'-counterexample.json'}
 (public/row['path']).write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
index={'version':'central-atomic-sources-v1','actor_access':True,'status':'conditional public source index; original historical scores unchanged','control_contract':control,'retrieval_order':['exact-task audited source','compatible mechanism audited source','matching counterexample'],'sources':rows,'separate_foundation':'table-cube-foundation.json','limits':'Certification labels only; no host audit payload. Cited external paths are provenance, not permission to browse outside the pinned workspace. Same-task/phase compatibility and feedback tier required.'}
(public/'atomic-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
coverage={'snapshot_utc':audit['updated_utc'],'actor_access':False,'audited_simple_successes':sum(c['audited_task_successes'] for c in audit['campaigns']),'indexed_successes':len(certificates),'successes':certificates,'excluded_host_or_native_success':excluded,'counterexamples':4,'scope':'All audited successes in the pinned R019 campaign_audit, independently rechecked via success_review/current episode_status. Not new six-task stability credit.'}
assert coverage['audited_simple_successes']==coverage['indexed_successes']
(HERE/'success-source-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'audited':len(certificates),'counterexamples':4,'excluded_host_or_native_success':len(excluded),'public_files':sum(p.is_file() for p in public.rglob('*'))}))
