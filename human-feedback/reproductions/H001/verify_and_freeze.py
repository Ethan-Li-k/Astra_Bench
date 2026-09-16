from pathlib import Path
import json,hashlib,datetime,subprocess,os
import numpy as np
p=Path(__file__).resolve().parent;a=p/'host_audit/attempt-002'
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as s:
  for chunk in iter(lambda:s.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
assert (p/'logs/physics-attempt-002.exit').read_text().strip()=='0'
assert (p/'logs/analysis.exit').read_text().strip()=='0'
s=json.loads((p/'status.json').read_text());assert s['failure_reproduced'] and not s['task_success_credit']
with np.load(a/'tracker_history.npz') as z:
 assert len(z['sim_s'])==10988
 assert np.allclose(np.diff(z['sim_s']),.02,atol=1e-9,rtol=0)
 assert z['policy_history_pre'].shape==(10988,1,3,64)
 assert z['action_history_pre'].shape==(10988,1,3,29)
 shapes={k:list(z[k].shape) for k in z.files}
video_results=[]
for video in [a/'video/episode.mp4',p/'evidence/closure-lift-head-left.mp4']:
 command=['ffmpeg','-v','error','-i',str(video),'-f','null','-']
 run=subprocess.run(command,capture_output=True,text=True)
 video_results.append({'command':command,'exit_code':run.returncode,'stderr':run.stderr})
 assert run.returncode==0
v={'task_success_credit':False,'reproduction_only':True,'tracker_array_shapes':shapes,'control_period_verified_s':.02,'videos':video_results,'threshold_hash_unchanged':sha(p/'thresholds.json')==s['frozen_threshold_sha256']}
assert v['threshold_hash_unchanged']
(a/'verification.json').write_text(json.dumps(v,indent=2))
selected=[p/'thresholds.json',p/'reproduce.py',p/'run_physics.sh',p/'analyze.py',p/'run_analysis.sh']
for directory in ['source_commands','attempt-001','attempt-002','evidence','host_audit']:
 selected.extend(f for f in (p/directory).rglob('*') if f.is_file())
files=[{'path':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(set(selected))]
freeze={'task_success_credit':False,'reproduction_only':True,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'attempt-002','failure_reproduced':True,'method':'content-addressed read-only baseline by manifest; no overwrite permitted by continuation contract','mutability_note':'Status/report/notification are handoff metadata; evidence listed here must remain unchanged.','files':files,'original_full_hidden_state_equivalence_claimed':False,'corrective_actor_executed':False}
(p/'BASELINE_FROZEN.json').write_text(json.dumps(freeze,indent=2))
s.update(phase='complete_baseline_frozen',baseline_frozen=True,baseline_manifest=str(p/'BASELINE_FROZEN.json'),baseline_manifest_sha256=sha(p/'BASELINE_FROZEN.json'),baseline_human_feedback_used=False,human_feedback_used=False,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(p/'status.json').write_text(json.dumps(s,indent=2,ensure_ascii=False))
print(json.dumps({'phase':s['phase'],'frozen_files':len(files),'frozen_bytes':sum(r['bytes'] for r in files),'video_decode_checks':'passed','tracker_history_check':'passed','reproduction_only':True,'task_success_credit':False}))
