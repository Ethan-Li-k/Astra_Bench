"""Small, read-only public goal projection. Never executes validator/source paths.

Formal credit stays pending until the actual owner validator contract is reviewed.
An engineering result's ready/complete, learning rates and a dispatch cannot pass it.
"""
import hashlib
import re
from simple_six import official_baseline, sha

BASE='artifacts/psi0-goal-20260916/'
TASKS=('XMovePick','BendPick','Handover','Mobile P&P','Grasp','XMoveBendPick')
RULE='ref/USER_UPDATE_20260916_PSI0_GOAL_API_FALLBACK.md'
FALLBACK_OWNER='01a0a982-cec5-71c0-b771-091c31df61f2'
PHASES={
 'legacy_reproduced_implementing':'旧接续阻塞已复现；正在实现受控 API 接续与目标门槛',
 'offline_verified':'离线验证已通过；实际安装与加载另验',
}
TEXT={
 'Quota turn.failed blocks all continuation; legacy PROMPT forbids API; completion claims lack benchmark validation.':'已复现旧接续器在额度耗尽后停止，且旧指令禁止 API；工程完成尚不能验证榜单目标。',
 'Implement guarded supervisor API transport and objective gate; stage rules with hash preconditions.':'实现受控 API 接续与目标验证；规则安装须核对原文件哈希。',
}

def short(v):
 return v if isinstance(v,str) and len(v)<=400 and not any(x in v.lower() for x in ('host_audit','host-only','api_key','authorization','bearer ','/home/','/tmp/','secret')) else None

def chinese(v):
 v=short(v)
 return v if v and re.search('[\u3400-\u9fff]',v) else TEXT.get(v)

def file_ref(d,relative):
 try:
  p=d.safe(d.root/relative)
  if p.stat().st_size>100000:return None
  raw=p.read_bytes()
  return {'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'at':p.stat().st_mtime}
 except (OSError,ValueError):return None

def goal_snapshot(d,simple):
 refs=[]
 def read(rel):
  doc,ref=d.read(d.root/rel)
  if ref:refs.append(ref)
  return doc,ref
 baseline,bref=read('ref/SIMPLE_OFFICIAL_BASELINE_20260916.json')
 b=official_baseline(baseline,list(TASKS));total=None
 if b['available']:total=sum(sum(v) for v in next(r['values'] for r in b['rows'] if r['method']=='Psi0'))
 rule_ref=file_ref(d,RULE)
 if rule_ref:refs.append(rule_ref)
 contract_ref=file_ref(d,'CURRENT_EFFECTIVE_CONTRACT.md')
 staged_ref=file_ref(d,BASE+'fallback/rules/CURRENT_EFFECTIVE_CONTRACT.md')
 for ref in (contract_ref,staged_ref):
  if ref:refs.append(ref)
 contract_state=('现行文件已写入；进程实际加载另验' if contract_ref else '候选已写入；尚未安装到现行入口' if staged_ref else 'pending')
 plan,planref=read('artifacts/R019/six-task-focus/benchmark-180-plan.json')
 plan_rows=plan.get('planned_episodes');not_run=(isinstance(plan_rows,list) and len(plan_rows)==180
  and plan.get('status')=='plan_only_not_final_preregistration' and plan.get('performed_episodes')==0
  and all(isinstance(r,dict) and r.get('status')=='planned_not_admitted_not_run' for r in plan_rows))
 progress,pref=read(BASE+'fallback/progress.json')
 result,rref=read(BASE+'fallback/result.json')
 ack,aref=read(BASE+'fallback/owner-ack.json')
 # Public progress is the live source; a later result may supply fields it omits.
 docs=sorted([(progress,pref),(result,rref)],key=lambda pair:pair[1]['at'] if pair[1] else -1,reverse=True)
 def explicit(key):
  for doc,ref in docs:
   if ref and type(doc.get(key)) is bool:return doc[key]
  return None
 fallback={'owner':'API 接续负责人','owner_ack':bool(aref and ack.get('owner')==FALLBACK_OWNER),
  'phase_label':PHASES.get(progress.get('phase'),'负责人尚未上报已核验的工程阶段'),
  'current_problem':chinese(progress.get('current_problem')) or '具体接续卡点尚未提供可展示的公开摘要。',
  'next_step':chinese(progress.get('next_step')) or '等待原负责人在自然边界交付；不重发未知请求。',
  'installed':explicit('installed'),'loaded':explicit('loaded'),
  'real_quota_switch_occurred':explicit('real_quota_switch_occurred'),
  'tests_passed':None,'at':pref['at'] if pref else None,
  'note':'规则授权、代码测试、运行加载和真实额度切换分别确认；不据此推断 actor 已切换。'}
 # Test counts have no implication for installed/loaded or real quota events.
 for doc,ref in docs:
  if ref and type(doc.get('tests_passed')) is int and doc['tests_passed']>=0:
   fallback['tests_passed']=doc['tests_passed'];break
 sp,sref=read(BASE+'simple/progress.json')
 sr,srref=read(BASE+'simple/result.json')
 dispatch,dispatch_ref=read(BASE+'simple/dispatch.json')
 validator,vref=read(BASE+'simple/goal-validation.json')
 # Do not guess a validator schema from ready/successes or follow output paths.
 formal={'state':'pending','numerator':None,'denominator':None,'percent':None,
  'note':'目标验证器尚未交付；本地正式六项未测评。学习成功不计入 180 回合目标。' if not vref else
         '目标验证器输出已到；格式与完整准入合同待核验，暂不计目标成绩。',
  'validator_at':vref['at'] if vref else None}
 formal['reported_performed']=0 if not_run else None
 formal['plan_note']='180 个计划位置尚未准入 / 未执行；seed、冻结候选、物理预算、策略渲染绑定待登记。' if not_run else '正式预登记计划与已执行数量尚未核验。'
 central,centref=read(BASE+'central/progress.json')
 candidates=[];routes=[]
 for task in simple.get('subtasks',[]):
  if task.get('name') not in TASKS:continue
  score=task.get('scorecard',{});s=score.get('stability',{});f=score.get('frozen',{})
  candidates.append({'task':task['name'],'stability_registered':s.get('registered') is True,
   'candidate_sha256':s.get('candidate_sha256') if sha(s.get('candidate_sha256')) else None,
   'consecutive':s.get('consecutive') if s.get('registered') is True else None,
   'frozen_registered':f.get('registered') is True})
  # The dashboard already selected an allowlisted episode; no arbitrary public path.
  episode=task.get('episode');catalog=d.simple_catalog
  records=score.get('records',[])
  match=next((r for r in records if r.get('episode')==episode and r.get('campaign') in catalog),None)
  route='未核验';at=None
  if match and isinstance(episode,str) and re.fullmatch(r'episode-\d{4,8}',episode):
   folder='artifacts/R019/'+catalog[match['campaign']][1]+'/'+episode
   backend,backref=read(folder+'/model_backend.json')
   receipt,route_ref=read(folder+'/account_route_verified.json')
   if backref and backend.get('model')=='gpt-6-astra' and backend.get('effort')=='xhigh':
    if (backend.get('account_route')=='authorized_account_2' and backend.get('launcher')==str(d.root/'codex-account-2/run.sh')
        and receipt.get('model')=='gpt-6-astra' and receipt.get('effort')=='xhigh'
        and receipt.get('reset_id')==task.get('episode_interface',{}).get('reset_id') and route_ref):
     route='辅助账号 2 · Astra / xhigh（本回合已核验）';at=route_ref['at']
   routes.append({'task':task['name'],'episode':episode,'route':route,'at':at})
 return {'schema':1,'baseline':{'successes':total,'planned':180,'percent':100*total/180 if total is not None else None,
  'source_url':b.get('source_url'),'read_at':b.get('read_at')},
  'target_successes':total+1 if total is not None else None,'target_percent':100*(total+1)/180 if total is not None else None,
  'planned':180,'achieved':False,'status':'尚未达标','formal':formal,'candidates':candidates,
  'rules':{'written':bool(rule_ref),'at':rule_ref['at'] if rule_ref else None,'contract_state':contract_state},
  'fallback':fallback,'routes':routes,
  'simple_goal':{'state':'queued_not_ACK' if dispatch.get('status')=='queued_not_ACK' and not sref else 'public_progress' if sref else 'pending',
   'current_problem':chinese(sp.get('current_problem')),'next_step':chinese(sp.get('next_step')),'at':sref['at'] if sref else dispatch_ref['at'] if dispatch_ref else None},
  'admission':['六个精确入口 × L0/L1/L2 × 每格 10 个独立 reset；seed / DR / split / 目标物预登记',
   '冻结完整 candidate：skill / 控制器 / 可读记忆 / 反馈来源与逐项指令哈希固定，五次稳定性单列',
   'Isaac 图像实际作为策略输入，episode / reset / state / camera 绑定通过；MuJoCo 可负责物理',
   '原生判据和 TimeLimit 单位对齐；正式回合无在线人工帮助、无跨回合学习',
   '完整 180 回合证据与独立审计、无重复计分、不择优拼接；原生与完整语义结果分开'],
  'review_decisions':['已采纳方向：短共同 skill + 控制合同 + 六任务差异、编号工具循环、公开阶段账本与带适用条件的原子经验；当前实现与加载见 Harness 发布回执。',
   '独立候选：Pelvis-1 / UpperBody-Mobile-7、既有 AMO/PD、真实接口核验后的 Hybrid；不替换在途四点控制，不混合计分。',
   '暂不训练四套角色模型、不引入神经 MoE；同步 Isaac 不自动意味着 RTC。'],
  'central_goal':{'state':'正在核对实际接口合同；新候选未据此视为发布或加载' if central.get('phase')=='inspecting_actual_contracts' else '新目标改造的具体交付阶段尚待公开回执','at':centref['at'] if centref else None},
  'note':'155/180 是榜单点估计超过，不宣称统计显著；工程交付和五次稳定性都不是总目标完成。',
  'sources':refs,'source_at':max((r['at'] for r in refs),default=None)}
