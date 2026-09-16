"""Small, explicit public source adapter. No actor imports, logs, credentials or reasoning.
Only whitelisted summary fields leave this module. File mtimes are evidence times,
not proof of current execution. No recursive filesystem discovery.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from api_progress import APIProgress, signature, number
from ikea_progress import IKEAProgress
from simple_six import scorecard, official_baseline

RSI = Path(__file__).resolve().parents[2]
CAMPAIGNS = {'door': ('推门', 'door-campaign', 10), 'apple': ('苹果', 'apple-campaign', 1),
             'faucet': ('水龙头', 'faucet-campaign', 1), 'boxpick': ('拾箱', 'bendpick-campaign', 1),
             'boxplace': ('放箱', 'boxplace-campaign', 1),
             'oven': ('烤箱 OpenOven', 'oven-campaign', 1)}
OVEN_TASK = 'simple/G1WholebodyOpenOvenTeleop-v0'
SIX_TASKS = {'XMovePick':'simple/G1WholebodyXMovePickTeleop-v0',
             'BendPick':'simple/G1WholebodyBendPickMP-v0',
             'Handover':'simple/G1WholebodyHandoverTeleop-v0',
             'Mobile P&P':'simple/G1WholebodyLocomotionPickBetweenTablesTeleop-v0',
             'Grasp':'simple/G1WholebodyTabletopGraspMP-v0',
             'XMoveBendPick':'simple/G1WholebodyXMoveBendPickTeleop-v0'}
CAMPAIGN_NAME = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*-campaign')
REGISTERED_TASK = re.compile(r'simple/[A-Za-z][A-Za-z0-9_-]*-v[0-9]+')
TASK_NAMES = {'simple/G1WholebodyOpenTrashCanTeleop-v0':'垃圾桶',
              'simple/G1WholebodyPushOfficeChairTeleop-v0':'办公椅',
              'simple/G1WholebodyXMoveBendPickTeleop-v0':'移动拾箱 XMoveBendPick'}
LABELS = {'modelwaiting':'等待完整推理', 'physicsrunning':'物理动作执行中',
          'budgetstop':'预算到界 · 未完成', 'safetystop':'安全停止',
          'infraerror':'基础设施错误', 'needs-human':'有待回答的问题',
          'engineering-prep':'工程准备 / 验证', 'complete':'目标已达成',
          'episode-complete':'回合成功 · 任务继续', 'earlystop':'主动提前结束 · 未完成',
          'physical-failure':'终态物理失败', 'unknown':'当前执行阶段未确认',
          'review':'等待结果审查', 'active-unknown':'回合未封口 · 阶段未上报'}
EP = re.compile(r'episode-\d{4,8}')

def hash_json(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def timestamp(v):
    if number(v) is not None: return v
    try: return dt.datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
    except (ValueError,TypeError,AttributeError): return None

def public_text(docs, *fields):
    """Only named short public fields; never stringify arbitrary nested payloads."""
    for doc in docs:
        for field in fields:
            value=doc.get(field)
            if isinstance(value,str) and value.strip():return value.strip()[:600]
    return None

def public_time(doc, ref):
    for field in ('updated_utc','updated_at','updated_at_unix','at','reviewed_utc','completed_utc'):
        value=timestamp(doc.get(field))
        if value is not None:return value
    return ref['at'] if ref else 0

class Dashboard:
    def __init__(self, root=RSI, api=None):
        self.root=Path(root); self.api=api or APIProgress(self.root/'api-ground-to-table/actor-adapter')
        self.ikea_media=IKEAProgress(self.root/'ikea'); self.lock=threading.RLock(); self.cache=None; self.cached_at=0
        self.media={}; self.probes={}; self.records={}; self.json_cache={}
        self.simple_catalog=dict(CAMPAIGNS)

    def safe(self,p):
        p=Path(p); rel=p.relative_to(self.root); cur=self.root
        if cur.is_symlink(): raise ValueError('symlink')
        for part in rel.parts:
            if part=='..': raise ValueError('path')
            cur=cur/part
            if cur.is_symlink(): raise ValueError('symlink')
        if not p.resolve().is_relative_to(self.root.resolve()): raise ValueError('path')
        return p

    def read(self,p,allow_list=False):
        try:
            p=self.safe(p); sig=signature(p)
            if sig[2]>8*1024*1024: return {},None
            cache_key=(str(p),allow_list);cached=self.json_cache.get(cache_key)
            if cached and cached[0]==sig:return cached[1],cached[2]
            raw=p.read_bytes(); d=json.loads(raw)
            if not isinstance(d,dict) and not (allow_list and isinstance(d,list)): return {},None
            ref={'path':str(p.relative_to(self.root)), 'sha256':hashlib.sha256(raw).hexdigest(),'at':p.stat().st_mtime}
            self.json_cache[cache_key]=(sig,d,ref)
            return d,ref
        except (OSError,ValueError,TypeError): return {},None

    def files(self,p,pattern):
        try: return sorted(x for x in self.safe(p).glob(pattern) if not x.is_symlink())
        except (OSError,ValueError): return []

    def simple_progress_text(self):
        """Read only the fixed public summary; parse known campaign/episode lines."""
        p=self.root/'artifacts/R019/PROGRESS.md'
        try:
            self.safe(p)
            if p.stat().st_size>100000:return {},None
            raw=p.read_bytes();body=raw.decode('utf-8')
            ref={'path':'artifacts/R019/PROGRESS.md','sha256':hashlib.sha256(raw).hexdigest(),'at':p.stat().st_mtime}
            rows={}
            for line in body.splitlines():
                match=re.fullmatch(r'- ([a-z][a-z0-9-]*-campaign)：审计成功 [^；]+；(episode-\d{4,8})，(.+?)，\d+动作；终态分类 ([a-z_]+)。最近物理日志 ([^。]+)。',line)
                if not match or match[1] not in {v[1] for v in self.simple_catalog.values()}:continue
                phase=match[3]
                rows[match[1]]={'episode_id':match[2],'current_problem':'负责人进展摘要：'+phase+'。',
                               'phase':phase,'termination_class':match[4],'last_action_at':timestamp(match[5])}
            return rows,ref
        except (OSError,ValueError,UnicodeError):return {},None

    def simple_campaign_public(self):
        doc,ref=self.read(self.root/'artifacts/R019/campaign_audit.json');rows={}
        self.simple_catalog=dict(CAMPAIGNS);extra={}
        fixed_folders={v[1]:k for k,v in CAMPAIGNS.items()}
        for row in doc.get('campaigns',[]) if isinstance(doc.get('campaigns',[]),list) else []:
            if not isinstance(row,dict):continue
            raw=row.get('campaign')
            if not isinstance(raw,str):continue
            folder=Path(raw).name
            if not CAMPAIGN_NAME.fullmatch(folder):continue
            expected=self.root/'artifacts/R019'/folder
            # Require the exact canonical direct-child spelling, before any filesystem reads.
            if raw not in (str(expected),str(expected.relative_to(self.root))):continue
            try:self.safe(expected)
            except ValueError:continue
            if folder in fixed_folders:
                key=fixed_folders[folder]
                if key=='oven' and row.get('task')!=OVEN_TASK:continue
                rows[key]=row
                continue
            key=folder.removesuffix('-campaign');task=row.get('task')
            if key in CAMPAIGNS or not isinstance(task,str) or not REGISTERED_TASK.fullmatch(task):continue
            if (number(row.get('physical_attempts')) or 0)<=0 or not expected.is_dir():continue
            progress,_=self.read(expected/'progress.json')
            if progress.get('task') not in (None,task):continue
            evidence=False
            for episode in row.get('episodes',[]) if isinstance(row.get('episodes',[]),list) else []:
                if not isinstance(episode,dict):continue
                ep=episode.get('episode_id')
                if not isinstance(ep,str) or not EP.fullmatch(ep) or episode.get('physical_attempt') is not True or (number(episode.get('actions')) or 0)<=0:continue
                if self.physical_evidence(expected/ep):evidence=True;break
            if not evidence:continue
            goal=number(row.get('required_successes'))
            extra[key]=(TASK_NAMES.get(task,task),folder,goal if goal is not None and goal>0 else None)
            rows[key]=row
        # The verified owner's bounded mapping can introduce a first physical attempt
        # before the campaign aggregate has been rebuilt. Never follow arbitrary paths.
        owner,oref=self.read(self.root/'artifacts/R019/six-task-focus/supervisor-ack.json')
        families=owner.get('campaign_families')
        if (owner.get('ack')=='SIX-TASK-FOCUS-20260916 ACK' and owner.get('mapping')==SIX_TASKS
            and owner.get('owner_thread')=='01a0a867-d7aa-71f2-8547-e264d6d09ede' and isinstance(families,dict)):
            for folder,name in families.items():
                if not isinstance(folder,str) or not CAMPAIGN_NAME.fullmatch(folder) or not isinstance(name,str) or name not in SIX_TASKS:continue
                key=folder.removesuffix('-campaign');native=SIX_TASKS[name]
                if key in CAMPAIGNS or key in rows:continue
                expected=self.root/'artifacts/R019'/folder
                for episode in self.files(expected,'episode-*'):
                    if not EP.fullmatch(episode.name):continue
                    scene,_=self.read(episode/'video/scene_setup.json')
                    if scene.get('env_id',scene.get('native_env_id'))!=native or not self.physical_evidence(episode):continue
                    extra[key]=(name,folder,None)
                    rows[key]={'campaign':str(expected.relative_to(self.root)),'task':native,'episodes':[],
                               'discovery_source':oref}
                    break
        # Stable IDs derive from the validated basename; the original six IDs and order never move.
        self.simple_catalog.update(sorted(extra.items()))
        return rows,ref

    def physical_evidence(self,episode):
        """Only public result/action receipts, never a preflight, reset, or manifest counter alone."""
        result,_=self.read(episode/'result.json')
        if (number(result.get('actions')) or 0)>0:return True
        return self.latest_physical_action(episode)[1] is not None

    def latest_physical_action(self,episode):
        """Completed public physical receipts; empty/pending records are not actions."""
        for p in reversed(self.files(episode/'rollout/episode','execution_[0-9][0-9][0-9][0-9].json')):
            data,_=self.read(p)
            receipts=data.get('receipts',[])
            if int(p.stem.split('_')[-1])>0 and isinstance(receipts,list) and any(isinstance(x,dict) and isinstance(x.get('command_id'),str) and (number(x.get('duration_s')) or 0)>0 for x in receipts):
                return int(p.stem.split('_')[-1]),self.read(p)[1]
        return None,None

    def preview(self,folder,key):
        for obs in reversed(self.files(folder/'rollout/episode/observations','[0-9][0-9][0-9][0-9]')):
            d,ref=self.read(obs/'observation.json')
            if not ref: continue
            for name in ['head_stereo_left.png','head_cam.png','head_rgb.png','rgb.png']:
                p=obs/name
                try:
                    self.safe(p); st=p.stat()
                    if st.st_size<64 or st.st_size>20*1024*1024:continue
                    with p.open('rb') as f:
                        if f.read(8)!=b'\x89PNG\r\n\x1a\n':continue
                        f.seek(-12,2)
                        if f.read(12)!=b'\x00\x00\x00\x00IEND\xaeB`\x82':continue
                    # Observations are immutable exports. Identity/version is pinned in URL.
                    route='/media/'+key+'-'+folder.name+'-'+obs.name+'-'+str(st.st_mtime_ns)+'.png'
                    self.media[route]=(p,signature(p))
                    return {'url':route,'at':st.st_mtime,'time_basis':'公开观测文件生成时间',
                            'action':int(obs.name),'sim_s':number(d.get('sim_s')),'episode':folder.name,
                            'view':'策略原始头部左目' if name=='head_stereo_left.png' else '策略原始头部相机',
                            'source':str(p.relative_to(self.root)), 'label':'最新画面（非连续视频）'}
                except (OSError,ValueError): pass
        return None

    def completed_video(self,folder,key,result_ref,view):
        if not result_ref: return None
        p=folder/'video/episode.mp4'
        try:
            self.safe(p); sig=signature(p); cache=self.probes.get(str(p))
            if cache and cache['sig']==sig and cache['result']==result_ref['sha256']:
                return cache['value']
            # A closed result must postdate the recording. No probing open recorders.
            if p.stat().st_mtime>result_ref['at']+1:return None
            probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                'format=duration:stream=width,height,codec_name','-of','json',str(p)],capture_output=True,timeout=8,check=True)
            d=json.loads(probe.stdout); s=d['streams'][0]; duration=float(d['format']['duration'])
            if duration<=0 or signature(p)!=sig:raise ValueError('not sealed')
            route='/media/'+key+'-'+folder.name+'-'+str(sig[3])+'.mp4'
            v={'url':route,'episode':folder.name,'at':p.stat().st_mtime,'duration_s':duration,
               'width':s['width'],'height':s['height'],'view':view,
               'source':str(p.relative_to(self.root)),'result_sha256':result_ref['sha256'],
               'timing':'连续物理录像；推理时物理暂停，录像时长不是墙钟时长。',
               'verified':'已封口结果 + ffprobe可读 + 文件签名缓存'}
            self.media[route]=(p,sig); self.probes[str(p)]={'sig':sig,'result':result_ref['sha256'],'value':v}
            return v
        except (OSError,ValueError,KeyError,IndexError,subprocess.SubprocessError):
            # Negative cache avoids probing the same damaged recording every poll.
            try:self.probes[str(p)]={'sig':signature(p),'result':result_ref['sha256'],'value':None}
            except OSError:pass
            return None

    def media_file(self,route):
        with self.lock:
            if route.startswith('/videos/ikea-'):return self.ikea_media.video(route)
            item=self.media.get(route)
            if not item:return None
            p,sig=item;self.safe(p)
            if signature(p)!=sig:return None
            return p,p.stat()

    def case_media(self, record_id):
        record=self.records.get(record_id)
        if not record:return None
        task=record['task'];ep=record['episode']
        if task=='simple':
            key=record['subtask'];entry=self.simple_catalog.get(key)
            if not entry or not isinstance(ep,str) or not EP.fullmatch(ep):return None
            folder=self.root/'artifacts/R019'/entry[1]/ep;media_key='simple-'+key
        elif task=='ground':folder=self.root/'api-ground-to-table/actor-adapter/campaign'/ep;media_key='ground'
        elif task=='ikea':folder=self.root/'ikea/campaign'/ep;media_key='ikea'
        else:return None
        _,ref=self.read(folder/'result.json')
        video=self.completed_video(folder,media_key,ref,'公开连续录像；额外诊断相机与策略相机分开解释。')
        preview=self.preview(folder,media_key)
        return {'folder':folder,'video':video,'preview':preview}

    @staticmethod
    def terminal(d,review):
        stop=d.get('stop_reason') or ''; kind=d.get('episode_terminal_kind',d.get('terminal_kind'))
        if review.get('audited_task_success') is True:return 'episode-complete'
        if kind=='host_audited_success':return 'episode-complete'
        if stop in ('episode_step_budget','episode_budget') or kind=='budget_limited_incomplete':return 'budgetstop'
        if 'safety' in stop or kind=='safety_stop':return 'safetystop'
        if d.get('error') or kind=='infrastructure_error':return 'infraerror'
        if stop in ('policy_declared_stall','policy_early_stop') or kind in ('agent_stopped_incomplete','adapter_stopped_incomplete'):return 'earlystop'
        if kind=='physical_failure' or d.get('native_outcome') in ('failure','failed'):return 'physical-failure'
        return 'review'

    def simple(self):
        supervisor,sref=self.read(self.root/'codex-account-2/continuation/supervisor-state.json')
        campaign_public,cref=self.simple_campaign_public();progress_public,mref=self.simple_progress_text()
        handoff,href=self.read(self.root/'human-feedback/dashboard-upgrade/root-simple-recovery-handoff.json')
        interruption,iref=self.read(self.root/'artifacts/R019/recovery-20260916/door15-interruption.json')
        history_note=None
        if iref and interruption.get('termination_class')=='infrastructure_interruption' and public_time(interruption,iref)>=public_time(handoff,href):
            history_note='负责人报告：旧推门15因主机重启中断，缺完整回合终态；保留原动作与未封口录像，不计物理失败。'
            if interruption.get('last_ack',{}).get('stop_reason')=='episode_step_budget':
                history_note+='最后物理回执已到预算边界；随后中断的是完整回合收尾。'
        elif href and handoff.get('state')=='infrastructure_error':
            history_note='负责人报告：'+(public_text([handoff],'current_problem') or '旧推门15发生基础设施中断。')
        prerequisite,pref0=self.read(self.root/'artifacts/architecture-review-20260916/status-evidence.json')
        cube=prerequisite.get('tasks',{}).get('table_cube',{})
        prerequisite_note=(f"前置桌面抓取：{cube['verified']}次原生成功（终态仍持有{cube['endpoint_retained']}次），学习成绩"
                           if number(cube.get('verified')) is not None and number(cube.get('endpoint_retained')) is not None else None)
        rows=[]
        for key,(name,campaign,goal) in self.simple_catalog.items():
            folder=self.root/'artifacts/R019'/campaign
            prog,pref=self.read(folder/'progress.json'); episodes=[p for p in self.files(folder,'episode-*') if EP.fullmatch(p.name)]
            campaign_doc=campaign_public.get(key,{})
            if key=='oven':
                # One bounded extension, only after actual physical evidence. Preparation is not an attempt.
                if prog.get('task') not in (None,OVEN_TASK):continue
                attempted=False
                for e in episodes:
                    rd,_=self.read(e/'result.json')
                    if (number(rd.get('actions')) or 0)>0:attempted=True;break
                    if any(self.read(p)[0] and int(p.stem.split('_')[-1])>0 for p in self.files(e/'rollout/episode','execution_[0-9][0-9][0-9][0-9].json')):attempted=True;break
                if not attempted:continue
            refs=[x for x in [pref] if x]; latest=episodes[-1] if episodes else None
            if campaign_doc and cref:refs.append(cref)
            if campaign_doc.get('discovery_source'):refs.append(campaign_doc['discovery_source'])
            campaign_episode=next((x for x in campaign_doc.get('episodes',[]) if isinstance(x,dict) and latest and x.get('episode_id')==latest.name),{})
            prose=progress_public.get(campaign,{})
            if not latest or prose.get('episode_id')!=latest.name:prose={}
            if prose and mref:refs.append(mref)
            results=[]; videos=[]; audits=[]
            for e in episodes:
                d,ref=self.read(e/'result.json')
                review,rref=self.read(e/'success_review.json')
                if not rref:review,rref=self.read(e/'failure_review.json')
                if ref:
                    state=self.terminal(d,review);results.append((e,d,ref,review,state)); refs.append(ref)
                    if rref:refs.append(rref)
                    if review.get('audited_task_success') is True:audits.append(e.name)
                    rec={'id':'simple/'+key+'/'+e.name,'task':'simple','subtask':key,'episode':e.name,
                         'result_sha256':ref['sha256'],'state':state,'actions':number(d.get('actions')),
                         'reset_id':review.get('reset',{}).get('reset_id'),
                         'independent_reset_verified':review.get('independent_reset_verified') is True,
                         'no_replay_or_diagnostic_initial_state':review.get('no_replay_or_diagnostic_initial_state') is True,
                         'control_version':review.get('control_version'), 'mechanism':review.get('mechanism'),
                         'skill_version':d.get('starting_skill_sha256'),'human_feedback_used':d.get('human_feedback_used')}
                    self.records[rec['id']]=rec
            # Only newest playable recording per known scenario; older fallback remains honest.
            for e,d,ref,review,state in reversed(results):
                v=self.completed_video(e,'simple-'+key,ref,'SIMPLE / MuJoCo 连续录像；含额外诊断视角，区别于策略左目预览。')
                if v:v=dict(v,outcome=LABELS[state],task=name); videos=[v];break
            current=next((x for x in results if x[0]==latest),None)
            preview=self.preview(latest,'simple-'+key) if latest else None
            public,uref=self.read(latest/'public-progress.json') if latest else ({},None)
            if uref:refs.append(uref)
            state=current[4] if current else {'inference_waiting':'modelwaiting','inference_waiting_no_deadline':'modelwaiting','action_executing':'physicsrunning','infrastructure_error':'infraerror','connection_unverified':'active-unknown','budget_stop':'budgetstop','safety_stop':'safetystop'}.get(public.get('state'),'active-unknown' if latest else 'unknown')
            # A terminal result ends the old activity phase even if its polling summary was written later.
            active_markers=('inference_waiting','inference_waiting_no_deadline','action_executing')
            public_summary={} if current and public.get('state') in active_markers else public
            docs=[public_summary,campaign_episode,campaign_doc]
            reported_problem=public_text(docs,'current_problem','problem','blocker')
            reported_next=public_text(docs,'next_step','next')
            if not reported_problem and prose and not current:reported_problem=prose['current_problem']+'当前执行存活未独立核验。'
            # This fixed coordination fallback concerns only the interrupted old episode.
            # A later owner publication takes precedence; never carry the interruption to a new reset.
            if key=='door' and latest and latest.name=='episode-0015' and not current:
                fallback_doc,fallback_ref=(interruption,iref) if iref and history_note and public_time(interruption,iref)>=public_time(handoff,href) else (handoff,href)
                if fallback_ref and history_note and public_time(public,uref)<=public_time(fallback_doc,fallback_ref):
                    state='infraerror';reported_problem=history_note
                    reported_next='由 SIMPLE 执行者核对恢复边界；旧动作不重放，保留中断记录。'
                    refs.append(fallback_ref)
            if key=='door' and history_note:
                refs.extend(x for x in (iref,href) if x and x not in refs)
            # Campaign's reviewed aggregate is authoritative; do not reinterpret raw native success.
            count=number(prog.get('successes')) if pref else number(supervisor.get('counts',{}).get(campaign,{}).get('audited_successes'))
            audited_count=number(campaign_doc.get('audited_task_successes'))
            if audited_count is not None and (count is None or (cref and cref['at']>=(pref['at'] if pref else 0))):count=audited_count
            if count is None and audits:count=len(audits)
            action,eref=self.latest_physical_action(latest) if latest else (None,None)
            last_action=eref['at'] if eref else None
            if eref:refs.append(eref)
            if action is None:action=number(current[1].get('actions')) if current else number(campaign_episode.get('actions'))
            if last_action is None:last_action=prose.get('last_action_at')
            problems={'door':'推门目标尚未达到；保持完整回合，并审查独立重置与终态保持。','apple':'尚未验证稳定抓持、搬运与放置；已有 H001 第四条侧抓反馈。','faucet':'尚未验证受控开启；接触与支撑稳定性仍需核对。','boxpick':'拾箱已有审计成功；不等于搬运或放置成功。','boxplace':'尚未完成包夹、抬起、搬运与释放；旧原生成功曾被任务审查否决。'}
            problems['oven']='烤箱尝试须独立任务审计；原生成功不自动计为已验收。'
            if current and current[4]=='review' and not reported_problem:
                reported_problem='回合已封口，独立任务审计尚未确认；原生结果不自动计入任务成功。'
            if current and not reported_next:reported_next='下一步尚未上报；由 SIMPLE 执行者审查封口结果和适用任务合同。'
            row={'id':key,'name':name,'state':state,'state_label':('物理回合预算到界 · 未完成' if state=='budgetstop' else LABELS[state]),'success':count,'goal':goal,
                 'episode':latest.name if latest else None,'actions':action,'last_action_at':last_action,
                 'source_at':max([x['at'] for x in refs],default=None),'sources':refs,
                 'problem':reported_problem or ('执行者尚未上报当前卡点。当前回合终态和执行状态未确认。' if state=='active-unknown' else '执行者尚未上报当前卡点。'+problems.get(key,'独立任务审计与适用合同仍需核对；原生结果不自动计分。')),
                 'next':reported_next or ('下一步尚未上报；由SIMPLE执行者核对在途turn/进程，再决定同回合续接。' if state=='active-unknown' else '下一步尚未上报；执行者在自然边界审查公开结果，不截断在途推理。'),
                 'recovery_note':history_note if key=='door' else None,
                 'who':'SIMPLE 执行者','backend':'SIMPLE / MuJoCo' if preview or results else '未知',
                 'mode':'学习 / 人工反馈 H001-004' if current and current[1].get('human_feedback_used') else '技能学习；非冻结测评',
                 'variant':'门框碰撞修复变体；不是原始未修改场景' if key=='door' else 'SIMPLE 对应任务；四点控制',
                 'preview':preview,'videos':videos,'completed_episodes':len(results),
                 'video_note':('当前回合尚无封口结果；显示上一完整录像。' if not current else '当前回合录像已封口。') if videos else '尚无通过封口与播放检查的完整录像。'}
            if count is not None and goal is not None and count>=goal:row['state']='complete';row['state_label']=LABELS['complete']
            rows.append(row)
        allrefs=[sref] if sref else []
        if pref0:allrefs.append(pref0)
        for row in rows:allrefs.extend(row['sources'])
        running=[x for x in rows if x['state'] in ('modelwaiting','physicsrunning','active-unknown')]
        state=running[0]['state'] if running else ('infraerror' if any(x['state']=='infraerror' for x in rows) else 'review')
        summary={'id':'simple','name':'SIMPLE测评','state':state,'state_label':LABELS[state],
                'summary':'推门 '+str(rows[0]['success'] if rows[0]['success'] is not None else '未知')+'/10；拾箱 '+str(rows[3]['success'] if rows[3]['success'] is not None else '未知')+'/1。其余见分任务。',
                'problem':'管理状态可能滞后；以下按回合结果与公开动作逐项核对。',
                'next':'自然边界续接与任务审查；优先推进推门。','who':'SIMPLE 执行者','subtasks':rows,
                'source_at':max([x['at'] for x in allrefs],default=None),'sources':allrefs,
                'last_action_at':max([x['last_action_at'] for x in rows if x['last_action_at']],default=None),
                'supervisor_at':timestamp(supervisor.get('updated_utc')),'mode':'技能学习；与冻结测评分开',
                'backend':'SIMPLE / MuJoCo','variant':'推门计数来自明确声明的碰撞修复变体',
                'prerequisite_note':prerequisite_note,'preview':None,'videos':[]}
        return self.six_task_focus(summary,campaign_public,supervisor,sref)

    def six_task_focus(self,row,campaigns,supervisor,sref):
        """Exact benchmark view over existing campaigns; original records/media IDs stay intact."""
        mapping,mref=self.read(self.root/'artifacts/architecture-review-20260916/six-task-focus/benchmark-mapping-evidence.json')
        if not mref or mapping.get('mapping')!=SIX_TASKS:return row
        baseline,baseline_ref=self.read(self.root/'ref/SIMPLE_OFFICIAL_BASELINE_20260916.json')
        row['official_baseline']=official_baseline(baseline,list(SIX_TASKS))
        if baseline_ref:row['sources'].append(baseline_ref)
        row['benchmark_plan']={'tasks':6,'levels':['L0','L1','L2'],'per_level':10,'per_task':30,'total':180,
            'alignment_state':'pending','learning_runtime_state':'未核验：持续学习指令不等于运行时已修改'}
        runtime,rrefs=self.central_learning_publication()
        row['benchmark_plan']['learning_runtime']=runtime
        row['benchmark_plan']['learning_runtime_state']=runtime['note']
        row['sources'].extend(rrefs)
        historical=row['subtasks']; old_by_id={x['id']:x for x in historical}; targets=[]
        scope=supervisor.get('six_task_focus') if isinstance(supervisor.get('six_task_focus'),dict) else supervisor
        acknowledged=scope.get('ack')=='SIX-TASK-FOCUS-20260916 ACK' and scope.get('benchmark_mapping')==SIX_TASKS
        scope_registered=supervisor.get('current_scope')==SIX_TASKS
        owner_ack,aref=self.read(self.root/'artifacts/R019/six-task-focus/supervisor-ack.json')
        if (scope_registered and owner_ack.get('ack')=='SIX-TASK-FOCUS-20260916 ACK'
            and owner_ack.get('mapping')==SIX_TASKS and owner_ack.get('owner_thread')=='01a0a867-d7aa-71f2-8547-e264d6d09ede'):
            acknowledged=True
        if aref:row['sources'].append(aref)
        scope_note=('主管已确认六项精确入口；'+(public_text([scope],'current_problem','problem') or '当前调度卡点尚未上报。') if acknowledged else
                    '主管公开状态已登记六项精确入口；明确调度 ACK 与新回合 / skill 加载仍未上报。' if scope_registered else
                    '六项要求已下发；待主管调度确认。排队不等于 ACK，尚未确认新回合或 skill 加载。')
        scope_note+=' 历史学习/人工辅助成绩与当前新冻结测评分开；其他入口只保留历史与在途收尾。'
        for index,(name,native) in enumerate(SIX_TASKS.items()):
            matches=[]; refs=[mref];candidate=None
            for key,campaign in campaigns.items():
                if campaign.get('native_env_id',campaign.get('task'))!=native or key not in old_by_id:continue
                folder=self.root/'artifacts/R019'/self.simple_catalog[key][1]
                campaign_status,cref=self.read(folder/'progress.json')
                if cref:refs.append(cref)
                if isinstance(campaign_status.get('candidate_manifest'),dict):candidate=campaign_status['candidate_manifest']
                entries=campaign.get('episodes')
                ledger={e.get('episode_id'):e for e in entries if isinstance(e,dict) and isinstance(e.get('episode_id'),str)} if isinstance(entries,list) else {}
                # Aggregate membership is metadata, not a freshness gate. Restrict
                # discovery to direct episodes of this already validated campaign.
                for episode in self.files(folder,'episode-*'):
                    if not EP.fullmatch(episode.name) or not self.physical_evidence(episode):continue
                    ep=ledger.get(episode.name,{})
                    result,rref=self.read(episode/'result.json');review,vref=self.read(episode/'success_review.json')
                    if not vref:review,vref=self.read(episode/'failure_review.json')
                    scene,eref=self.read(episode/'video/scene_setup.json');public,pref=self.read(episode/'public-progress.json')
                    budget,bref=self.read(episode/'policy_instruction_budget.json')
                    evaluation,qref=self.read(episode/'evaluation-manifest.json')
                    # Recorder env_id is the actual native entry alias. Only identity and
                    # assistance fields are projected, never scene objects, poses or audit bodies.
                    identities=[v for v in (result.get('native_env_id'),scene.get('native_env_id',scene.get('env_id')),
                                           public.get('native_env_id'),review.get('native_env_id',review.get('task'))) if v is not None]
                    if not identities or any(v!=native for v in identities):continue
                    audit=bool(rref and vref and review.get('audited_task_success') is True
                               and review.get('task',review.get('native_env_id'))==native
                               and isinstance(review.get('reset'),dict) and review['reset'].get('reset_id'))
                    flags=[d.get('human_feedback_used') for d in (result,review,scene,ep)]
                    assisted=True if any(v is True for v in flags) else False if any(v is False for v in flags) else None
                    feedback=[v for d in (result,review) for v in (d['human_feedback_sources'] if isinstance(d.get('human_feedback_sources'),list) else []) if isinstance(v,dict)]
                    h001=any(v.get('path') in ('human-feedback/H001-user-feedback-004.json',str(self.root/'human-feedback/H001-user-feedback-004.json')) for v in feedback)
                    evidence_refs=[v for v in (rref,vref,eref,pref,bref,qref) if v];refs.extend(evidence_refs)
                    action,xref=self.latest_physical_action(episode)
                    last_action=xref['at'] if xref else None
                    if xref:refs.append(xref)
                    if action is None:action=number(result.get('actions'))
                    matches.append({'key':key,'folder':episode,'episode':episode.name,'audit':audit,'assisted':assisted,
                                    'h001':h001,'result':result,'result_ref':rref,'review':review,'public':public,
                                    'public_ref':pref,
                                    'scene':scene,'budget':budget,'ledger':ep,'evaluation':evaluation,
                                    'last_action_at':last_action,'actions':action,
                                    'order':last_action or (rref['at'] if rref else eref['at'] if eref else 0)})
            base={'id':'benchmark-'+str(index+1),'name':name,'native_env_id':native,'goal':1,'success':None,
                  'state':'unknown','state_label':'未开始 / 待适配（未见精确证据）','actions':None,'episode':None,
                  'source_at':mref['at'],'sources':refs,'last_action_at':None,'preview':None,'videos':[],
                  'problem':'未发现精确入口的可核验物理记录；当前执行状态尚未上报。',
                  'next':'由 SIMPLE 唯一主管核对原生任务/控制与验收合同，按精确入口适配；不以相近变体替代。',
                  'who':'SIMPLE 唯一主管','backend':'尚未上报','mode':'当前六项范围；新冻结测评成绩未上报',
                  'variant':'精确原生入口：'+native,'historical_audited_successes':None,
                  'historical_assisted_successes':None,'historical_autonomous_successes':None,
                  'summary':name+'：精确入口尚无物理记录；当前新冻结测评成绩未知。',
                  'video_note':'尚无匹配精确入口的封口录像。','nav_label':name+' · 未开始 / 待适配'}
            if matches:
                matches.sort(key=lambda x:(x['order'],x['episode']))
                newest_by_campaign={}
                for match in matches:
                    previous=newest_by_campaign.get(match['key'])
                    if previous is None or int(match['episode'].split('-')[1])>int(previous['episode'].split('-')[1]):newest_by_campaign[match['key']]=match
                latest=max(newest_by_campaign.values(),key=lambda x:x['order']); original=old_by_id[latest['key']]
                for field in ('state','state_label','actions','last_action_at','source_at','backend','problem','next'):
                    base[field]=original[field]
                base['actions']=latest['actions'];base['last_action_at']=latest['last_action_at']
                if original['episode']!=latest['episode']:
                    base['state']='active-unknown';base['state_label']=LABELS['active-unknown']
                    base['problem']=public_text([latest['public']],'current_problem','problem') or '当前精确入口阶段尚未上报。'
                    base['next']=public_text([latest['public']],'next_step','next') or '由主管核对精确入口的回合终态。'
                base['episode']=latest['episode'];base['sources']=original['sources']+refs
                base['source_at']=max([v['at'] for v in base['sources']],default=None)
                base['preview']=self.preview(latest['folder'],'simple-'+latest['key'])
                for match in reversed(matches):
                    video=self.completed_video(match['folder'],'simple-'+match['key'],match['result_ref'],
                                               'SIMPLE 连续物理录像；外部诊断视角与策略相机分开。')
                    if video:
                        base['videos']=[dict(video,task=name,outcome='精确入口学习记录；人工反馈辅助' if match['assisted'] else '精确入口学习记录')];break
                audited=list({x['review']['reset']['reset_id']:x for x in matches if x['audit']}.values());assisted=sum(x['assisted'] is True for x in audited)
                autonomous=sum(x['assisted'] is False for x in audited);unknown=len(audited)-assisted-autonomous
                base.update(historical_audited_successes=len(audited),historical_assisted_successes=assisted,
                            historical_autonomous_successes=autonomous,historical_assistance_unknown=unknown)
                base['mode']='学习记录；当前范围与历史成绩分列；'+('人工反馈 H001-004 辅助' if any(x['h001'] for x in matches) else '人工反馈辅助单列' if any(x['assisted'] is True for x in matches) else '辅助信息按回合记录')+'；非冻结测评'
                base['summary']=f'{name}：精确入口历史审计成功 {len(audited)}（无辅助 {autonomous}、人工辅助 {assisted}'+(f'、辅助类型未知 {unknown}' if unknown else '')+'）；当前新冻结测评成绩未上报。'
                base['video_note']='仅显示精确入口已封口录像；历史成功不等于本轮新冻结测评。'
                phase_ref=latest['public_ref']
                current_public=latest['public'] if phase_ref and phase_ref['at']>=(latest['last_action_at'] or 0) else {}
                state_map={'inference_waiting':'modelwaiting','inference_waiting_no_deadline':'modelwaiting','action_executing':'physicsrunning',
                           'infrastructure_error':'infraerror','connection_unverified':'active-unknown','budget_stop':'budgetstop','safety_stop':'safetystop'}
                base['phase_report_at']=phase_ref['at'] if current_public else None
                if latest['result_ref']:
                    base['state']=self.terminal(latest['result'],latest['review'])
                    base['state_label']=LABELS[base['state']]
                    if base['state']=='review':base['state_label']='回合已封口；完整任务审计未通过或待核验'
                    current_public={}  # Sealed result wins residual activity and problem text.
                    base['problem']='本回合已封口；原生结果与完整任务审计分别计数。冻结测评尚未启动。'
                    base['next']='由原负责人按完整任务审计修订学习；新候选须重新登记，旧成功不回填。'
                else:
                    base['state']=state_map.get(current_public.get('state'),'active-unknown')
                    base['state_label']=('最近上报：'+LABELS[base['state']]+'；存活未独立核验' if current_public else LABELS['active-unknown'])
                    base['problem']=f"{name} 本回合已有 {latest['actions'] if latest['actions'] is not None else '未知'} 个动作，尚无封口结果；精确阶段未上报，当前存活未独立核验。"
                    base['next']='保留当前回合，由原负责人完整收尾并审计；不重放已执行动作。'
                base['problem']=public_text([current_public],'current_problem','problem','blocker') or base['problem']
                base['next']=public_text([current_public],'next_step','next') or base['next']
                base['recent_audit_note']=None
                for prior in reversed(matches):
                    v=prior['review'];stages=v.get('independently_verified_stages',{})
                    if (name=='Handover' and v.get('audited_task_success') is False and v.get('native_success') is True
                        and isinstance(stages,dict) and stages.get('release_and_supported_destination_placement') is False
                        and all(isinstance(stages.get(k),dict) and (number(stages[k].get('samples')) or 0)>0
                            for k in ('right_unsupported_hold','giver_clear_left_unsupported_hold'))):
                        base['recent_audit_note']=prior['episode']+'：转交阶段审计通过，但未完成释放放置；原生成功不等于完整任务成功。'
                        break
                base['summary']=f"{name} · {base['episode']} · 动作 {base['actions'] if base['actions'] is not None else '未知'} · {base['state_label']}。"+(base['recent_audit_note'] or '')
                base['nav_label']=name+' · '+('历史已审计' if latest['audit'] else '已有物理记录')
            base['scorecard']=scorecard(matches,native,owner_ack.get('effective_utc','2026-09-16T12:28:40.091351+00:00'),candidate)
            targets.append(base)
        row['history_subtasks']=[dict(x,summary='历史 / 迁移记录：'+(x.get('summary') or f'{x["name"]}，历史审计成功 {x["success"] if x["success"] is not None else "未知"}；不计当前六项新测评。')) for x in historical]
        row.update(subtasks=targets,focus_acknowledged=acknowledged,focus_scope_registered=scope_registered,scope_notice=scope_note,
                   summary='本阶段仅六项精确入口；历史学习与新冻结测评分开。',
                   state='engineering-prep',state_label='六项范围已确认；'+('主管已 ACK' if acknowledged else '主管已登记范围；待调度 ACK' if scope_registered else '待主管调度确认'),
                   problem=scope_note,next=public_text([scope],'next_step','next') if acknowledged else '仅推进六项精确入口；非目标在途完整收尾后不续开。',
                   variant='SIMPLE 原始六项 benchmark；相关变体只作历史/迁移证据',mode='学习与冻结测评分开')
        row['sources'].append(mref);row['source_at']=max(row.get('source_at') or 0,mref['at'])
        if row.get('prerequisite_note'):row['prerequisite_note']='历史迁移证据 · '+row['prerequisite_note']+'；不计本阶段六项原生成绩。'
        return row

    def central_learning_publication(self):
        """Fixed engineering receipts, never follow release/first-evidence paths."""
        folder=self.root/'artifacts/architecture-review-20260916/central-skill-publication'
        pub,pref=self.read(folder/'publication-receipt.json')
        integration,iref=self.read(folder/'runtime-integration-receipt.json')
        load,lref=self.read(folder/'first-load-status.json')
        pointer=pub.get('pointer') if isinstance(pub.get('pointer'),dict) else {}
        digest=pointer.get('manifest_sha256');release=pointer.get('release_id')
        published=pub.get('status')=='published' and isinstance(digest,str) and bool(re.fullmatch('[a-f0-9]{64}',digest))
        integrated=published and pub.get('shared_runner_integrated') is True and integration.get('status')=='integrated_for_next_launch'
        # Current explicit receipt is a pending-load contract. A future positive
        # schema needs its actual episode/hash binding checked, not a guessed flag.
        pending=(published and load.get('release_sha256')==digest and load.get('actual_actor_load_confirmed') is False
                 and pub.get('first_physical_load_confirmed') is False)
        note=('中央技能源码已发布；'+('运行入口已集成，下一自然边界加载。' if integrated else '运行入口集成待确认。')+
              ('首次物理加载待确认。' if pending else '首次物理加载证据未确认。') if published else '持续学习与中央技能发布状态待确认。')
        note+='旧 240 秒批次不回填新版五次准入；源码发布不代表物理加载或任务收益。'
        return {'source_published':bool(published),'runtime_integrated':bool(integrated),'physical_load_confirmed':False if pending else None,
                'release_id':release if isinstance(release,str) and re.fullmatch('[a-zA-Z0-9_-]{1,80}',release) else None,
                'at':pref['at'] if pref else None,'note':note},[r for r in (pref,iref,lref) if r]

    def verified_user_pause(self,row):
        """Public verified process disposition, never a PAUSE marker or heartbeat inference."""
        if row['id'] not in ('ikea','ground'):return row
        pause,ref=self.read(self.root/'artifacts/architecture-review-20260916/six-task-focus/pause-status.json')
        branch=pause.get(row['id']);at=timestamp(pause.get('verified_at'))
        if not ref or not isinstance(branch,dict) or pause.get('classification')!='user_requested_pause' or pause.get('all_requested_branches_paused') is not True:return row
        if branch.get('actor_alive') is not False or pause.get('no_automatic_resume') is not True:return row
        if row['id']=='ikea' and not all(branch.get(k) is False for k in ('actor_app_server_alive','continuation_owner_alive','continuation_watcher_alive')):return row
        if row['id']=='ground' and (branch.get('owner_alive') is not False or branch.get('watcher_state')!='blocked_zero_model_sleep_no_children'):return row
        if row.get('episode') not in (None,branch.get('episode')) or (at and row.get('last_action_at') and row['last_action_at']>at):return row
        historical={k:row.get(k) for k in ('state_label','episode','problem','next','source_at')}
        if row['id']=='ikea' and isinstance(branch.get('raw_error_preserved'),dict) and branch['raw_error_preserved'].get('type')=='EOFError':
            historical['problem']='暂停前末记录：系统/接口中断（EOF）；原回执保留。'+(historical['problem'] or '')
        row.update(state='paused',state_label='用户已暂停（已核验）',pause_reason='user_requested_pause',pause_verified_at=at or ref['at'],
                   historical_status=historical,problem='用户要求暂停；公开核验确认执行进程已退出。用户暂停不计物理失败或成功。',
                   next='保持暂停，保留原回合影像与未知请求；未经用户恢复不自动续开，不重发未知结果。',who='原负责人保全证据；等待用户恢复',
                   source_at=at or ref['at'],source_time_note='此时间为用户暂停核验；零模型心跳/监督休眠不是物理执行，最近实际动作时间另列。')
        row['summary']='已暂停 · 历史记录：'+row['summary'];row['sources'].append(ref)
        return row

    def ground(self):
        a=self.api.snapshot(); current,ref=self.read(self.root/'api-ground-to-table/actor-adapter/auxiliary-progress.json')
        state={'inference_waiting_no_deadline':'modelwaiting','action_executing':'physicsrunning','error':'infraerror','infrastructure_error':'infraerror'}.get(a['state'],'unknown')
        folder=self.root/'api-ground-to-table/actor-adapter/campaign'/a['episode'] if a['episode'] else None
        preview=self.preview(folder,'ground') if folder else None
        last=None; refs=[ref] if ref else []
        if folder:
            for p in reversed(self.files(folder/'rollout/episode','execution_*.json')):
                d,eref=self.read(p)
                if eref and d:last=eref['at'];refs.append(eref);break
        if last is None and number(current.get('last_physical_update_at_unix')) is not None:
            last=current['last_physical_update_at_unix']
        if a['terminal_kind']:state=self.terminal({'terminal_kind':a['terminal_kind']},{})
        videos=[]
        for v in reversed(a['videos']):
            ep=v['id'].removeprefix('api-ground-'); p=self.root/'api-ground-to-table/actor-adapter/campaign'/ep
            videos.append(dict(v,episode=ep,at=(p/'video/episode.mp4').stat().st_mtime,task='地面物块搬运',outcome=v['result_note']))
        for row in a['episodes']:
            ep=row['episode'];e=self.root/'api-ground-to-table/actor-adapter/campaign'/ep
            result,rref=self.read(e/'result.json');review,_=self.read(e/'failure_review.json')
            if rref:
                rec={'id':'ground/'+ep,'task':'ground','episode':ep,'state':self.terminal(result,review),
                     'result_sha256':rref['sha256'],'actions':number(result.get('actions')),
                     'reset_id':review.get('reset',{}).get('reset_id'),
                     'independent_reset_verified':review.get('independent_reset_verified') is True,
                         'no_replay_or_diagnostic_initial_state':review.get('no_replay_or_diagnostic_initial_state') is True,
                     'control_version':review.get('control_version'),'mechanism':review.get('mechanism'),
                     'human_feedback_used':result.get('human_feedback_used')}
                self.records[rec['id']]=rec
        recovery,rref=self.read(self.root/'api-ground-to-table/actor-adapter/recovery-history.json')
        if rref:refs.append(rref)
        recovery_note=('旧回合 episode-0002 因主机重启中断，录像未封口；公开计数23动作，但独立完整回执只到22。不计物理失败。' if recovery.get('old_episode')=='episode-0002' and recovery.get('stop_reason')=='host_reboot_infrastructure_interruption' else None)
        delivery_note='网页新增回答通知已核实的现任搬运负责人；历史回答不自动重投。保存、排队、负责人确认与物理验证分别记录。'
        problem=None; next_step=None; source_at=a['updated_at_unix']
        disposition,dref=self.read(self.root/'api-ground-to-table/recovery-20260916/progress.json')
        # Recovery details are scoped to the selected episode, never a global sticky blocker.
        episode=a['episode']; candidates=[(current,ref)]
        if (episode and current.get('episode')==episode and disposition.get('episode')==episode
                and (not current.get('run_id') or not disposition.get('run_id') or current['run_id']==disposition['run_id'])):
            candidates.append((disposition,dref))
        candidates.sort(key=lambda x:public_time(*x),reverse=True)
        for doc,sref in candidates:
            if not episode or doc.get('episode')!=episode:continue
            # A later explicit activity or different disposition supersedes the older 429.
            if doc.get('state') in ('action_executing','inference_waiting_no_deadline'):break
            blocker=doc.get('blocker'); recovery_state=doc.get('recovery_state')
            if blocker=='gateway_http_429' or recovery_state=='blocked_http429_no_automatic_retry':
                if a['terminal_kind'] and state!='infraerror':break
                problem='HTTP 429：网关限制请求。'+(public_text([doc],'recovery_note') or '请求的远端结果与费用尚未确认。')
                if any(d.get('supervisor_blocker')=='blocked_owner_disposition' for d,_ in candidates):
                    problem+=' 监督补充：自动接续暂停，待负责人处理。'
                next_step=public_text([doc,current],'next_step','next') or '由当前搬运负责人核对请求实际结果与后续处理；未知请求不重发。'
                state='infraerror'
                if sref and sref not in refs:refs.append(sref)
                source_at=max(source_at or 0,public_time(doc,sref))
                break
            if blocker and blocker!='blocked_owner_disposition':break
        return {'id':'ground','name':'地面物块搬运','recovery_note':recovery_note,'delivery_note':delivery_note,'state':state,'state_label':LABELS[state],
            'summary':f"最近公开记录：{a['actions'] if a['actions'] is not None else '未知'} 个动作；抓取、携带、放置尚未验证。",
            'problem':problem or public_text([current],'current_problem','problem','blocker','recovery_note') or ('执行者尚未上报当前卡点。最近公开阶段为完整推理等待；当前存活未独立核验。' if state=='modelwaiting' else ('负责人报告主机重启中断；原回合尚无终态，未知结果不重发。' if current.get('stop_reason')=='host_reboot_infrastructure_interruption' else '执行者尚未上报当前卡点。'+str(a['terminal_label'] or '当前执行状态未确认。'))),
            'next':next_step or public_text([current],'next_step','next') or ('下一步尚未上报；恢复负责人保全回合证据并核对续接条件；不重放未知结果动作。' if state=='infraerror' else '下一步尚未上报；由搬运执行者核对实际结果与自然边界。'),'who':'搬运执行者',
            'source_at':source_at,'source_time_note':'此时间是管理恢复记录；最近物理动作时间独立显示。' if current.get('recovery_state') or problem else None,'sources':refs,'last_action_at':last,
            'episode':a['episode'],'backend':a['backend'],'mode':'学习；F001 反馈已收到，是否用于本回合由执行者记录',
            'variant':'地面块 → 原桌面；推理期间物理暂停' if a['physics_paused'] else '地面块 → 原桌面',
            'preview':preview,'videos':videos[:1],'video_note':('当前录像损坏、未封口；仅显示先前完整录像。' if current.get('current_video_status')=='unsealed_ffprobe_failed_moov_atom_missing' else '当前回合未封口；显示最近完成录像。') if not a['terminal_kind'] else '最近已完成录像。',
            'success':None,'goal':1,'subtasks':[]}

    def ikea(self):
        d,ref=self.read(self.root/'ikea/state.json'); beat,bref=self.read(self.root/'ikea/heartbeat.json')
        pub,pref=self.read(self.root/'ikea/web-progress.json'); actor,aref=self.read(self.root/'ikea/actor-progress.json')
        state=('engineering-prep' if d.get('actor_running') is False else 'active-unknown') if ref or pref or aref else 'unknown'
        phase=actor.get('phase',pub.get('policy_state',pub.get('phase')))
        state={'inference_waiting':'modelwaiting','inference_waiting_no_deadline':'modelwaiting','action_executing':'physicsrunning','safety_stop':'safetystop','budget_stop':'budgetstop','infrastructure_error':'infraerror'}.get(phase,state)
        refs=[x for x in [ref,bref,pref,aref] if x];videos=[];preview=None;last=None
        for e in reversed(self.files(self.root/'ikea/campaign','*')):
            if not re.fullmatch(r'(?:episode|door|apple|fridge|placement)-[0-9]{4,8}',e.name):continue
            result,rref=self.read(e/'result.json')
            if rref:
                refs.append(rref);review,_=self.read(e/'failure_review.json')
                rec={'id':'ikea/'+e.name,'task':'ikea','episode':e.name,'state':self.terminal(result,review),
                     'result_sha256':rref['sha256'],'actions':number(result.get('actions')),
                     'reset_id':review.get('reset',{}).get('reset_id'),
                     'independent_reset_verified':review.get('independent_reset_verified') is True,
                         'no_replay_or_diagnostic_initial_state':review.get('no_replay_or_diagnostic_initial_state') is True,
                     'control_version':review.get('control_version'),'mechanism':review.get('mechanism'),
                     'human_feedback_used':result.get('human_feedback_used')}
                self.records[rec['id']]=rec
            if not preview:preview=self.preview(e,'ikea-'+e.name)
            if e.name==actor.get('episode') and rref:state=self.terminal(result,{})
            if not videos:
                v=self.completed_video(e,'ikea',rref,'IKEA 派生场景连续物理录像；包含外部诊断相机。')
                if v:videos=[dict(v,task='IKEA探索',outcome=LABELS[self.terminal(result,{})])]
            for p in reversed(self.files(e/'rollout/episode','execution_*.json')):
                _,eref=self.read(p)
                if eref:last=max(last or 0,eref['at']);refs.append(eref);break
        manifest_videos,_=self.ikea_media.manifest_videos([])
        if not videos and manifest_videos:
            v=max(manifest_videos,key=lambda x:x['completed_at_unix'])
            if v['category']=='diagnostic' or v.get('source_kind')=='diagnostic':
                task_label='IKEA 工程诊断（非策略尝试）'
                outcome='诊断录像，不计策略成功'
            elif v.get('source_kind')=='policy_incomplete':
                task_label='IKEA 策略尝试（未完成）'
                outcome=(v.get('source_title')+'；' if v.get('source_title') else '')+'策略尝试未完成，未审计成功'
            else:
                task_label='IKEA 策略学习'
                outcome=v['result_note']
            videos=[dict(v,at=v['completed_at_unix'],episode=v['id'].removeprefix('ikea-'),task=task_label,outcome=outcome)]
        for name in ('STATUS.md','INVENTORY.md'):
            p=self.root/'ikea'/name
            try:
                self.safe(p);raw=p.read_bytes()
                if len(raw)<100000:refs.append({'path':'ikea/'+name,'at':p.stat().st_mtime,'sha256':hashlib.sha256(raw).hexdigest()})
            except (OSError,ValueError):pass
        return {'id':'ikea','name':'IKEA探索','state':state,'state_label':LABELS[state],
            'summary':'登记回合 '+str(pub.get('attempts',d.get('physical_attempts','未知')))+'（含重置） · 本回合公开动作 '+str(actor.get('actions','未知'))+' · 审计成功 '+str(pub.get('audited_successes',d.get('audited_successes','未知'))),
            'problem':public_text([pub,actor,d],'current_problem','problem','blocker','engineering_state') or ('执行者尚未上报当前卡点。最近公开阶段为完整推理等待；物理暂停，当前存活未独立核验。' if state=='modelwaiting' else '执行者尚未上报当前卡点；尚无可核验执行状态。'),
            'next':public_text([pub,actor,d],'next_step','next') or '下一步尚未上报；等待执行者更新公开状态。','who':'IKEA 执行者',
            'success':number(pub.get('audited_successes',d.get('audited_successes'))),'goal':None,
            'physical_attempts':number(pub.get('attempts',d.get('physical_attempts'))),
            'source_at':timestamp(actor.get('at')) or timestamp(d.get('updated_at')),'heartbeat_at':timestamp(beat.get('at')),
            'sources':refs,'last_action_at':last,'backend':str(pub.get('backend',d.get('backend','未知')))[:150],
            'mode':'策略学习；诊断次数单列，不计策略成绩' if actor.get('episode') else '工程验证；准备不计策略尝试',
            'variant':'USD 对齐派生无锁舌 v3；不等同原始 USD 场景完整物理验证' if 'v3' in str(pub.get('backend',d.get('backend'))) else '声明的派生无锁舌变体',
            'episode':actor.get('episode'),'preview':preview,'videos':videos,
            'video_note':('工程诊断连续录像，不计策略尝试或成功。' if videos and (videos[0].get('category')=='diagnostic' or videos[0].get('source_kind')=='diagnostic') else '已封口的连续记录；封口只说明录像可播放，不代表任务成功或回合完整完成。') if videos else '尚无通过封口检查的公开连续录像。','subtasks':[]}

    def framework(self):
        base=self.root/'artifacts/architecture-review-20260916'; refs=[]; docs={}
        for name,rel in [('review','result.json'),('memory','memory-priority/result.json'),('continuity','no-truncation/status.json'),('continuity_result','no-truncation/result.json'),('continuity_progress','no-truncation/progress.json')]:
            d,ref=self.read(base/rel);docs[name]=d
            if ref:refs.append(ref)
        d={}
        for name in sorted(('continuity','continuity_result','continuity_progress'),key=lambda name:public_time(docs[name],None)):
            d.update(docs[name])
        result=docs['continuity_result'];delivery=result.get('delivery',{})
        applied=d.get('candidate_applied',delivery.get('integrated')) is True
        delivered=d.get('state') in ('bounded_review_completed_candidate_delivered','complete_candidate_only')
        tests=number(d.get('tests_passed'))
        if tests is None:
            counts=[number(result.get('checks',{}).get(k)) for k in ('focused','existing_adapter','actual_caller_fake_transport_backend')]
            if all(x is not None for x in counts):tests=sum(counts)
        queued=number(d.get('queued_recipients',delivery.get('queued')));ack=number(d.get('acknowledged_recipients',delivery.get('acknowledged')))
        next_step=public_text([d],'next_step','next')
        if next_step=='publisher review and owner validation; bounded reviewer stopped, no monitoring':
            next_step='唯一发布者在自然边界审查集成；各任务执行者确认适配后单独做物理验证。'
        verification=[]
        if tests is not None:verification.append({'name':'离线回归','state':f'{tests}项通过；不代表物理收益'})
        if queued is not None:verification.append({'name':'辅助入口交付','state':f'{queued}个已排队；{ack if ack is not None else "未知"}个确认；排队不等于消费'})
        row={'id':'framework','name':'Skill/Harness优化','state':'engineering-prep' if refs else 'unknown','state_label':'离线验证 / 已交付；待集成与物理验证' if delivered and not applied else LABELS['engineering-prep' if refs else 'unknown'],
            'summary':str(d.get('summary','已读取候选回执；续接审查进度未提供。' if refs else '尚无可核验的公开工程记录。'))[:400],
            'problem':public_text([d],'current_problem','problem','blocker') or '维护者尚未上报当前卡点；候选集成与物理验证须分别确认。',
            'next':next_step or '下一步尚未上报；维护者在自然边界核对候选与适用性，执行者另做物理验证。','who':'框架维护者 / 唯一发布者',
            'source_at':timestamp(d.get('updated_utc')) or max([x['at'] for x in refs],default=None),
            'sources':refs,'last_action_at':None,'backend':'工程审查，无新仿真','mode':'候选评审','variant':'禁止截断完整推理；共享经验按控制合同适配',
            'preview':None,'videos':[],'subtasks':[], 'video_note':'此任务交付代码与验证回执，没有自己的机器人录像。',
            'milestones':[{'name':'主 harness 候选','state':'已集成' if docs['review'].get('deployed_changes') else ('候选未集成' if docs['review'] else '未知 / 未提供')},
                          {'name':'经验优先级候选','state':'已集成' if docs['memory'].get('deployed') else ('候选未集成' if docs['memory'] else '未知 / 未提供')},
                          {'name':'不中断续接审查','state':'已应用（仍需物理验证）' if applied else ('候选已交付；待集成 / 物理验证' if delivered else ('审查中 / 待自然边界' if d else '未知 / 未提供'))}]+verification}
        publisher,pref=self.read(self.root/'artifacts/R019/instruction-cap-integration/status.json')
        if not pref:return self.publication_updates(row)
        applied_ids=publisher.get('applied',[])
        deployed=[(identifier,label) for identifier,label in (
            ('ARCH-REVIEW-20260916-V1','ARCH 组合长度'),
            ('ARCH-MEMORY-PRIORITY-20260916-V1','MEMORY-PRIORITY 检索'),
            ('mujoco-render-frustum-v1','相机标定')) if identifier in applied_ids]
        nt=publisher.get('NT-20260916-v1',{})
        accepted=nt.get('accepted_and_applied','') if isinstance(nt,dict) else ''
        partial_nt=isinstance(accepted,str) and 'Unbounded turn/start ACK wait' in accepted and 'uncertain-submit guard' in accepted
        if not deployed and not partial_nt:return self.publication_updates(row)
        refs.append(pref)
        # Publisher receipts establish deployment; reviewer candidate flags describe a different scope.
        # Never feed the embedded host_review or source-code payload to the page or feedback package.
        replacements={'ARCH-REVIEW-20260916-V1':'主 harness 候选','ARCH-MEMORY-PRIORITY-20260916-V1':'经验优先级候选'}
        replaced={replacements[x] for x,_ in deployed if x in replacements}
        if partial_nt:replaced.add('不中断续接审查')
        milestones=[x for x in row['milestones'] if x['name'] not in replaced]
        milestones=[{'name':label,'state':'SIMPLE 已上线；依据发布者集成回执'} for _,label in deployed]+milestones
        validated=[]
        physical=publisher.get('complete_physical_validation',{})
        for task,label,campaign in [('door','门16','door-campaign'),('faucet','水龙头8','faucet-campaign')]:
            proof=physical.get(task,{}) if isinstance(physical,dict) else {}
            episode=proof.get('episode');expected=self.root/'artifacts/R019'/campaign/('episode-0016' if task=='door' else 'episode-0008')
            if proof.get('audited_task_success') is True and episode in (str(expected),str(expected.relative_to(self.root))):validated.append(label)
        if validated:milestones.append({'name':'真实回合验证','state':'、'.join(validated)+'：真实调用链、受限 skill_update 与独立审计回执；共同变更回归，不能单因归因或泛化。'})
        if partial_nt:
            milestones.append({'name':'NT 连续性保护','state':'部分上线：turn/start 确认无期限等待、不确定提交锁；完整自动网络续接未上线。'})
            compat,caref=self.read(base/'no-truncation/audit-compat/progress.json')
            compat_result,crref=self.read(base/'no-truncation/audit-compat/result.json')
            refs.extend(x for x in (caref,crref) if x)
            milestones.append({'name':'已闭合失败 turn 自动续接','state':'待中间回执与逐 turn 审计兼容；'+('兼容候选已离线交付，待发布者审查' if crref else '兼容审查仅离线进行' if caref else '尚无兼容审查公开回执')+'。'})
        permission,perref=self.read(self.root/'artifacts/R019/recovery-20260916/permission-contract-fix.json')
        if perref:
            refs.append(perref)
            if str(permission.get('status','')).startswith('published_for_next_reset'):
                milestones.append({'name':'权限合同修正','state':'已发布供下一新 reset；无模型握手已验证，既有在途回合不热改。'})
        if publisher.get('shared_core_changed') is False:milestones.append({'name':'共享 core','state':'未晋升；SIMPLE 发布与共享层分开记录。'})
        row.update(state='engineering-prep',state_label='SIMPLE 分项已上线 · NT 部分上线' if partial_nt else 'SIMPLE 分项已上线',
            summary='、'.join(label for _,label in deployed)+'已在 SIMPLE 上线。'+('门16、水龙头8有真实回合验证；' if len(validated)==2 else '')+('NT 仍有自动网络续接待审计兼容。' if partial_nt else ''),
            problem='入口、检索、标定与 reset 同时变化；现有回归不能证明单项收益或泛化。'+('已闭合失败 turn 的自动续接仍待审计兼容。' if partial_nt else ''),
            next='由兼容审查者离线对齐中间失败回执与逐 turn 审计，再交唯一发布者审查；不修改在途回合。' if partial_nt else '由 SIMPLE 发布者在自然边界维护公开集成回执。',
            who='SIMPLE 发布者 / 续接兼容审查者',mode='SIMPLE 集成回执；共同变更验证',backend='工程改动；真实回归后端 SIMPLE / MuJoCo',
            source_at=max(public_time(publisher,pref),public_time(permission,perref)),source_time_note='发布者集成/权限回执更新时间；候选交付和实际应用分别记录。',
            milestones=milestones)
        return self.publication_updates(row)

    def publication_updates(self,row):
        """Later publisher evidence overrides candidate text, never infers recovery from success."""
        refs=row['sources'];milestones=row['milestones']
        nt,nref=self.read(self.root/'artifacts/R019/nt-audit-integration-20260916/status.json')
        permission,pref=self.read(self.root/'artifacts/R019/recovery-20260916/permission-contract-fix.json')
        route,rref=self.read(self.root/'artifacts/R019/recovery-20260916/permission-physical-route-verification.json',allow_list=True)
        for ref in (nref,pref,rref):
            if ref and not any(x['path']==ref['path'] for x in refs):refs.append(ref)
        permission_state=permission.get('status')
        if permission_state=='published_and_verified_on_formal_physical_actions':
            verified=[x for x in route if isinstance(x,dict) and x.get('first_physical_action_observed') is True and (number(x.get('observed_actions')) or 0)>0 and x.get('sandbox',{}).get('type')=='workspaceWrite' and x.get('approvalPolicy')=='on-request' and x.get('approvalsReviewer')=='auto_review'] if isinstance(route,list) else []
            milestones[:]=[x for x in milestones if x['name']!='权限合同修正']
            milestones.append({'name':'权限合同修正','state':f'已在正式物理动作验证；{len(verified)}份公开路由回执。既有在途回合不热改。' if verified else '发布者报告已在正式物理动作验证；可核验路由回执尚未提供。'})
        candidate=nt.get('candidate');file_hashes=nt.get('files',[])
        expected_files={'rsi/codex_app_server.py','tools/learn_grasp_skill.py','tools/audit_simple_campaigns.py'}
        after={x.get('path') for x in file_hashes if isinstance(x,dict) and x.get('path') in expected_files and isinstance(x.get('after_sha256'),str) and re.fullmatch(r'[a-f0-9]{64}',x['after_sha256'])} if isinstance(file_hashes,list) else set()
        published=isinstance(candidate,str) and re.fullmatch(r'NT-AUDIT-[0-9]{8}-v[0-9]+',candidate) is not None and str(nt.get('state','')).startswith('published') and after==expected_files
        if published:
            budget,bref=self.read(self.root/'artifacts/R019/door-campaign/episode-0019/policy_instruction_budget.json')
            if bref:
                refs.append(bref);row['source_at']=max(row.get('source_at') or 0,bref['at'])
            # The named v1 receipt and door19 reservation are the supplied loading contract.
            matching_version=candidate=='NT-AUDIT-20260916-v1' or budget.get('nt_audit_version')==candidate
            loaded=bool(bref and matching_version and budget.get('contract')=='skill-plus-runtime-v1' and isinstance(budget.get('network_continuation'),str) and budget['network_continuation'].strip() and isinstance(budget.get('developer_instructions_sha256'),str) and re.fullmatch(r'[a-f0-9]{64}',budget['developer_instructions_sha256']))
            recovered=nt.get('physical_network_recovery_verified')
            recovery_text='发布者已报告真实断线恢复验证' if recovered is True else ('真实断线恢复尚未验证' if recovered is False else '真实断线恢复验证未上报')
            summary='续接审计已发布；'+('门19已加载；' if loaded else '门19加载尚未确认；')+recovery_text
            retired={'不中断续接审查','NT 连续性保护','已闭合失败 turn 自动续接','NT 发布离线回归','NT 门19加载','真实断线恢复'}
            milestones[:]=[x for x in milestones if x['name'] not in retired]
            tests=number(nt.get('publisher_tests_passed'))
            milestones.extend([
                {'name':'NT 续接审计发布','state':candidate+' 已发布；按发布者自然边界与文件哈希回执确认。'},
                {'name':'NT 发布离线回归','state':f'{tests}项通过；离线测试不等于真实网络收益。' if tests is not None else '发布者离线测试数量未上报。'},
                {'name':'NT 门19加载','state':'新合同与 network_continuation 预留已加载；不据此宣称回合成功。' if loaded else '尚缺匹配的新合同加载证据；发布不等于加载。'},
                {'name':'真实断线恢复','state':recovery_text+'；不从回合成功、动作数或视频播放推断。'}])
            row.update(state='engineering-prep',state_label=summary,summary=summary+'。其他已上线改动分项保留。',
                problem='发布、加载、真实断线恢复分开记录；离线回归及共同变更后的成功不证明单项网络收益或泛化。',
                next=public_text([nt],'next_step','next') or '由 SIMPLE 发布者在自然边界补充实际恢复回执；不制造断线，不热改在途回合。',
                who='SIMPLE 发布者',mode='发布与加载回执；真实恢复验证独立记录',
                nt_publication={'candidate':candidate,'published':True,'door19_loaded':loaded,'physical_network_recovery_verified':recovered if type(recovered) is bool else None,'publisher_tests_passed':tests})
        if nref or (pref and permission_state=='published_and_verified_on_formal_physical_actions'):
            times=[row.get('source_at') or 0]+[public_time(doc,ref) for doc,ref in ((nt,nref),(permission,pref)) if ref]
            if rref:times.append(rref['at'])
            row['source_at']=max(times)
            row['source_time_note']='发布、加载及权限动作验证使用各自公开回执；源码/宿主详情不进入页面。'
        return self.stability_observation(row)

    def stability_observation(self,row):
        """Fixed reviewer/publisher receipts; publication, field checks and benefit stay separate."""
        prior_summary=row['summary']; prior_time_note=row.get('source_time_note') or ''
        base=self.root/'artifacts/architecture-review-20260916/robot-stability-observation'
        publication=self.root/'artifacts/R019/robot-stability-integration-20260916'
        pub,pref=self.read(publication/'status.json')
        first,fref=self.read(publication/'first-action-physical-verification.json')
        sources=[]; result={}; progress={}
        for name in ('manager-status.json','progress.json','result.json'):
            doc,ref=self.read(base/name)
            if ref:sources.append((doc,ref))
            if name=='result.json':result=doc
            if name=='progress.json':progress=doc
        if not sources and not pref and not fref:return row
        sources.sort(key=lambda x:x[1]['at'],reverse=True)
        docs=[d for d,_ in sources]
        candidate=lambda d:d.get('candidate_only') is True or any(d.get(k) in ('candidate_only','candidate-only','complete_candidate_only') for k in ('state','status'))
        delivery=result.get('delivery') if isinstance(result.get('delivery'),dict) else {}
        candidate_id=result.get('candidate_id')
        # The real v1 progress omits candidate_id. Bind it to this fixed source pair
        # and the known result ID; reject any explicitly conflicting progress ID.
        completed_handoff=(candidate_id=='ROBOT-STABILITY-OBS-V1'
            and progress.get('candidate_id',candidate_id)==candidate_id
            and candidate(result) and candidate(progress)
            and progress.get('stage')=='bounded_delivery_complete'
            and delivery.get('queued') is True and progress.get('delivery_queued') is True
            and result.get('deployed') is False and delivery.get('integrated') is False
            and progress.get('integrated') is False)
        delivered=(result.get('ready') is True and candidate(result)) or completed_handoff
        reviewing=any(candidate(d) or d.get('phase')=='offline_review_in_progress' for d in docs)
        state='candidate-delivered' if delivered else 'offline-review' if reviewing else 'unknown'
        label='候选已交付；待发布者审查集成' if delivered else '离线审查候选' if reviewing else '候选工程状态尚未上报'
        # False is a reported boundary; missing flags stay unknown. Reviewer tests or
        # ready flags cannot establish deployment or physical benefit, even if claimed.
        deployed=next((d['deployed'] for d in docs if type(d.get('deployed')) is bool),None)
        benefit=next((d['physical_benefit_verified'] for d in docs if type(d.get('physical_benefit_verified')) is bool),None)
        if benefit is None and completed_handoff:benefit=delivery.get('physically_validated')
        deployed=False if deployed is False else None
        benefit=False if benefit is False else None
        boundary=('未部署' if deployed is False else '部署状态未上报')+'；'+('物理收益未验证' if benefit is False else '物理收益验证未上报')+'。候选不代表线上生效。'
        at=max((ref['at'] for _,ref in sources),default=None)
        work={'name':'本体状态观测候选','state':state,'deployed':deployed,'physical_benefit_verified':benefit,'source_at':at}
        row['current_work']=work
        row['summary']+=' 当前在研：本体状态观测 · '+label+'。'
        row['problem']=public_text(docs,'current_problem','problem','blocker') or '本体状态观测候选的当前问题尚未上报。'
        next_step=public_text(docs,'next_step','next') or '本体状态观测候选的下一步尚未上报；由审查者补充公开工程状态。'
        row['next']=next_step
        handoff_note=''
        if delivered:
            row['problem']='本体状态观测候选已完成并交付；'+boundary
            row['next']='待发布者审查集成：由 SIMPLE 唯一发布者在自然边界检查与集成；不改在途回合。'
            if delivery.get('queued') is True:
                ack=delivery.get('acknowledged')
                handoff_note=' 交接已排队；'+('负责人尚未确认。' if ack is False else '负责人已确认；集成仍独立记录。' if ack is True else '负责人是否确认尚未上报。')
        row['who']='辅助架构审查者 / SIMPLE 唯一发布者'
        row['milestones'].append({'name':work['name'],'state':label+'；'+boundary+handoff_note})
        row['sources'].extend(ref for _,ref in sources)
        row['source_at']=max(row.get('source_at') or 0,at or 0) or None
        when=dt.datetime.fromtimestamp(at,dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if at is not None else '尚未上报'
        row['source_time_note']=(row.get('source_time_note') or '')+' 本体候选管理状态文件更新：'+when+'；非物理动作时间。'
        if not pref and not fref:return row
        refs=[ref for ref in (pref,fref) if ref]
        row['sources'].extend(refs)
        row['source_at']=max(row.get('source_at') or 0,*(ref['at'] for ref in refs))
        hashes=pub.get('source_sha256')
        published=(pub.get('ack')=='ROBOT-STABILITY-OBS-V1 ACK'
            and pub.get('status') in ('published','published_first_formal_action_fields_verified','published_first_formal_episode_audited_success')
            and pub.get('source_hashes_match') is True and isinstance(hashes,dict)
            and all(isinstance(hashes.get(path),str) and re.fullmatch(r'[a-f0-9]{64}',hashes[path])
                    for path in ('rsi/live.py','rsi/policy_harness.py')))
        if not published:
            row['milestones'].append({'name':'本体状态观测发布回执','state':'发布者回执尚未确认；暂保留候选状态，不推断已部署。'})
            return row
        # Compare canonical episode identifiers as strings. Never follow first_action_evidence,
        # root_mapping_receipt or source_sha256 keys to read other files or rerun diagnostics.
        boundary=pub.get('first_physical_boundary')
        canonical=isinstance(boundary,str) and re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*-campaign/episode-[0-9]{4,8}',boundary)
        same_episode=bool(canonical and first.get('episode')=='artifacts/R019/'+boundary)
        samples=number(first.get('samples')); height=number(first.get('max_height_difference_m')); tilt=number(first.get('max_tilt_difference_deg'))
        fields_verified=bool(fref and same_episode and number(first.get('actual_formal_physical_action'))==1
            and type(samples) is int and samples>0 and height is not None and tilt is not None
            and all(first.get(key) is True for key in ('published_sources_match_formal_runtime',
                    'same_action_time_and_episode_identity','summary_recomputation_exact')))
        benefit_claims=[pub.get('physical_benefit_verified')]
        if same_episode:benefit_claims.append(first.get('physical_task_benefit_verified'))
        negative=any(v is False for v in benefit_claims) or pub.get('full_episode_and_task_benefit')=='pending'
        contradictory=negative and any(v is True for v in benefit_claims)
        benefit=False if negative and not contradictory else None
        benefit_text=('完整回合和任务收益回执不一致，尚未确认' if contradictory else
                      '完整回合和任务收益尚未验证' if benefit is False else '完整回合和任务收益验证尚未上报')
        label='本体状态观测已发布；'+('首动作字段验证通过' if fields_verified else '首动作字段验证尚未确认')
        episode_audited=(fields_verified and pub.get('status')=='published_first_formal_episode_audited_success'
                         and pub.get('first_complete_episode')=='artifacts/R019/'+boundary)
        if episode_audited:
            label+='；首个完整回合受限审计通过'
            benefit_text='完整回合审计已报告；单项改动的物理收益仍未验证，不作因果或泛化推断'
        work.update(name='本体状态观测',state='published-fields-verified' if fields_verified else 'published',
            deployed=True,publisher_acknowledged=True,physical_benefit_verified=benefit,
            first_action_fields_verified=True if fields_verified else None,
            first_complete_episode_audited=episode_audited,
            first_physical_boundary=boundary if canonical else None,
            actual_formal_physical_action=1 if fields_verified else None,samples=samples if fields_verified else None,
            max_height_difference_m=height if fields_verified else None,max_tilt_difference_deg=tilt if fields_verified else None,
            source_at=max(ref['at'] for ref in refs))
        row['summary']=prior_summary+' '+label+'。'
        row['problem']=benefit_text+('；人工反馈辅助与原生任务审计边界继续单列。' if episode_audited else '；首动作字段核验不代表完整回合或任务成功。')
        row['next']=('等待原任务完整回合审计；不重复该首动作字段等值诊断；在途旧版冻结。' if fields_verified else
                     '由原发布者核对首动作回执是否齐全且属于同一回合；等待完整回合审计；在途旧版冻结。')
        row['who']='SIMPLE 原任务执行者 / 唯一发布者'
        if episode_audited:row['next']='依据六项协议分别学习、登记固定候选和冻结测评；不重复字段等值诊断，在途旧版冻结。'
        row['milestones'][:]=[m for m in row['milestones'] if m['name']!='本体状态观测候选']
        detail=(f'；首动作 {work["actual_formal_physical_action"]}、{samples} 个采样；只读字段验证回执' if fields_verified else '；缺少匹配且明确通过的首动作验证回执')
        row['milestones'].append({'name':'本体状态观测发布与验证','state':label+'；发布者已 ACK、已集成'+detail+'。'+benefit_text+'。'})
        row['source_time_note']=prior_time_note+' 本体观测采用发布/首动作字段验证回执；旧候选保留为历史来源。回执文件更新时间非实际动作时间。'
        if row['state']=='unknown':row.update(state='engineering-prep',state_label=label)
        return row

    def snapshot(self,force=False):
        with self.lock:
            if not force and self.cache and time.time()-self.cached_at<4:return self.cache
            self.records={}
            tasks=[self.verified_user_pause(t) for t in (self.simple(),self.ground(),self.ikea(),self.framework())]
            for t in tasks:
                # Stable source package excludes browser refresh/derived age. Only public projection.
                t['version']=hash_json(t)
            self.cache={'schema':1,'observed_at':time.time(),'poll_seconds':5,'tasks':tasks,
                'notice':'来源超过 5 分钟未更新会标记陈旧；陈旧不等于执行停止。只有公开证据，未读取模型推理日志。'}
            self.cached_at=time.time();return self.cache
