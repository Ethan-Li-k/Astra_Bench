"""Read-only projections. No robot imports or executable paths from public JSON."""
import hashlib
import json
from pathlib import Path
import re

SOURCES=('rsi/policy_harness.py','rsi/four_point.py','tools/learn_grasp_skill.py','tools/learn_simple_task.py',
 'rsi/codex_app_server.py','rsi/reference_sequence.py','rsi/scalebfm.py','rsi/live.py','rsi/episode_video.py',
 '/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/bfm/scaletrack.py',
 '/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/runtime/fsq_scaletrack_vla_interface.md',
 'GPT-as-Policy/hybrid_rollout/robodojo/robodojo-gpt-only-rollout/SKILL.md',
 'ref/RoboRSI/roborsi/embodied/skills/agent/atomic_lifecycle/SKILL.md',
 'ref/RoboRSI/roborsi/embodied/skills/_lib/human_review/harness_standard/SKILL.md',
 'ref/RoboRSI/roborsi/embodied/skills/atomic/handover_block/SKILL.md')

SOURCES += ('human-feedback/tools/server.py', 'human-feedback/tools/dashboard.py', 'human-feedback/tools/feedback_board.py', 'human-feedback/tools/harness_view.py', 'human-feedback/tools/progress_clips.py', 'human-feedback/ui/index.html', 'human-feedback/ui/app.js', 'human-feedback/ui/simple-six.html', 'human-feedback/ui/style.css', 'human-feedback/ui/harness.html', 'human-feedback/ui/harness.js', 'human-feedback/ui/harness.css', 'human-feedback/dashboard-upgrade/harness-observability/build_contract.py')

def short(v):return v[:160] if isinstance(v,str) else None
def sha(v):return v if isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) else None

def episode_interface(d,folder):
    budget,_=d.read(folder/'policy_instruction_budget.json')
    protocol,_=d.read(folder/'protocol-registration.json')
    backend,_=d.read(folder/'model_backend.json')
    scene,_=d.read(folder/'video/scene_setup.json')
    observations=d.files(folder/'rollout/episode/observations','[0-9][0-9][0-9][0-9]')
    observation,oref=d.read(observations[-1]/'observation.json') if observations else ({},None)
    cameras=[]
    for im in observation.get('images',[]) if isinstance(observation.get('images'),list) else []:
        if not isinstance(im,dict):continue
        calibration=im.get('calibration',{});intr=calibration.get('render_intrinsics',{}) if isinstance(calibration,dict) else {}
        cameras.append({'camera':short(im.get('camera')),'version':short(intr.get('version')),
                        'render_source':short(intr.get('source'))})
    chunks=[]
    for f in d.files(folder/'rollout/episode','execution_[0-9][0-9][0-9][0-9].json')[-5:]:
        e,ref=d.read(f);response=e.get('response',{});rows=response.get('trajectory') if isinstance(response,dict) else None
        if not isinstance(rows,list) or not 1<=len(rows)<=5 or not ref:continue
        durations=[r.get('duration_s') for r in rows if isinstance(r,dict)]
        if len(durations)!=len(rows) or any(type(v) not in (int,float) or not .5<=v<=3 for v in durations):continue
        receipts=e.get('receipts',[])
        if not isinstance(receipts,list) or not any(isinstance(v,dict) and type(v.get('duration_s')) in (int,float) and v['duration_s']>0 for v in receipts):continue
        chunks.append({'action':int(f.stem.split('_')[-1]),'waypoints':len(rows),'duration_s':sum(durations),
                       'segments_s':durations,'grippers':[{side:r.get('grippers',{}).get(side) if isinstance(r.get('grippers'),dict) and type(r['grippers'].get(side)) in (int,float) and 0<=r['grippers'][side]<=1 else None for side in ('left','right')} for r in rows],'at':ref['at'],'statuses':[short(v.get('status')) for v in receipts if isinstance(v,dict)]})
    continuous=observation.get('continuous_chunk_contract');enabled=continuous.get('enabled') if isinstance(continuous,dict) else None
    size=budget.get('combined_size',{})
    return {'observation_id':short(observation.get('observation_id')),'observation_at':oref['at'] if oref else None,
        'cameras':cameras,'control_source':short(observation.get('joint_command_source')),
        'skill_sha256':sha(budget.get('skill_sha256')),'runtime_sha256':sha(budget.get('runtime_sha256')),
        'instruction_size':{k:size[k] for k in ('words','characters','non_whitespace') if type(size.get(k)) is int},
        'reset_id':short(scene.get('reset_provenance',{}).get('reset_id')),
        'phase':short(protocol.get('phase')),'model':short(backend.get('model')),'effort':short(backend.get('effort')),
        'continuous_enabled':enabled if type(enabled) is bool else None,
        'waypoint_admission':'continuous 2–5；单点也可用' if enabled is True else '普通学习入口：单点后重新观察' if enabled is False else '当前加载准入未上报',
        'loaded_far_offset':None,'chunks':chunks}

def central_load(d):
    """Current publisher pointer and historical physical receipt are separate facts."""
    from dashboard import timestamp
    folder=d.root/'artifacts/architecture-review-20260916/central-skill-publication'
    pub,pref=d.read(folder/'publication-receipt.json');pointer=pub.get('pointer',{})
    pointer=pointer if isinstance(pointer,dict) else {}
    current,cref=d.read(d.root/'skills/releases/CURRENT.json')
    engineering,eref=d.read(d.root/'artifacts/R019/user-update-isaac-api-amo-20260916/terminal-amo-framework/progress.json')
    actual,aref=d.read(d.root/'artifacts/R019/six-task-focus/central-v4-first-actual-load.json')
    ep=d.root/'artifacts/R019/xmovepick-campaign/episode-0006'
    historical=(pub.get('status')=='published' and actual.get('central_release')==pointer.get('release_id')=='central-20260916-v4'
            and sha(actual.get('release_sha256')) is not None and actual.get('release_sha256')==pointer.get('manifest_sha256')
            and actual.get('first_physical_action_observed') is True and type(actual.get('observed_actions')) is int and actual['observed_actions']>0
            and actual.get('runtimeWorkspaceRoots')==[str(ep/'agent')] and d.physical_evidence(ep))
    last=({'release_id':actual['central_release'],'manifest_sha256':actual['release_sha256'],
        'episode':'xmovepick-campaign/episode-0006','verified_at':timestamp(actual.get('verified_utc')) or aref['at'],
        'source_at':aref['at']} if historical else None)
    verified_loads=[last] if last else []
    # One newly reviewed public receipt family, all paths fixed here, never from JSON.
    v5ep=d.root/'artifacts/R019/handover-campaign/episode-0003'
    v5,v5ref=d.read(d.root/'artifacts/R019/handover-campaign/release-load-receipts/episode-0003.json')
    scene,sref=d.read(v5ep/'video/scene_setup.json');budget,bref=d.read(v5ep/'policy_instruction_budget.json')
    first,fref=d.read(v5ep/'rollout/episode/execution_0001.json')
    release=scene.get('central_skill_release',{});reset=scene.get('reset_provenance',{})
    receipts=first.get('receipts',[])
    first_action=isinstance(receipts,list) and any(isinstance(r,dict) and isinstance(r.get('command_id'),str) and r['command_id'].startswith('ep3_a001') and type(r.get('duration_s')) in (int,float) and 0<r['duration_s']<float('inf') for r in receipts)
    if (v5ref and sref and bref and fref and isinstance(release,dict) and isinstance(reset,dict)
        and release.get('release_id')=='central-20260916-v5' and sha(release.get('sha256'))
        and release['sha256']==v5.get('release_sha256') and sha(v5.get('skill_sha256'))==budget.get('skill_sha256') and sha(v5.get('skill_sha256'))
        and v5.get('env_id')==scene.get('env_id')=='simple/G1WholebodyHandoverTeleop-v0'
        and v5.get('episode')=='episode-0003' and type(v5.get('seed')) is int and v5['seed']==scene.get('seed')
        and reset.get('method')=='fresh_environment_reset' and isinstance(reset.get('reset_id'),str) and reset['reset_id'] and first_action):
        verified_loads.append({'release_id':'central-20260916-v5','manifest_sha256':release['sha256'],
            'episode':'handover-campaign/episode-0003','verified_at':fref['at'],'source_at':v5ref['at'],
            'reset_id':short(reset['reset_id']),'scope':'发布/场景/指令哈希一致且已执行首动作；不代表完整任务成功或收益'})
    if verified_loads:last=max(verified_loads,key=lambda r:r['verified_at'])
    publication=None
    if cref and isinstance(current.get('release_id'),str) and re.fullmatch(r'central-\d{8}-v[1-9]\d*',current['release_id']) and sha(current.get('manifest_sha256')):
        publication={'release_id':current['release_id'],'manifest_sha256':current['manifest_sha256'],
            'source_at':cref['at'],'published_at':None,'runtime_integrated':None,
            'time_basis':'CURRENT文件更新时间；发布时间尚未独立上报'}
        for receipt in (pub,engineering.get('handover_publication')):
            if not isinstance(receipt,dict):continue
            registered=receipt.get('pointer')
            if (receipt.get('status')=='published' and isinstance(registered,dict)
                and registered.get('release_id')==current['release_id'] and registered.get('manifest_sha256')==current['manifest_sha256']):
                at=timestamp(receipt.get('at') or receipt.get('published_at'))
                if at:publication.update(published_at=at,time_basis='匹配版本与哈希的发布回执时间')
                integrated=receipt.get('runtime_integrated',receipt.get('shared_runner_integrated'))
                if type(integrated) is bool:publication['runtime_integrated']=integrated
    matched=bool(publication and last and publication['release_id']==last['release_id'] and publication['manifest_sha256']==last['manifest_sha256'])
    note=('当前发布 '+publication['release_id']+'；'+('对应物理加载已核验。' if matched else '该发布版本的实际物理加载尚未确认。') if publication else '当前发布指针未核验，不以旧发布回执代替。')
    note+=(' 最近已核验物理加载：'+last['release_id']+' / '+last['episode']+'（历史回执）。' if last else ' 最近物理加载未核验。')
    return {'current_publication':publication,'last_verified_load':last,'verified_loads':verified_loads,'current_load_confirmed':True if matched else None,
        'published':publication is not None,'release_id':publication['release_id'] if publication else None,
        # Kept for old callers: loaded refers ONLY to last_verified_load.
        'loaded':True if historical else None,'loaded_episode':last['episode'] if last else None,
        'at':publication['published_at'] or publication['source_at'] if publication else None,
        'learning_cumulative_limit_removed':bool(historical and 'max_episode_steps' in actual and actual['max_episode_steps'] is None),
        'physical_benefit_verified':False if historical and actual.get('physical_benefit_verified') is False else None,
        'sources':[r for r in (cref,pref,aref,eref,v5ref,sref,bref,fref) if r], 'note':note}

class HarnessView:
    def __init__(self,dashboard,contract_path=None):
        self.d=dashboard;self.path=Path(contract_path or dashboard.root/'human-feedback/dashboard-upgrade/harness-observability/HARNESS_CONTRACT.json');self.hashes={}
    def contract(self):
        try:doc=json.loads(self.path.read_text())
        except (OSError,ValueError):return {'verification':'unknown','changed_sources':[],'sources':[]}
        changed=[]
        for ref in doc.get('sources',[]):
            name=ref.get('path');actual=None
            if name in SOURCES:
                p=self.d.root/name
                try:
                    if not Path(name).is_absolute():self.d.safe(p)
                    st=p.stat();key=(st.st_mtime_ns,st.st_size,st.st_ino)
                    if self.hashes.get(name,{}).get('stat')!=key:self.hashes[name]={'stat':key,'sha':hashlib.sha256(p.read_bytes()).hexdigest()}
                    actual=self.hashes[name]['sha']
                except (OSError,ValueError):pass
            if actual!=ref.get('sha256'):changed.append(name)
        return dict(doc,verification='stale_source_snapshot' if changed else 'verified_source_snapshot',changed_sources=changed)
    def snapshot(self,simple):
        current=[]
        for t in simple.get('subtasks',[]):
            current.append({k:t.get(k) for k in ('id','name','episode','actions','last_action_at','state_label','problem','episode_interface','progress_clip','preview')})
        statuses=[];central=central_load(self.d)
        for name,relative in [('Isaac视觉','artifacts/R019/user-update-isaac-api-amo-20260916/isaac-render-integration/progress.json'),
                              ('完整学习终止 / AMO','artifacts/R019/user-update-isaac-api-amo-20260916/terminal-amo-framework/progress.json')]:
            doc,ref=self.d.read(self.d.root/relative)
            if not ref and name=='完整学习终止 / AMO':
                relative=relative.replace('/progress.json','/status.json');doc,ref=self.d.read(self.d.root/relative)
            phase=short(doc.get('phase'))
            labels={'bounded_engineering_complete':'本轮工程已交付；源码发布与物理加载分别核验，AMO候选待物理准入',
                'amo_actual_caller_offline_passed':'AMO实际调用方离线检查通过；物理加载与收益另验',
                'fresh_cache_startup_test_and_calibration_contract':'新缓存启动检查与相机标定合同审查',
                'isolated_sync_candidate':'同步渲染隔离候选审查',
                'render_kinematic_regression_startup_recovery':'渲染运动学回归检查与启动恢复',
                'handover_termination_reproduction':'复现弱原生成功提前终止',
                'handover_v5_published_amo_adapter_in_progress':'Handover终止修复源码已发布；AMO适配在研'}
            publication=doc.get('handover_publication',{});publication=publication if isinstance(publication,dict) else {}
            handover=doc.get('handover');active_publication=central.get('current_publication')
            if (not publication and isinstance(handover,dict) and handover.get('state')=='published_and_load_observed' and active_publication
                and handover.get('release')==active_publication['release_id'] and handover.get('release_sha256')==active_publication['manifest_sha256']):
                publication={'status':'published','pointer':{'release_id':handover['release'],'manifest_sha256':handover['release_sha256']},
                    'first_physical_load_confirmed':central['current_load_confirmed']}
            pointer=publication.get('pointer',{});pointer=pointer if isinstance(pointer,dict) else {}
            published=(publication.get('status')=='published' and sha(pointer.get('manifest_sha256')) is not None)
            statuses.append({'name':name,'phase':phase,'phase_label':labels.get(phase,'工程阶段尚无已核验中文说明；请看来源状态'),
                'current_problem':short(doc.get('current_problem')),'next_step':short(doc.get('next_step')),
                'source_published':True if published else None,'release_id':short(pointer.get('release_id')) if published else None,
                'physical_load_confirmed':publication.get('first_physical_load_confirmed') if published and type(publication.get('first_physical_load_confirmed')) is bool else None,
                'at':ref['at'] if ref else None,
                'physics_backend':short(doc.get('physics_backend')),'render_backend_current':short(doc.get('render_backend_current')),
                'actor_loaded_isaac_verified':doc.get('actor_loaded_isaac_verified') if type(doc.get('actor_loaded_isaac_verified')) is bool else None,
                'source':relative,'note':'工程状态；不代表实际物理进展或收益'})
        return {'contract':self.contract(),'central':central,'episodes':current,'engineering':statuses}
