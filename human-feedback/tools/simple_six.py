"""Read-only six-task score arithmetic over already allowlisted episode summaries.
No filesystem traversal, runtime calls, or host evidence is exposed here.
"""
import datetime as dt
import hashlib
import json
import re

PROTOCOL='SIX-TASK-FIVE-STABLE-V1'
CONFIG_KEYS=('skill','entry','runtime','memory','retrieval','feedback','task_asset','control','camera','model')

def timestamp(value):
    try:return dt.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    except (ValueError,TypeError,AttributeError):return None

def sha(value):return isinstance(value,str) and bool(re.fullmatch('[a-f0-9]{64}',value))
def rate(rows,key):
    known=[r for r in rows if type(r.get(key)) is bool]
    n=sum(r[key] for r in known);d=len(known)
    return {'numerator':n,'denominator':d,'percent':100*n/d if d else None}

def scorecard(matches,native,effective,candidate=None):
    """Learning totals describe changing skills; fixed-candidate counts require manifests.
    A reviewed, sealed physical budget/safety termination is an unsuccessful sample.
    Unknown results stay visible in dispositions and never become silent failures.
    """
    counts=dict.fromkeys(('valid','inflight','pending','infrastructure','paused','replay','duplicate'),0)
    records=[];seen=set();cutoff=timestamp(effective)
    for m in matches:
        result=m['result'];review=m['review'];scene=m.get('scene',{});budget=m.get('budget',{});ledger=m.get('ledger',{})
        reset=scene.get('reset_provenance') if isinstance(scene.get('reset_provenance'),dict) else review.get('reset',{})
        rid=reset.get('reset_id');when=timestamp(reset.get('recorded_utc'))
        stop=result.get('stop_reason') or review.get('termination_class') or ledger.get('termination_class')
        if stop=='episode_step_budget' and review.get('termination_class')=='budget_truncation':stop='budget_truncation'
        period='current' if when is not None and cutoff is not None and when>=cutoff else 'history' if when is not None and cutoff is not None else 'unknown'
        flags=[d['human_feedback_used'] for d in (result,scene,review) if type(d.get('human_feedback_used')) is bool]
        assisted='assisted' if flags and all(flags) else 'autonomous' if flags and not any(flags) else 'unknown'
        r={'episode':m['episode'],'campaign':m['key'],'reset_id':rid if isinstance(rid,str) else None,
           'period':period,'stage':'learning','assistance':assisted,'disposition':'pending','native':None,'semantic':None,
           'at':when,'variant':scene.get('variant') if isinstance(scene.get('variant'),str) else None,
           'control':scene.get('pd_profile') if isinstance(scene.get('pd_profile'),str) else None,
           'contract':result.get('completion_contract') or ledger.get('completion_contract'),
           'skill_sha256':result.get('starting_skill_sha256'),'runtime_sha256':budget.get('runtime_sha256'),
           'reason':'封口、独立 reset、审计或配置身份尚未齐全'}
        kind='pending'
        if stop=='user_requested_pause':kind='paused'
        elif result.get('error') or stop in ('infrastructure_error','system_error','system','network_error','usageLimitExceeded'):kind='infrastructure'
        elif review.get('no_replay_or_diagnostic_initial_state') is False or reset.get('method') in ('replay','diagnostic_reset'):kind='replay'
        elif not m.get('result_ref'):kind='inflight'
        elif rid and rid in seen:kind='duplicate'
        else:
            audit_closed=(review.get('full_turn_and_skill_update') is True and review.get('turn_record_integrity')=='complete_terminal_sequence')
            identity=(reset.get('method')=='fresh_environment_reset' and isinstance(rid,str) and rid
                and (not review.get('reset') or review['reset'].get('reset_id')==rid)
                and scene.get('env_id',scene.get('native_env_id'))==native
                and r['variant'] and r['control'] and isinstance(r['contract'],str)
                and sha(r['skill_sha256']) and budget.get('skill_sha256')==r['skill_sha256'] and sha(budget.get('runtime_sha256')))
            terminal=stop in ('native_success','budget_truncation','physical_budget_exhausted','runtime_safety_stop','safety_stop','native_failure','policy_early_stop')
            if (identity and audit_closed and terminal and type(review.get('audited_task_success')) is bool
                and result.get('native_outcome') in ('success','failure','in_progress') and (m.get('actions') or 0)>0):
                kind='valid';r['native']=result['native_outcome']=='success';r['semantic']=review['audited_task_success']
                r['reason']='完整物理预算结束，计未成功' if stop in ('budget_truncation','physical_budget_exhausted') else '安全停止，计未成功' if stop in ('runtime_safety_stop','safety_stop') else '独立完成且已审计'
        if rid and kind!='duplicate':seen.add(rid)
        r['disposition']=kind;counts[kind]+=1
        if kind!='valid':r['reason']={'pending':r['reason'],'inflight':'未封口；当前存活未由计分器核验','infrastructure':'系统/接口中断或结果不确定','paused':'用户暂停','replay':'回放或诊断初始化','duplicate':'重复 reset，不重复计分'}[kind]
        # Manifest comparison uses only explicit hashes; no source path is opened.
        r['evaluation']=m.get('evaluation',{})
        records.append(r)
    stability={'registered':False,'consecutive':None,'required':5,'candidate_sha256':None,'note':'未登记完整固定候选；历史成功不回填'}
    frozen={'registered':False,'planned':10,'native':rate([],'native'),'semantic':rate([],'semantic'),'note':'默认计划 10 回合；批次/seed/reset 清单未登记'}
    manifest=candidate if isinstance(candidate,dict) else {}
    config=manifest.get('config_sha256');registered=timestamp(manifest.get('registered_at'))
    digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest() if isinstance(config,dict) else None
    valid_manifest=(manifest.get('protocol')==PROTOCOL and manifest.get('native_env_id')==native and manifest.get('locked') is True
        and isinstance(config,dict) and set(config)==set(CONFIG_KEYS) and all(sha(v) for v in config.values())
        and manifest.get('candidate_sha256')==digest and registered is not None
        and type(manifest.get('human_feedback_used')) is bool)
    if valid_manifest:
        ids=manifest.get('stability_reset_ids');frozen_ids=manifest.get('frozen_reset_ids')
        valid_ids=lambda ids,n:isinstance(ids,list) and len(ids)==n and all(isinstance(x,str) and x for x in ids) and len(set(ids))==n
        if valid_ids(ids,5):
            stability.update(registered=True,candidate_sha256=digest,consecutive=0,note='同一完整候选；5/5 仅为冻结测评入口，不证明高可靠性')
            byreset={r['reset_id']:r for r in records if r['disposition']!='duplicate'}
            def bound(r):
                e=r['evaluation']
                return (r['at'] is not None and r['at']>=registered and e.get('candidate_sha256')==digest
                    and e.get('config_sha256')==config and e.get('loaded') is True and e.get('config_unchanged') is True
                    and r['skill_sha256']==config['skill'] and r['runtime_sha256']==config['runtime']
                    and r['assistance']==('assisted' if manifest['human_feedback_used'] else 'autonomous'))
            for rid in ids:
                if rid in byreset:byreset[rid]['stage']='stability'
            sequence=0;uncertain=False
            for rid in ids:
                r=byreset.get(rid)
                if not r:break
                if not bound(r) or r['disposition']!='valid':uncertain=True;break
                sequence=sequence+1 if r['semantic'] and r['native'] else 0
            stability['consecutive']=None if uncertain else sequence
            if uncertain:stability['note']='登记回合配置不匹配或结果未知；连续成功待核验，不沿用旧候选计数'
            if sequence==5 and not uncertain and valid_ids(frozen_ids,10) and not set(ids)&set(frozen_ids):
                for rid in frozen_ids:
                    if rid in byreset:byreset[rid]['stage']='frozen'
                rows=[byreset[rid] for rid in frozen_ids if rid in byreset and bound(byreset[rid]) and byreset[rid]['disposition']=='valid']
                frozen.update(registered=True,native=rate(rows,'native'),semantic=rate(rows,'semantic'),note='冻结计划 10；只以实际完成审计样本为分母，未跑的不计失败')
    groups={}
    for r in records:
        if r['disposition']!='valid' or r['stage']!='learning':continue
        key=(r['period'],r['assistance'],r['variant'],r['control'],r['contract'])
        groups.setdefault(key,[]).append(r)
    summaries=[]
    for key,rows in groups.items():
        period,assistance,variant,control,contract=key
        summaries.append({'period':period,'assistance':assistance,'variant':variant,'control':control,'contract':contract,
            'native':rate(rows,'native'),'semantic':rate(rows,'semantic'),'skill_versions':len({r['skill_sha256'] for r in rows}),
            'episodes':[r['episode'] for r in rows]})
    # Totals are inventory only. UI rates render separate condition/assistance groups.
    current=[r for r in records if r['period']=='current' and r['disposition']=='valid' and r['stage']=='learning']
    for r in records:r.pop('evaluation')
    return {'protocol':PROTOCOL,'groups':summaries,'records':records,'dispositions':counts,
            'current':{'native':rate(current,'native'),'semantic':rate(current,'semantic')},'stability':stability,'frozen':frozen,
            'definition':'成功 / 同条件、独立 reset、真实执行、完整封口并审计的完成尝试；预算耗尽与安全停止计未成功。学习累计描述允许技能版本变化，不代表固定策略可靠性。'}
