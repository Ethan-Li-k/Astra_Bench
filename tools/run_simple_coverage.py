"""One durable supervisor: breadth-first fresh episodes, evidence count, fixed concurrency."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from rsi.actor_transport import atomic
from rsi.coverage_rounds import read,classify,select_next
from rsi.skill_release import digest
W=R/'artifacts/harness-reset-20260917/execution';PLAN=R/'artifacts/harness-reset-20260917/plan.json'
PYTHON='/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python'
FIRST=['simple/G1WholebodyOpenTrashCanTeleop-v0','simple/G1WholebodyOpenOvenTeleop-v0','simple/G1WholebodyOpenFaucetTeleop-v0','simple/G1WholebodyCloseDoorTeleop-v0','simple/G1WholebodyPickAndPlaceAppleTeleop-v0','simple/G1WholebodyBendPickAndPlaceTeleop-v0','simple/G1WholebodyBendPickTeleop-v0','simple/G1WholebodyPushOfficeChairTeleop-v0']
W.mkdir(exist_ok=True);(W/'campaigns').mkdir(exist_ok=True)
if (read(W/'runtime.json',{}) or {}).get('dispatch_allowed') is False:
    raise SystemExit('User cancelled this coverage plan; no process admission or API requests')
# One supervisor process, separate per-exact-env leases remain in the real host.
import fcntl
lock=(W/'scheduler.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
plan=read(PLAN);selection=read(R/'artifacts/harness-reset-20260917/task-inventory/exact60.json')['tasks'];inventory={r['env_id']:r for r in read(R/'artifacts/harness-reset-20260917/task-inventory/tasks.json')['tasks']}
class ExistingProcess:
    def __init__(self,pid):self.pid=pid
    def poll(self):
        p=Path('/proc')/str(self.pid)
        try:return 0 if (p/'stat').read_text().split()[2]=='Z' else None
        except FileNotFoundError:return 0
procs={};blocked={};cached={};started=time.time()
for lane in (read(W/'status.json',{}) or {}).get('lanes',[]):
    ep=Path(lane['episode']);p=ExistingProcess(lane['pid'])
    if p.poll() is not None:continue
    command=(Path('/proc')/str(p.pid)/'cmdline').read_bytes().decode().split('\0')
    if str(R/'tools/learn_simple_task.py') not in command or str(ep.parent) not in command:raise ValueError('Cannot adopt different PID command')
    launch=read(ep.parent/(ep.name+'-launch.json'))
    procs[lane['env_id']]={'process':p,'episode':ep,'release_id':launch['release']['release_id'],'started_at':lane['started_at']}
    print(json.dumps({'event':'worker_adopted_without_restart','pid':p.pid,'episode':str(ep)}),flush=True)
while True:
    pointer=read(R/'skills/releases/CURRENT.json');release=R/'skills/releases'/pointer['release_id'];manifest=read(release/'release.json')
    runtime=read(W/'runtime.json',{'parallel_target':4});target=int(runtime['parallel_target']);assert 1<=target<=8
    for env,item in list(procs.items()):
        if item['process'].poll() is not None:
            ep=item['episode'];classification=classify(ep,plan['started_at']) if (ep/'result.json').exists() else {'complete':False,'state':'infrastructure_blocked','reason':'Worker exited without terminal episode result'}
            atomic(ep.parent/(ep.name+'-classification.json'),classification)
            if not classification['complete']:blocked[env]={'release_id':item['release_id'],'classification':classification}
            del procs[env]
    tasks=[]
    for rank,selected in enumerate(selection):
        env=selected['env_id'];meta=inventory[env];uid=meta['task_uid'];campaign=W/'campaigns'/(uid+'-campaign');episodes=sorted(campaign.glob('episode-*')) if campaign.exists() else [];episodes=[p for p in episodes if p.is_dir()]
        entries=[]
        for ep in episodes:
            if not (ep/'result.json').exists():continue
            key=(str(ep),(ep/'result.json').stat().st_mtime_ns)
            if key in cached and not cached[key].get('complete'):cached.pop(key)
            if key not in cached:cached[key]=classify(ep,plan['started_at']);atomic(campaign/(ep.name+'-classification.json'),cached[key])
            entries.append(cached[key])
        seen=set();valid=[]
        for row in entries:
            if row.get('complete') and row.get('reset_id') not in seen:valid.append(row);seen.add(row['reset_id'])
        binding=manifest['tasks'].get(env);ready=bool(binding and binding['ready_for_load'])
        row={'env_id':env,'task_key':uid,'rank':FIRST.index(env) if env in FIRST else rank+10,'ready':ready,'complete_attempts':len(valid),'successes':sum(v['configured_success'] for v in valid),'configured_successes':sum(v['configured_success'] for v in valid),'audited_successes':sum(v['audited_success'] for v in valid),'reward_model':meta['reward_model'],'progress_model':meta['progress_model'],'experience_sources':[],'blocking':None if ready else meta['blockers'] or ['No released exact task input/control binding'],'latest_episode':str(episodes[-1]) if episodes else None,'current_episode':str(procs[env]['episode']) if env in procs else None,'attempt_classification':entries,'campaign':str(campaign)}
        if env in blocked and blocked[env]['release_id']==pointer['release_id']:row['blocking']=blocked[env]['classification']['reason']
        if episodes:
            spec=read(episodes[-1]/'agent/task_specification.json',{});row['experience_sources']=spec.get('reset_experience',{}).get('cases',[])
            row['experience_selected']=[]
            path=episodes[-1]/'rollout/skill_selection.jsonl'
            if path.exists():row['experience_selected']=[json.loads(x) for x in path.read_text().splitlines()]
        tasks.append(row)
    blocked_now={e for e,v in blocked.items() if v['release_id']==pointer['release_id']}
    while len(procs)<target and time.time()<plan['deadline_at'] and runtime.get('dispatch_allowed',True):
        task=select_next(tasks,set(procs),blocked_now,plan['minimum_complete_attempts_per_task'])
        if task is None:break
        env=task['env_id'];t=manifest['tasks'][env];campaign=Path(task['campaign']);campaign.mkdir(exist_ok=True)
        number=max([int(p.name.split('-')[-1]) for p in campaign.glob('episode-*') if p.is_dir()],default=0)+1;ep=campaign/f'episode-{number:04d}'
        argv=[PYTHON,'-B',str(R/'tools/learn_simple_task.py'),'--env-id',env,'--task-spec',str(release/'public'/t['task_spec_path']),'--output',str(campaign),'--seed',str(1000+number),'--phase','learning','--skill-release',str(release),'--release-sha256',pointer['manifest_sha256'],'--direct-api']
        for key,flag in [('continuous_chunks','--continuous-chunks'),('native_mp_amo','--native-mp-amo'),('native_mp_checkpoint','--native-mp-checkpoint'),('verified_placement','--verified-placement'),('door_frame_override','--door-frame-override')]:
            if t['bindings'].get(key):argv.append(flag)
        for feedback in t.get('human_feedback_paths',[]):argv+=['--human-feedback',str(release/'public'/feedback)]
        if t['bindings'].get('scene_contract_sha256'):
            scene=release/'public'/t['scene_contract_path'];argv+=['--scene-contract',str(scene),'--scene-contract-sha256',t['bindings']['scene_contract_sha256']]
        envvars=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MUJOCO_GL='egl',OMP_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(R)+':/home/galbot/lizekai/Loco_manip/locomanip/src',TMPDIR=str(W/'tmp'),XDG_CACHE_HOME=str(W/'cache'))
        for folder in ['tmp','cache']:(W/folder).mkdir(exist_ok=True)
        with (campaign/(ep.name+'.log')).open('a') as log:p=subprocess.Popen(argv,cwd=R,env=envvars,stdout=log,stderr=subprocess.STDOUT)
        procs[env]={'process':p,'episode':ep,'release_id':pointer['release_id'],'started_at':time.time()}
        atomic(campaign/(ep.name+'-launch.json'),{'argv':argv,'pid':p.pid,'episode':str(ep),'route':'api','release':pointer,'started_at':time.time(),'plan_id':plan['id']})
        print(json.dumps({'event':'worker_started','env_id':env,'pid':p.pid,'episode':str(ep)}),flush=True)
    lanes=[]
    for env,item in procs.items():
        ep=item['episode'];actions=len(list((ep/'rollout/episode').glob('execution*.json')));progress=read(ep/'task-progress.json',{});paused=(ep/'api-service-paused.json').exists();task=next(r for r in tasks if r['env_id']==env)
        lanes.append({'task_key':task['task_key'],'env_id':env,'episode':str(ep),'route':'api','pid':item['process'].pid,'state':'api_service_paused' if paused else 'acting' if actions else 'initializing_or_model_planning','actions':actions,'complete_attempts':task['complete_attempts'],'started_at':item['started_at'],'progress':progress,'real_process_alive':item['process'].poll() is None,'reset_completed':(ep/'reset-receipt.json').exists(),'service_paused':paused,'pause_detail':read(ep/'api-service-paused.json',{})})
    complete=sum(t['complete_attempts'] for t in tasks);totals={'complete_attempts':complete,'attempted_tasks':sum(t['complete_attempts']>0 for t in tasks),'tasks_at_least_five':sum(t['complete_attempts']>=5 for t in tasks),'active_lanes':sum(x['real_process_alive'] for x in lanes),'reset_lanes':sum(x['reset_completed'] for x in lanes),'acting_lanes':sum(x['actions']>0 and not x['service_paused'] for x in lanes),'service_paused_lanes':sum(x['service_paused'] for x in lanes),'ready_tasks':sum(t['ready'] for t in tasks),'target_tasks':60,'target_complete_attempts':300,'successes':sum(t['configured_successes'] for t in tasks),'configured_successes':sum(t['configured_successes'] for t in tasks),'audited_successes':sum(t['audited_successes'] for t in tasks)}
    status={'plan_id':plan['id'],'started_at':plan['started_at'],'deadline_at':plan['deadline_at'],'updated_at':time.time(),'parallel_target':target,'release':pointer,'lanes':lanes,'tasks':tasks,'totals':totals,'formal_credit':False,'historical_counts_excluded':True,'elapsed_hours':(time.time()-plan['started_at'])/3600}
    atomic(W/'status.json',status)
    if not procs and (totals['tasks_at_least_five']==60 or time.time()>=plan['deadline_at']):break
    time.sleep(10)
