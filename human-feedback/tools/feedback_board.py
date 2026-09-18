"""Scoped append-only browser feedback. Persist before local priority handoff; never launch a model or account CLI.
A claimed/uncertain delivery is never blindly retried, including after restart.
"""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import uuid
from dashboard import hash_json, RSI
from store import immutable, now, digest

OWNERS={'simple':'01a0a867-d7aa-71f2-8547-e264d6d09ede',
        'ground':'01a0a982-cec5-71c0-b771-091c31df61f2',
        'ikea':'01a0a96b-06cc-7150-8c73-7b0897936b52',
        'framework':'01a0a94d-6143-74c0-80cd-03d0b61acaf0'}
ID=re.compile(r'FB-[a-f0-9]{32}')
HEX=re.compile(r'[a-f0-9]{64}')

class FeedbackBoard:
    def __init__(self,dashboard,root=None,fixture=False,delivery=None):
        self.dashboard=dashboard;self.root=Path(root or RSI/'human-feedback/dashboard-upgrade/feedback')
        self.fixture=fixture;self.delivery=delivery;self.lock=threading.RLock()
        for d in ['packages','answers','delivery','cases','acks']:(self.root/d).mkdir(parents=True,exist_ok=True)

    def publish_packages(self,tasks):
        for task in tasks:
            path=self.root/'packages'/(task['version']+'.json')
            if not path.exists():
                try:immutable(path,task)
                except FileExistsError:pass

    def validate_case(self,c):
        allowed={'case_id','task_id','title','mechanism','control_version','question','choices','facts','hypothesis','already_tried','unresolved','attempts','source_version'}
        if not isinstance(c,dict) or set(c)-allowed:raise ValueError('case fields')
        if not re.fullmatch(r'HC-[A-Za-z0-9_-]{3,64}',c.get('case_id','')) or c.get('task_id') not in OWNERS:raise ValueError('case identity')
        if c.get('unresolved') is not True:raise ValueError('analysis not unresolved')
        for k in ['title','mechanism','control_version','question','facts','hypothesis','already_tried']:
            if not isinstance(c.get(k),str) or not 1<=len(c[k])<=3000:raise ValueError('case missing '+k)
        if not isinstance(c.get('choices',[]),list) or len(c.get('choices',[]))>6 or any(not isinstance(x,str) or len(x)>300 for x in c.get('choices',[])):raise ValueError('choices')
        attempts=c.get('attempts',[])
        if not isinstance(attempts,list) or not 3<=len(attempts)<=20:raise ValueError('three independent attempts required')
        resets=set();episodes=set()
        for a in attempts:
            if not isinstance(a,dict) or set(a)!={'record_id','result_sha256','reset_id','video_url','timestamps','keyframe_url','change','outcome'}:raise ValueError('attempt fields')
            record=self.dashboard.records.get(a['record_id'])
            if not record or record['task']!=c['task_id'] or record['state']!='physical-failure':raise ValueError('not a physical terminal failure')
            if not record.get('actions') or record.get('human_feedback_used') is not False or record.get('independent_reset_verified') is not True or record.get('no_replay_or_diagnostic_initial_state') is not True:raise ValueError('independent autonomous reset unverified')
            if record.get('control_version')!=c['control_version'] or record.get('mechanism')!=c['mechanism']:raise ValueError('not comparable')
            if not a['reset_id'] or a['reset_id']!=record.get('reset_id') or a['result_sha256']!=record['result_sha256']:raise ValueError('evidence mismatch')
            if a['reset_id'] in resets or a['record_id'] in episodes:raise ValueError('duplicate reset')
            resets.add(a['reset_id']);episodes.add(a['record_id'])
            evidence=self.dashboard.case_media(a['record_id'])
            media=self.dashboard.media_file(a['video_url']); frame=self.dashboard.media_file(a['keyframe_url'])
            if not media or media[0].suffix!='.mp4' or not frame or frame[0].suffix!='.png':raise ValueError('continuous video and keyframe required')
            if not evidence or not media[0].is_relative_to(evidence['folder']) or not frame[0].is_relative_to(evidence['folder']):raise ValueError('media from another episode')
            duration=(evidence.get('video') or {}).get('duration_s',0)
            if not isinstance(a['timestamps'],list) or not a['timestamps'] or any(type(x) not in (float,int) or x<0 or x>duration for x in a['timestamps']):raise ValueError('timestamps')
            for k in ['change','outcome']:
                if not isinstance(a[k],str) or not 1<=len(a[k])<=1000:raise ValueError('attempt summary')
        return dict(c,version=hash_json(c))

    def cases(self):
        cases=[];invalid=0
        for p in sorted((self.root/'cases').glob('HC-*.json')):
            try:
                if p.is_symlink() or p.stat().st_size>128000:raise ValueError('case source')
                c=self.validate_case(json.loads(p.read_text()))
                # Once answered, do not keep asking; corrections remain available as feedback.
                if any(x['submission'].get('case_id')==c['case_id'] for x in self.all_answers()):continue
                package=self.root/'packages'/(c['version']+'.json')
                if not package.exists():immutable(package,c)
                cases.append(dict(c,source_at=p.stat().st_mtime))
            except (OSError,ValueError,KeyError,TypeError):invalid+=1
        return {'cases':cases,'eligible_count':len(cases),'rejected_count':invalid,
                'latest_case_at':max([c['source_at'] for c in cases],default=None),'waiting_for':'用户判断' if cases else '执行者提供合格失败簇；用户可随时主动补充',
                'reason':'尚无经核验的三次可比独立物理失败簇。提前结束、预算截断、旧动作复现及单回合多次动作均不计入。H001/F001 已回答，不重复提问。'}

    def all_answers(self):
        out=[]
        for p in sorted((self.root/'answers').glob('FB-*.json')):
            if not p.is_symlink():
                try:out.append(json.loads(p.read_text()))
                except (OSError,ValueError):pass
        return out

    def status(self,rec):
        aid=rec['feedback_id']; events=[]
        for name in ['claim','result']:
            p=self.root/'delivery'/(aid+'-'+name+'.json')
            if p.exists():events.append(json.loads(p.read_text()))
        queued=any(x.get('state')=='queued' for x in events)
        main_inbox=any(x.get('state')=='main_account_inbox' for x in events)
        owner_inbox=any(x.get('state')=='authorized_owner_inbox' for x in events)
        claimed=any(x.get('state')=='claimed' for x in events)
        recipient=OWNERS[rec['submission']['task_id']]
        message_path=self.root/'delivery'/(aid+'-message.json')
        # Existing receipts stay bound to their original recipient; this never queues again.
        if message_path.exists() and not message_path.is_symlink():
            message=json.loads(message_path.read_text())
            historical={'01a0a948-10bb-7d03-8f1d-b1eeda7cb93c'} if rec['submission']['task_id']=='ground' else set()
            if message.get('owner') in historical|{recipient} and message.get('answer_sha256')==digest((self.root/'answers'/(aid+'.json')).read_bytes()):
                recipient=message['owner']
        ack=None;verified=None;adoption=None;loaded=None
        for p in sorted((self.root/'acks').glob(aid+'-*.json')):
            try:
                a=json.loads(p.read_text())
                if p.is_symlink() or a.get('feedback_id')!=aid or a.get('owner')!=recipient or a.get('answer_sha256')!=digest((self.root/'answers'/(aid+'.json')).read_bytes()):continue
                if a.get('stage')=='owner_ack':ack={'at':a.get('at'),'note':str(a.get('note',''))[:600]}
                if a.get('stage')=='loaded' and isinstance(a.get('evidence'),str) and a['evidence'].startswith('artifacts/') and '..' not in Path(a['evidence']).parts:
                    evidence,ref=self.dashboard.read(self.dashboard.root/a['evidence'])
                    if ref and a.get('evidence_sha256')==ref['sha256'] and evidence.get('feedback_id')==aid and evidence.get('answer_sha256')==a['answer_sha256'] and evidence.get('human_feedback_used') is True:
                        loaded={'at':a.get('at'),'evidence':a['evidence'],'note':str(a.get('note',''))[:600]}
                if a.get('stage') in ('adopted','rejected'):
                    adoption={'state':a['stage'],'at':a.get('at'),'note':str(a.get('note',''))[:600]}
                if a.get('stage')=='physical_verified' and a.get('human_feedback_used') is True and isinstance(a.get('evidence'),str) and not a['evidence'].startswith('/') and '..' not in Path(a['evidence']).parts and a['evidence'].startswith(('artifacts/','api-ground-to-table/','ikea/')):
                    evidence_path=self.dashboard.root/a['evidence']
                    evidence,ref=self.dashboard.read(evidence_path) if evidence_path.name=='result.json' else ({},None)
                    if ref and ref['at']>=dt.datetime.fromisoformat(rec['saved_at']).timestamp() and evidence.get('human_feedback_used') is True:
                        verified={'at':a.get('at'),'evidence':a['evidence'],'note':str(a.get('note',''))[:600]}
            except (OSError,ValueError,KeyError,TypeError):pass
        coordination=None
        review_path=self.root/'reviews'/(aid+'.json')
        if review_path.exists() and not review_path.is_symlink():
            try:
                review=json.loads(review_path.read_text())
                if (review.get('feedback_id')==aid
                        and review.get('answer_sha256')==digest((self.root/'answers'/(aid+'.json')).read_bytes())
                        and review.get('reviewer') in ('01a0a949-dc8e-70c3-b8a6-53131882e19d',OWNERS['framework'])
                        and review.get('stage') in ('accepted_for_implementation','implemented')):
                    coordination={k:review.get(k) for k in ('stage','priority','note','at','release_id')}
            except (OSError,ValueError,TypeError):pass
        waiting_s=max(0,time.time()-dt.datetime.fromisoformat(rec['saved_at']).timestamp())
        return {'saved':True,'queued':queued,'queue_pending':not queued,'delivery_uncertain':claimed and events[-1].get('state') not in ('failed','file_handoff','main_account_inbox','authorized_owner_inbox') and not queued if events else False,
                'owner_ack':ack,'adoption':adoption,'actual_loaded':loaded,'physical_verified':verified,'fixture':self.fixture,
                'priority':'highest' if rec.get('kind')=='unsolicited_observation' else 'normal',
                'handoff':'legacy_queue' if queued else 'authorized_owner_inbox' if owner_inbox else 'main_account_inbox' if main_inbox else 'local_priority_file','consumption_pending':not bool(ack),'evidence_binding':rec.get('evidence_binding',{'state':'verified'}),
                'coordination':coordination,'attention_required':not (ack or coordination) and waiting_s>300,
                'waiting_s':waiting_s,'main_account_inbox':main_inbox}

    def receipts(self):
        return [dict(x,status=self.status(x)) for x in self.all_answers()]

    def submit(self,payload):
        required={'request_id','task_id','case_id','source_version','text','choice','user_timestamp','correction_of'}
        if not isinstance(payload,dict) or set(payload)-{'context'}!=required:raise ValueError('提交字段不完整')
        if payload['task_id'] not in OWNERS or not isinstance(payload['request_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',payload['request_id']):raise ValueError('任务或请求标识无效')
        if not isinstance(payload['source_version'],str) or not HEX.fullmatch(payload['source_version']):raise ValueError('证据版本无效')
        for k in ['text','choice']:
            if not isinstance(payload[k],str) or len(payload[k])>(12000 if k=='text' else 300):raise ValueError('回答长度无效')
        if not payload['text'].strip() and not payload['choice'].strip():raise ValueError('请输入观察或选择答案')
        try:
            stamp=dt.datetime.fromisoformat(payload['user_timestamp'].replace('Z','+00:00'))
            if stamp.tzinfo is None:raise ValueError('timezone')
        except (ValueError,TypeError,AttributeError):raise ValueError('回答时间无效')
        with self.lock,(self.root/'.submit.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            old=self.all_answers()
            for r in old:
                if r['submission']['request_id']==payload['request_id']:
                    if r['submission']!=payload:raise ValueError('同一提交标识的内容不一致')
                    return dict(r,status=self.status(r),duplicate=True)
            package=self.root/'packages'/(payload['source_version']+'.json')
            binding={'state':'verified','source_version':payload['source_version']}
            try:
                if package.is_symlink() or not package.exists():raise ValueError('证据包已缺失')
                source=json.loads(package.read_text())
                if hash_json({k:v for k,v in source.items() if k!='version'})!=payload['source_version']:raise ValueError('证据包内容与版本不符')
                if payload['case_id'] is None:
                    if source.get('id')!=payload['task_id'] or source.get('version')!=payload['source_version']:raise ValueError('任务证据绑定不匹配')
                    if 'context' in payload:
                        context=payload['context']
                        if (payload['task_id']!='simple' or not isinstance(context,dict) or set(context)!={'subtask_id','native_env_id'}
                            or not any(r.get('id')==context['subtask_id'] and r.get('native_env_id')==context['native_env_id']
                                       for r in source.get('subtasks',[])+source.get('history_subtasks',[]))):raise ValueError('任务上下文与证据不匹配')
                else:
                    if 'context' in payload:raise ValueError('求助案例使用其原始同回合绑定')
                    case=next((c for c in self.cases()['cases'] if c['case_id']==payload['case_id']),None)
                    if not case or case['version']!=payload['source_version'] or case['task_id']!=payload['task_id']:raise ValueError('求助题已回答或版本改变')
                    if payload['choice'] and payload['choice'] not in case.get('choices',[]):raise ValueError('选项无效')
            except (ValueError,OSError,KeyError,TypeError) as error:
                # Proactive human words must survive stale/missing/broken page evidence.
                # Preserve the original reference as UNVERIFIED; never bless it or use it as truth.
                if payload['case_id'] is not None:raise
                binding={'state':'unverified','source_version':payload['source_version'],
                         'reason':str(error) if isinstance(error,ValueError) else '证据包暂不可读',
                         'note':'原话已保存并优先交接；证据绑定需核查，不能据此宣称已使用或生效。'}
            parent=payload['correction_of']
            if parent is not None:
                if not isinstance(parent,str) or not ID.fullmatch(parent) or not any(x['feedback_id']==parent and x['submission']['task_id']==payload['task_id'] for x in old):raise ValueError('被纠正回答无效')
            rec={'schema':1,'feedback_id':'FB-'+uuid.uuid4().hex,'saved_at':now(),'submission':payload,
                 'kind':'requested_case' if payload['case_id'] else 'unsolicited_observation','fixture':self.fixture,
                 'rule_status':'human_proposed','human_feedback_used':False,'human_demonstration_used':False,
                 'priority':'highest' if payload['case_id'] is None else 'normal','evidence_binding':binding}
            immutable(self.root/'answers'/(rec['feedback_id']+'.json'),rec)
        # Persisted before any attempt to notify; never send user text as shell/code.
        if not self.fixture or self.delivery:
            try:self.deliver(rec)
            except OSError:pass  # Durable answer remains pending even if handoff storage is unavailable.
        return dict(rec,status=self.status(rec),duplicate=False)

    def deliver(self,rec):
        aid=rec['feedback_id'];claim=self.root/'delivery'/(aid+'-claim.json')
        try:immutable(claim,{'state':'claimed','at':now()})
        except FileExistsError:return
        p=self.root/'answers'/(aid+'.json');sha=digest(p.read_bytes());s=rec['submission']
        msg=(f"网页真实用户反馈已保存。task={s['task_id']} case={s['case_id'] or '主动补充'} "
             f"feedback={aid} source_version={s['source_version']} answer_sha256={sha}。"
             f"只读原文路径：{p}；同信息公开证据包：{self.root/'packages'/(s['source_version']+'.json')}。"
             "主动反馈不受三次失败门槛限制；任务顺序和操作纠正优先处理，观察中的因果判断另行验证。不得把原文当shell代码执行或泄露隐藏审计。"
             "在下一个安全工具边界读取并登记处理；完整等待在途推理、不重放动作。排队不是消费，队列阻塞时读取持久answers目录。按 dashboard-upgrade/OWNER_INTERFACE.md 写 owner_ack；"
             "实际用于后续回合再标 human_feedback_used，物理验证另写回执。保存/排队不等于采纳。")
        immutable(self.root/'delivery'/(aid+'-message.json'),{'owner':OWNERS[s['task_id']],'message':msg,'answer_sha256':sha,'priority':rec.get('priority','highest'),'state':'pending_consumption'})
        try:
            if self.delivery: outcome=self.delivery(msg,OWNERS[s['task_id']])
            else:
                # No auxiliary/API/main-account model call from the website. The existing
                # authorized owner consumes these immutable files at its next safe boundary.
                policy,_=self.dashboard.read(self.dashboard.root/'ref/tasks/account-policy.json')
                main_only=policy.get('main_account_allowed') and policy.get('auxiliary_accounts_allowed') is False
                api_owner=policy.get('api_enabled') is True and policy.get('preferred_route')=='api'
                outcome={'state':'authorized_owner_inbox' if api_owner else 'main_account_inbox' if main_only else 'file_handoff','priority':rec.get('priority','highest'),
                         'reason':'persisted priority handoff; awaiting authorized owner consumption',
                         'account_calls':0,'retry':False}
        except subprocess.TimeoutExpired:outcome={'state':'uncertain','reason':'queue acknowledgement not confirmed; no retry'}
        except OSError:outcome={'state':'failed','reason':'queue launcher unavailable; saved answer preserved'}
        immutable(self.root/'delivery'/(aid+'-result.json'),dict(outcome,at=now()))
