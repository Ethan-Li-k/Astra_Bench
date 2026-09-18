"""Up to four approved transfer lanes; exact split and one locked supervisor."""
from pathlib import Path
import datetime,fcntl,hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from rsi.coverage_rounds import read,classify
from rsi.training_gate import require_training,reviewed_attempt,BASE
from rsi.actor_transport import atomic
from rsi.episode_continuation import pending_diagnostic
W=BASE/'execution';W.mkdir(exist_ok=True);(W/'campaigns').mkdir(exist_ok=True)
lock=(W/'scheduler.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
PYTHON='/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python'
procs={};blocked={}

class ExistingWorker:
 def __init__(self,pid,argv):
  self.pid=pid;self.argv=argv;self.root=Path('/proc')/str(pid)
  assert os.getsid(pid)==pid, 'Only an independent actor session may be adopted'
  assert self.root.joinpath('cmdline').read_bytes().split(b'\0')[:-1]==[s.encode() for s in argv], 'Actor identity changed'
  self.start=self.root.joinpath('stat').read_text().rsplit(') ',1)[1].split()[19]
 def poll(self):
  try:fields=self.root.joinpath('stat').read_text().rsplit(') ',1)[1].split()
  except FileNotFoundError:return 0
  return 0 if fields[0]=='Z' or fields[19]!=self.start else None

# A supervisor handoff adopts existing independent workers; it never repeats a
# reset, a model request, or an action. The exclusive scheduler lock is held.
previous=read(W/'status.json',{})
for lane in previous.get('lanes',[]):
 ep=Path(lane['episode']);launch=read(ep.parent/(ep.name+'-launch.json'),{})
 assert launch.get('pid')==lane['pid'] and launch.get('episode')==str(ep)
 worker=ExistingWorker(lane['pid'],launch['argv'])
 procs[lane['env_id']]={'process':worker,'episode':ep,'release':launch['release']['release_id'],'started_at':launch['started_at'],'route':launch.get('route','api')}
if procs:atomic(W/'scheduler-adoption.json',{'at':time.time(),'pid':os.getpid(),'workers':{env:{'pid':v['process'].pid,'episode':str(v['episode']),'release':v['release']} for env,v in procs.items()},'new_resets':0,'new_model_requests':0,'worker_restarts':0})
while True:
 plan=read(BASE/'plan.json');split=read(BASE/'task-split.json');scope=plan['launch_scope']
 assert 1<=len(scope)<=4 and len(set(scope))==len(scope), 'Expected 1–4 distinct approved tasks'
 assert set(scope)<=set(plan['selected_training_env_ids']), 'Scope must stay in selected training tasks'
 ptr=read(R/'skills/releases/CURRENT.json');release=R/'skills/releases'/ptr['release_id'];manifest=read(release/'release.json')
 rows=[]
 for env in scope:
  override=read(W/'route-overrides.json',{}).get(env)
  lane_ptr=ptr;lane_release=release;lane_manifest=manifest;route='api';runner=R/'tools/learn_simple_task.py'
  if override:
   assert override['env_id']==env and override['route']=='main_chatgpt'
   assert override['model']=='gpt-6-astra' and override['effort']=='xhigh'
   fence=Path(override['fenced_episode'])/'execution-fence.json';f=read(fence)
   assert hashlib.sha256(fence.read_bytes()).hexdigest()==override['execution_fence_sha256']
   assert f['status']=='execution_fenced' and f['late_output_cannot_execute'] and not Path('/proc',str(f['pid'])).exists()
   lane_ptr=override['release'];lane_release=Path(override['release_path']);lane_manifest=read(lane_release/'release.json')
   assert hashlib.sha256((lane_release/'release.json').read_bytes()).hexdigest()==lane_ptr['manifest_sha256']
   route='main_chatgpt';runner=Path(override['runner'])
  key=env.split('/')[1].removesuffix('-v0');campaign=W/'campaigns'/(key+'-campaign');episodes=sorted(p for p in campaign.glob('episode-*') if p.is_dir()) if campaign.exists() else []
  classified=[dict(reviewed_attempt(ep,classify(ep,plan['started_at'],plan['id'])),episode=str(ep)) for ep in episodes if (ep/'result.json').exists()];valid=[];seen=set()
  for entry in classified:
   if entry.get('complete') and entry['reset_id'] not in seen:valid.append(entry);seen.add(entry['reset_id'])
  curriculum_rows=[r for r in classified if r.get('curriculum_complete')]
  level=read(lane_release/'public'/lane_manifest['tasks'][env]['task_spec_path'],{}).get('curriculum_contract',{}).get('level')
  consecutive=[];curriculum_seen=set()
  for cr in reversed(curriculum_rows):
   if cr.get('curriculum_level')!=level:continue
   if not cr.get('audited_curriculum_success'):break
   if cr['reset_id'] not in curriculum_seen:consecutive.append(cr);curriculum_seen.add(cr['reset_id'])
  promotion_needed=len(consecutive)>=2
  if env in procs and procs[env].get('route','api')=='api':
   from rsi.legacy_transport_recovery import recover_if_eligible
   recovery=recover_if_eligible(env,procs[env])
   if recovery:
    print(json.dumps({'event':'legacy_api_recovery','env_id':env,'state':recovery.get('status','main_release_ready')}),flush=True)
    continue
  if env in procs and procs[env]['process'].poll() is not None:
   item=procs.pop(env);result=next((r for r in classified if r['episode']==str(item['episode'])),None)
   if not result or not (result['complete'] or result.get('reviewed_curriculum_attempt')):blocked[env]={'episode':str(item['episode']),'release':item['release'],'reason':(result or {}).get('reason','Worker exited without complete episode evidence')}
  if env in blocked and any(r['episode']==blocked[env]['episode'] and (r.get('complete') or r.get('reviewed_curriculum_attempt')) for r in classified):blocked.pop(env)
  row={'env_id':env,'task_key':key,'complete_attempts':len(valid),'configured_successes':sum(r.get('configured_success',False) for r in valid),'audited_successes':sum(r.get('audited_success',False) for r in valid),'latest_episode':str(episodes[-1]) if episodes else None,'current_episode':str(procs[env]['episode']) if env in procs else None,'blocking':None if env in procs else blocked.get(env),'attempt_classification':classified}
  row.update(curriculum_completed_attempts=len(curriculum_rows),curriculum_audited_successes=sum(r.get('audited_curriculum_success',False) for r in curriculum_rows),curriculum_current_level=level,curriculum_consecutive_successes=len(consecutive),curriculum_attempts=len(curriculum_rows),curriculum_successes=sum(r.get('curriculum_success',False) for r in curriculum_rows),audited_curriculum_successes=sum(r.get('audited_curriculum_success',False) for r in curriculum_rows),curriculum_level=level,curriculum_next_state='promotion_needed' if promotion_needed else 'collect_two_reviewed_successes' if level else 'not_loaded')
  if promotion_needed and env not in procs:
   row['blocking']={'reason':'Two independent reviewed stage successes; publish next curriculum level before another reset','level':level}
   promotion_dir=BASE/'curriculum/promotion-requests';promotion_dir.mkdir(exist_ok=True)
   atomic(promotion_dir/(key+'.json'),{'env_id':env,'level':level,'release':lane_ptr,'episodes':[r['episode'] for r in consecutive],'apply_on':'next_reset','at':time.time()})
  rows.append(row)
  if env in procs or (env in blocked and blocked[env]['release']==lane_ptr['release_id']):continue
  if promotion_needed:continue
  if len(valid)>=plan['minimum_complete_attempts_per_selected_training_task']:continue
  if (BASE/'STOP.json').exists() or not plan.get('new_training_launch_allowed'):continue
  require_training(env,plan=plan,split=split,complete_attempts=len(valid))
  t=lane_manifest['tasks'][env];assert t['ready_for_load'];campaign.mkdir(exist_ok=True);number=max([int(p.name.split('-')[-1]) for p in episodes],default=0)+1;ep=campaign/f'episode-{number:04d}'
  argv=[PYTHON,'-B',str(runner),'--env-id',env,'--task-spec',str(lane_release/'public'/t['task_spec_path']),'--output',str(campaign),'--seed',str(number),'--phase','learning','--skill-release',str(lane_release),'--release-sha256',lane_ptr['manifest_sha256'],('--main-account' if route=='main_chatgpt' else '--direct-api')]
  for key,flag in [('api_background','--background'),('continuous_chunks','--continuous-chunks'),('native_mp_amo','--native-mp-amo'),('native_mp_checkpoint','--native-mp-checkpoint'),('verified_placement','--verified-placement'),('door_frame_override','--door-frame-override')]:
   if t['bindings'].get(key):argv.append(flag)
  for feedback in t.get('human_feedback_paths',[]):argv+=['--human-feedback',str(lane_release/'public'/feedback)]
  if t['bindings'].get('scene_contract_sha256'):argv+=['--scene-contract',str(lane_release/'public'/t['scene_contract_path']),'--scene-contract-sha256',t['bindings']['scene_contract_sha256']]
  envvars=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MUJOCO_GL='egl',OMP_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(R)+':/home/galbot/lizekai/Loco_manip/locomanip/src',TMPDIR=str(W/'tmp'),XDG_CACHE_HOME=str(W/'cache'))
  for folder in ['tmp','cache']:(W/folder).mkdir(exist_ok=True)
  with (campaign/(ep.name+'.log')).open('a') as log:p=subprocess.Popen(argv,cwd=R,env=envvars,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  procs[env]={'process':p,'episode':ep,'release':lane_ptr['release_id'],'started_at':time.time(),'route':route};atomic(campaign/(ep.name+'-launch.json'),{'argv':argv,'pid':p.pid,'episode':str(ep),'route':route,'release':lane_ptr,'started_at':time.time(),'plan_id':plan['id'],'independent_process_session':True})
  print(json.dumps({'event':'training_started','env_id':env,'episode':str(ep),'pid':p.pid}),flush=True)
 lanes=[]
 for env,item in procs.items():
  ep=item['episode'];progress=read(ep/'task-progress.json',{});actions=len(list((ep/'rollout/episode').glob('execution*.json')));paused=read(ep/'api-service-paused.json',{})
  diagnostic=pending_diagnostic(ep/'api-continuation')
  if diagnostic:paused=dict(diagnostic,diagnostic_boundary=True)
  lanes.append({'env_id':env,'task_key':env.split('/')[1].removesuffix('-v0'),'episode':str(ep),'pid':item['process'].pid,'loaded_release':item['release'],'route':item.get('route','api'),'model':'gpt-6-astra','effort':'xhigh','state':'diagnostic_paused' if diagnostic else 'service_paused' if paused else 'acting' if actions else 'initializing_or_reasoning','actions':actions,'started_at':item['started_at'],'real_process_alive':item['process'].poll() is None,'progress':progress,'progress_verification':progress.get('stage_verification','not yet observed'),'pause_detail':paused})
 status={'plan_id':plan['id'],'updated_at':time.time(),'started_at':plan['started_at'],'parallel_target':len(scope),'dispatch_allowed':plan.get('new_training_launch_allowed') and not (BASE/'STOP.json').exists(),'release':ptr,'lanes':lanes,'tasks':rows,'training_only':True,'tests_started':0,'totals':{'active_lanes':sum(x['real_process_alive'] for x in lanes),'acting_lanes':sum(x['actions']>0 and not x['pause_detail'] for x in lanes),'complete_attempts':sum(r['complete_attempts'] for r in rows),'configured_successes':sum(r['configured_successes'] for r in rows),'audited_successes':sum(r['audited_successes'] for r in rows),'selected_tasks':len(scope),'complete_attempts_per_task':plan['minimum_complete_attempts_per_selected_training_task']}}
 atomic(W/'status.json',status)
 if not procs and (not status['dispatch_allowed'] or all(r['complete_attempts']>=plan['minimum_complete_attempts_per_selected_training_task'] for r in rows)):break
 time.sleep(5)
