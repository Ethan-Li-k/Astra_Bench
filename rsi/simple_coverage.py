"""Read-only coverage selection; no model, reset, or control actions."""
import json
import fcntl
import hashlib
from pathlib import Path
from tools.audit_simple_campaigns import episode_status

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'ref/tasks/simple-easy-coverage.json'

def claim_task(env_id, root=ROOT):
    """Hold for the entire episode; distinct environments can run concurrently."""
    folder=root/'artifacts/easy-coverage-20260917/locks'
    folder.mkdir(parents=True,exist_ok=True)
    stream=(folder/(hashlib.sha256(env_id.encode()).hexdigest()+'.lock')).open('a')
    try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        raise ValueError('coverage_task_already_running: '+env_id) from None
    return stream

def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default

def evidence(root=ROOT):
    """Canonical campaigns only; archives/replays and native flags earn no credit."""
    groups = {}
    for campaign in sorted((root/'artifacts/R019').glob('*-campaign')):
        for episode in sorted(campaign.glob('episode-*')):
            result = read(episode/'result.json', {})
            spec = read(episode/'agent/task_specification.json', {})
            scene = read(episode/'video/scene_setup.json', {})
            env = spec.get('env_id') or scene.get('env_id') or result.get('env_id')
            if campaign.name == 'door-campaign': env = 'push_door'
            if not env: continue
            row = groups.setdefault(env, {'env_id':env, 'successes':[], 'attempts':[], 'active':[], 'pending_review':[]})
            if not result:
                if (episode/'user_stop.json').exists(): continue
                row['active'].append(str(episode.relative_to(root))); continue
            stop = read(episode/'user_stop.json', {})
            if (stop.get('reason') == 'user_changed_account_policy'
                    and stop.get('authority') == 'latest explicit user message main account only'):
                row.setdefault('policy_interruptions', []).append(str(episode.relative_to(root)))
                continue  # Raw episode stays intact; account policy change is not a skill failure.
            row['attempts'].append(str(episode.relative_to(root)))
            review = read(episode/'success_review.json', {})
            if result.get('success') and not review:
                row['pending_review'].append(str(episode.relative_to(root)))
            if review.get('audited_task_success') is True and episode_status(episode)['audited_task_success']:
                row['successes'].append({'episode':str(episode.relative_to(root)),
                    'review':str((episode/'success_review.json').relative_to(root)),
                    'scope_note':review.get('limitations'),
                    'formal_credit':False})
    return groups

def snapshot(root=ROOT):
    policy=read(root/'ref/tasks/simple-easy-coverage.json', {})
    groups=evidence(root)
    inventory=read(root/'artifacts/R019/task-inventory.json', {'entries':[]})
    labels={r['task']:r['label'] for r in read(root/'artifacts/R019/simple-success-inventory-20260917/inventory.json', {'tasks':[]})['tasks']}
    done=[dict(r,label=labels.get(env,env),state='completed_no_retry') for env,r in groups.items() if r['successes']]
    done_ids={r['env_id'] for r in done}
    deferred={r['env_id']:r for r in policy.get('deferred',[])}
    candidates=[]
    for r in policy.get('priority',[]):
        if r['env_id'] in done_ids: continue
        attempts=groups.get(r['env_id'],{}).get('attempts',[])
        if len(attempts)>=policy.get('max_new_attempts_per_task',2):
            deferred[r['env_id']]={'env_id':r['env_id'],'reason':'已达到简单覆盖尝试上限，换下一项'}
        elif r['env_id'] not in deferred:
            pending=groups.get(r['env_id'],{}).get('pending_review',[])
            candidates.append(dict(r,attempts=len(attempts),
                **({'state':'awaiting_review','pending_review':pending} if pending else {})))
    scheduled=done_ids|set(deferred)|{r['env_id'] for r in candidates}
    untriaged=[r['id'] for r in inventory['entries'] if r['id'].startswith('simple/G1Wholebody') and r['id'] not in scheduled]
    return dict(policy=policy,completed=done,completed_tasks=len(done),
        audited_successes=sum(len(r['successes']) for r in done),next=candidates,
        deferred=list(deferred.values()),untriaged=untriaged,
        registered_entries=len(inventory['entries']),
        inventory_note='本地 91 个注册入口含机器人与场景变体；60 项精确映射待核对。历史成功按原学习范围标明，不是正式 60 项完成率。')

def require_admission(env_id, root=ROOT):
    policy=read(root/'ref/tasks/simple-easy-coverage.json', {})
    if policy.get('id')=='simple-six-transfer-isaac-20260917':
        from rsi.training_gate import require_training
        return require_training(env_id)
    if not policy.get('active'): return
    if policy.get('id')=='simple-60x5-24h-v1':
        row=next((r for r in policy.get('priority',[]) if r['env_id']==env_id),None)
        if not row or row.get('state')!='ready':
            raise ValueError('Task interface not admitted; capability test required: '+env_id)
        return  # New plan counts fresh complete attempts; no historical success/max2 ban.
    state=snapshot(root)
    if any(r['env_id']==env_id for r in state['completed']):
        raise ValueError('coverage_already_successful_no_retry: '+env_id)
    if any(r['env_id']==env_id for r in state['deferred']):
        raise ValueError('coverage_deferred_choose_an_easy_similar_task: '+env_id)
    if not any(r['env_id']==env_id and r['state']=='ready' for r in state['next']):
        raise ValueError('coverage_preflight_required: '+env_id)
