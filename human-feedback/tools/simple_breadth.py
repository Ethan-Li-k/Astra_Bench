"""Public read-only projection of the authoritative one-success coverage policy."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import re
from tools.audit_simple_campaigns import turn_completeness

CAMPAIGN = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*-campaign')
EPISODE = re.compile(r'episode-[0-9]{4,8}')
ENV = re.compile(r'simple/[A-Za-z][A-Za-z0-9_-]*-v[0-9]+')


def episode_bindings(board, policy):
    """Only canonical direct children; policy admission never supplies a read path."""
    priority = {r['env_id']: r for r in policy.get('priority', [])
                if isinstance(r, dict) and isinstance(r.get('env_id'), str) and ENV.fullmatch(r['env_id'])}
    bindings = []
    for campaign in board.files(board.root/'artifacts/R019', '*-campaign'):
        if not CAMPAIGN.fullmatch(campaign.name) or not campaign.is_dir():
            continue
        for episode in board.files(campaign, 'episode-*'):
            if not EPISODE.fullmatch(episode.name) or not episode.is_dir():
                continue
            spec, sref = board.read(episode/'agent/task_specification.json')
            scene, cref = board.read(episode/'video/scene_setup.json')
            result, rref = board.read(episode/'result.json')
            ids = [d[k] for d in (spec, scene, result) for k in ('env_id', 'native_env_id') if d.get(k)]
            if campaign.name == 'door-campaign' and not ids:
                ids = ['push_door']
            if not ids or len(set(ids)) != 1:
                continue
            env = ids[0]
            if not isinstance(env, str) or not (ENV.fullmatch(env) or (campaign.name == 'door-campaign' and env == 'push_door')):
                continue
            if result.get('episode_id') not in (None, episode.name):
                continue
            entry = priority.get(env)
            admitted = bool(entry and entry.get('state') == 'ready' and
                            spec.get('env_id') == env and scene.get('env_id', scene.get('native_env_id')) == env)
            # New priority tasks require both exact bindings, even if an aggregate claims success.
            if entry and not admitted:
                continue
            if campaign.name == 'door-campaign':
                env = 'push_door'
            bindings.append(dict(path=episode, env_id=env, admitted=admitted,
                                 spec=spec, scene=scene, result=result, result_ref=rref,
                                 sources=[r for r in (sref, cref, rref) if r]))
    return bindings


def admitted_campaigns(board):
    policy, _ = board.read(board.root/'ref/tasks/simple-easy-coverage.json')
    if not policy.get('active'):
        return {}
    groups = {}
    for item in episode_bindings(board, policy):
        if item['admitted']:
            groups.setdefault(item['path'].parent.name, []).append(item)
    # A mixed environment campaign is ambiguous, never bind it by its newest name.
    return {name: items for name, items in groups.items() if len({i['env_id'] for i in items}) == 1}


def review_reset_matches(review, scene):
    """Accept both existing audit schemas; the optional flag is not a new gate.

    New audits bind their full reset receipt instead of repeating a top-level
    independent_reset_verified flag. Check that binding without inventing or
    rewriting the producer's task verdict.
    """
    reset = scene.get('reset_provenance', {})
    reviewed = review.get('reset', {})
    if not isinstance(reset, dict) or not isinstance(reviewed, dict):
        return False
    fields = ('reset_id', 'seed', 'method', 'launch', 'post_settle_qpos_qvel_sha256')
    if any(key in reviewed and reviewed[key] != reset.get(key) for key in fields):
        return False
    if 'independent_reset_verified' in review:
        return review['independent_reset_verified'] is True
    launch = reviewed.get('launch', {})
    return (all(key in reviewed and key in reset for key in fields) and
            reviewed['method'] == 'fresh_environment_reset' and
            isinstance(reviewed['reset_id'], str) and bool(reviewed['reset_id']) and
            type(reviewed['seed']) is int and isinstance(launch, dict) and
            isinstance(launch.get('boot_id'), str) and bool(launch['boot_id']) and
            type(launch.get('pid')) is int and launch['pid'] > 0 and
            type(launch.get('start_ticks')) is int and launch['start_ticks'] >= 0 and
            isinstance(reviewed['post_settle_qpos_qvel_sha256'], str) and
            re.fullmatch(r'[a-f0-9]{64}', reviewed['post_settle_qpos_qvel_sha256']) is not None)


def audited_success(board, item):
    """Reuse terminal validation, with safe local receipts; native flags earn no credit."""
    episode = item['path']; result = item['result']
    review, ref = board.read(episode/'success_review.json')
    if not (ref and review.get('audited_task_success') is True and
            result.get('success') is True and result.get('native_outcome') == 'success' and
            type(result.get('actions')) is int and result['actions'] > 0 and
            result.get('skill_updated') and not result.get('error') and
            review_reset_matches(review, item['scene'])):
        return False
    reset = item['scene'].get('reset_provenance', {})
    reviewed_reset = review.get('reset', {}).get('reset_id')
    if reviewed_reset and reviewed_reset != reset.get('reset_id'):
        return False
    if isinstance(review.get('task'), str) and ENV.fullmatch(review['task']) and review['task'] != item['env_id']:
        return False
    if item['admitted'] and (not reset.get('reset_id') or reset.get('method') != 'fresh_environment_reset'):
        return False
    # Web reads never chase externally referenced API/recovery documents. Those
    # contracts require a separate bounded public audit before this projection.
    if result.get('api_continuation') or result.get('turn_record_contract') == 'api-terminal-sequence-v1':
        return False
    try:
        board.safe(episode)
        for path in episode.glob('turn_*.json'):
            doc, tref = board.read(path)
            if not tref or doc.get('_rsi_terminal', {}).get('recovery_reason') == 'no_new_physical_progress':
                return False
        complete, _ = turn_completeness(episode, result)
    except (OSError, ValueError, TypeError):
        return False
    return complete


def coverage_snapshot(board):
    """Bounded safe equivalent of the coverage selector; no runtime/actor imports."""
    policy, _ = board.read(board.root/'ref/tasks/simple-easy-coverage.json')
    bindings = episode_bindings(board, policy); groups = {}; seen_resets = set()
    labels, _ = board.read(board.root/'artifacts/R019/simple-success-inventory-20260917/inventory.json')
    labels = {r['task']: r['label'] for r in labels.get('tasks', [])}
    for item in bindings:
        env = item['env_id']; ep = str(item['path'].relative_to(board.root))
        row = groups.setdefault(env, dict(env_id=env, successes=[], attempts=[]))
        if item['result_ref'] and board.physical_evidence(item['path']):
            row['attempts'].append(ep)
        reset = item['scene'].get('reset_provenance', {}).get('reset_id')
        if audited_success(board, item) and (not reset or (env, reset) not in seen_resets):
            row['successes'].append(dict(episode=ep))
            if reset: seen_resets.add((env, reset))
    done = [dict(row, label=labels.get(env, env), state='completed_no_retry')
            for env, row in groups.items() if row['successes']]
    done_ids = {r['env_id'] for r in done}
    deferred = {r['env_id']: r for r in policy.get('deferred', [])}; candidates = []
    for entry in policy.get('priority', []):
        env = entry['env_id']
        if env in done_ids: continue
        attempts = len(groups.get(env, {}).get('attempts', []))
        if attempts >= policy.get('max_new_attempts_per_task', 2):
            deferred[env] = dict(env_id=env, reason='已达到简单覆盖尝试上限，换下一项')
        elif env not in deferred:
            candidates.append(dict(entry, attempts=attempts))
    inventory, _ = board.read(board.root/'artifacts/R019/task-inventory.json')
    scheduled = done_ids | set(deferred) | {r['env_id'] for r in candidates}
    return dict(policy=policy, completed=done, audited_successes=sum(len(r['successes']) for r in done),
                next=candidates, deferred=list(deferred.values()), bindings=bindings,
                untriaged=[r['id'] for r in inventory.get('entries', []) if r['id'].startswith('simple/G1Wholebody') and r['id'] not in scheduled],
                registered_entries=len(inventory.get('entries', [])),
                inventory_note='本地注册入口含机器人与场景变体；60 项精确映射待核对。历史成功按原学习范围标明，不是正式 60 项完成率。')


def environment_row(board, item, label, retired):
    from dashboard import LABELS, public_time
    ep = item['path']; result = item['result']; rref = item['result_ref']
    public, pref = board.read(ep/'public-progress.json')
    if public.get('episode_id') != ep.name: public = {}; pref = None
    action, aref = board.latest_physical_action(ep)
    if action is None and type(result.get('actions')) is int: action = result['actions']
    review, audit_ref = board.read(ep/'success_review.json')
    accepted = audited_success(board, item)
    phase_at = public_time(public, pref) if pref else None
    state = 'engineering-prep'
    if rref:
        state = 'complete' if accepted else 'review'
        if review.get('audited_task_success') is False: state = 'audit-rejected'
        elif review.get('audited_task_success') is True and not accepted: state = 'audit-unverified'
    elif pref and (not aref or phase_at >= aref['at']):
        state = {'inference_waiting': 'modelwaiting', 'inference_waiting_no_deadline': 'modelwaiting',
                 'action_executing': 'physicsrunning', 'infrastructure_error': 'infraerror',
                 'safety_stop': 'safetystop', 'connection_unverified': 'active-unknown'}.get(public.get('state'), 'active-unknown')
    elif aref:
        state = 'active-unknown'
    labels = dict(LABELS, review='终态已封口 · 待独立审计', complete='独立审计成功 · 退出重试',
                  **{'engineering-prep': '已准入 · 环境准备', 'audit-rejected': '终态审计未通过', 'audit-unverified': '审计已通过 · 证据绑定或完整终态待核对'})
    refs = [*item['sources'], *[r for r in (pref, aref, audit_ref) if r]]
    key = item.get('key', ep.parent.name.removesuffix('-campaign'))
    video = board.completed_video(ep, 'simple-'+key, rref, 'SIMPLE / MuJoCo 连续录像；含诊断视角，非 RTC。')
    if video: video = dict(video, task=label, outcome=labels[state])
    row = dict(id=key, name=label, native_env_id=item['env_id'], campaign=ep.parent.name,
               environment_id=str(ep.relative_to(board.root)), reset_id=item['scene'].get('reset_provenance', {}).get('reset_id'),
               episode=ep.name, actions=action, last_action_at=aref['at'] if aref else None,
               last_action_time_basis='已完成 execution 回执文件时间', phase_report_at=phase_at,
               source_at=max((r['at'] for r in refs), default=None), sources=refs, state=state, state_label=labels[state],
               success=int(accepted), goal=1, retired=retired, terminal=bool(rref), audit_pending=bool(rref and state=='review'),
               result_success=result.get('success') if rref else None,
               who='唯一物理主管 01a0a867', backend='SIMPLE / MuJoCo；非 RTC', mode='辅助账号 · 一次成功覆盖',
               variant=item['env_id'], preview=board.preview(ep, 'simple-'+key), videos=[video] if video else [],
               video_note='当前回合已封口。' if video else '当前连续录像尚未封口或未通过验签；不播放开放录制文件。',
               problem='终态与审计分别计数；原生事件、管理状态和预检均不计成功。' if rref else '执行阶段取自本回合公开回执；陈旧状态不证明进程仍存活。',
               next='已成功退出重试，保留证据。' if retired else '由原主管审计终态。' if rref else '由原主管继续本独立环境；完整等待在途推理。')
    if state == 'audit-unverified':
        row['problem'] = '已有成功审计；网页尚不能确认其重置绑定或 host 完整终态。此项不是未审计。'
        row['next'] = '由原主管核对现有审计绑定或完整终态证据；不重跑已审计任务。'
    row['summary'] = f"{label} · {ep.name} · 动作 {action if action is not None else '未知'} · {labels[state]}"
    row['nav_label'] = label+' · '+labels[state]
    if not rref and board.progress_clips:
        row['progress_clip'] = board.progress_clips.request(board, ep, 'simple-'+key)
    return row


def project(board, snapshot):
    from similar_six_mainline import read_override, project_mainline
    mainline = read_override(board)
    if mainline:
        return project_mainline(board, snapshot, mainline)
    from coverage_goal import read_plan, project_goal
    goal = read_plan(board)
    if goal:
        return project_goal(board, snapshot, goal)
    policy=board.root/'ref/tasks/simple-easy-coverage.json'
    policy_doc, policy_ref=board.read(policy)
    if not policy_ref: return snapshot
    state=coverage_snapshot(board)
    if not state.get('policy',{}).get('active'): return snapshot
    result=copy.deepcopy(snapshot)
    simple=result['tasks'][0]
    rows=[*simple.get('subtasks',[]),*simple.get('history_subtasks',[])]
    campaign_env={item['episode'].split('/')[2]:done['env_id'] for done in state['completed'] for item in done['successes']}
    for row in rows:
        catalog=board.simple_catalog.get(row.get('id'))
        inferred=campaign_env.get(catalog[1]) if catalog else None
        if not row.get('native_env_id'):
            row['native_env_id']=inferred or (row.get('name') if str(row.get('name','')).startswith('simple/') else None)
    by_env={}
    for row in rows:
        if row.get('native_env_id'): by_env.setdefault(row['native_env_id'],row)
    completed=[]
    done_ids={r['env_id'] for r in state['completed']}
    labels={r['env_id']:r.get('label',r['env_id']) for r in state['policy'].get('priority',[])}
    environments=[]
    for campaign,items in admitted_campaigns(board).items():
        item=items[-1];env=item['env_id']
        live=environment_row(board,item,labels.get(env,env),env in done_ids)
        environments.append(live)
        rows=[r for r in rows if r['id']!=live['id']];rows.append(live)
        by_env[env]=live
    for done in state['completed']:
        env=done['env_id'];live=by_env.get(env,{})
        if env=='push_door': live=next((r for r in rows if r.get('id')=='door'),live)
        episodes=[s['episode'].split('/')[-1] for s in done['successes']]
        folder=board.root/done['successes'][-1]['episode']
        _,result_ref=board.read(folder/'result.json')
        success_video=board.completed_video(folder,'coverage-'+folder.parent.name,result_ref,'已审计成功回合 · 原始策略相机')
        if success_video: success_video.update(task=done['label'],outcome='完整任务审计成功')
        completed.append(dict(env_id=env,label=done['label'],successes=len(episodes),episodes=episodes,
            detail_id=live.get('id'),video=success_video,
            scope='历史学习变体；非正式测评',state='completed_no_retry'))
    done_ids={r['env_id'] for r in completed}
    deferred={r['env_id']:r for r in state['deferred']}
    for row in rows:
        env=row.get('native_env_id')
        row['goal']=1
        if env in done_ids:
            row['nav_label']=row['name']+' · 已成功，退出重试'
            row['next']='已满足一次完整审计成功；不再开新回合。保留原在途回执并在确认边界收尾。'
        elif env in deferred:
            row['nav_label']=row['name']+' · 暂缓'
            row['next']='当前阶段暂缓：'+deferred[env]['reason']
    stopped,stop_ref=board.read(board.root/'artifacts/R019/handover-campaign/episode-0004/user_stop.json')
    if (stop_ref and stopped.get('reason')=='user_strategy_change_easy_once' and
        all(stopped.get(k) is True for k in ('acknowledged','process_exited','actor_exited','physics_action_completed','video_finalized','not_task_failure','not_success'))):
        for row in rows:
            if row.get('native_env_id')=='simple/G1WholebodyHandoverTeleop-v0' and row.get('episode')=='episode-0004':
                row.update(state='paused',state_label='用户调整策略 · 已停止',
                    summary='Handover 已有一次完整审计成功；重复的 episode-0004 已在确认动作边界停止，不计失败或新增成功。',
                    problem='已停止重复探索；完整录像已封存。',source_at=stop_ref['at'])
                video=board.completed_video(board.root/'artifacts/R019/handover-campaign/episode-0004','coverage-handover-stop',stop_ref,'用户策略切换前 · 原始录像')
                if video:
                    video.update(task='Handover',outcome='用户策略切换停止；非失败、非新成功')
                    row['videos']=[video,*row.get('videos',[])];row.setdefault('sources',[]).append(stop_ref)
    nextrows=[]
    preflights=[]
    preflight_dirs={'simple/G1WholebodyHandoverSimToRealTeleop-v0':'handover-sim','simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0':'handover-place-back-sim'}
    for i,entry in enumerate(state['next']):
        env=entry['env_id'];live=by_env.get(env)
        if live is None:
            live=dict(id='coverage-'+hashlib.sha256(env.encode()).hexdigest()[:12],name=entry['label'],native_env_id=env,success=0,goal=1,
                state='engineering-prep',state_label='已准入 / 未开始' if entry.get('state')=='ready' else '待准入 / 未开始',summary=entry['label']+'：尚无新回合物理证据。',
                problem='等待精确任务准入和独立 reset。',next=entry['reuse'],who='原 SIMPLE 主管',
                backend='尚未物理加载',mode='一次成功覆盖',variant=env,source_at=policy_ref['at'],
                last_action_at=None,preview=None,videos=[],sources=[])
        preflight_dir=preflight_dirs.get(env)
        if preflight_dir:
            preflight,ref=board.read(board.root/'artifacts/easy-coverage-20260917/preflight'/preflight_dir/'result.json')
            if ref and preflight.get('status')=='passed' and preflight.get('task_success_credit') is False:
                preflights.append(dict(env_id=env,state='standing_preflight_passed',sim_s=preflight.get('elapsed_sim_s'),source_at=ref['at']))
                if live['state']=='engineering-prep' and not live.get('actions'):
                    live['problem']='独立 7 秒站立预检通过；等待独立环境启动证据。预检不计任务成功。'
                    live['source_at']=ref['at'];live['sources'].append(ref)
        nextrows.append(live)
    # Keep the exact legacy records accessible for videos and feedback.
    priority_ids={r['id'] for r in nextrows}
    nextrows=[r for r in nextrows if r['id'] not in {e['id'] for e in environments}]
    nextrows=[*[e for e in environments if not e['retired']],*nextrows]
    priority_ids={r['id'] for r in nextrows}
    simple['subtasks']=nextrows
    simple['history_subtasks']=[r for r in rows if r['id'] not in priority_ids]
    simple.update(name='SIMPLE · 简单任务覆盖',summary=f"已有 {len(completed)} 类任务/学习变体成功，成功后不再重试。优先相似短流程任务。",
        next=' → '.join(r['label'] for r in state['next']) or '等待下一简单任务登记',
        scope_notice='当前策略：简单相似任务优先；一次完整成功即退出。难任务暂缓，180 正式测评暂停。',
        prerequisite_note=state['inventory_note'])
    pending=sum(e['audit_pending'] for e in environments)
    active=[e for e in environments if not e['terminal'] and not e['retired']]
    simple.update(state='review' if pending else 'active-unknown' if active else 'engineering-prep',
        state_label=f'{len(active)} 个独立环境未封口 · {pending} 个终态待审计',
        summary=f'{len(completed)} 类已审计完成 · {pending} 个终态待审计 · {len(active)} 个独立环境未封口',
        last_action_at=max((e['last_action_at'] for e in environments if e['last_action_at']),default=None))
    simple['version']=hashlib.sha256(json.dumps({k:v for k,v in simple.items() if k!='version'},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    result['simple_coverage']=dict(active=True,completed_tasks=len(completed),audited_successes=state['audited_successes'],
        environments=environments,pending_audit=pending,active_environments=len(active),completed=completed,next=state['next'],preflights=preflights,deferred=state['deferred'],untriaged=state['untriaged'],
        registered_entries=state['registered_entries'],inventory_note=state['inventory_note'],
        requested_task_count=state['policy'].get('requested_task_count'),exact_mapping=state['policy'].get('exact_60_mapping'),
        psi_amo=state['policy'].get('psi_amo',{}),policy_source='ref/tasks/simple-easy-coverage.json',
        policy_updated_at=policy_ref['at'],observed_at=datetime.datetime.now(datetime.timezone.utc).timestamp(),
        formal_scheduling='paused',success_rule='一次独立重置并通过完整任务审计；弱原生事件不计。')
    result['notice']='简单相似任务优先，成功一次退出；困难任务暂缓。页面刷新与物理动作时间分开，排队不代表运行。'
    return result
