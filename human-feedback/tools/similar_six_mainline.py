"""UI-only user scope override. Does not launch, stop, or reconfigure experiments."""
import copy
from dashboard import SIX_TASKS, hash_json, timestamp

OVERRIDE = 'human-feedback/dashboard-upgrade/similar-six-mainline-20260917/user-override.json'
PLAN = 'artifacts/six-transfer-20260917/plan.json'
SPLIT = 'artifacts/six-transfer-20260917/task-split.json'
NEW_EXECUTION = 'artifacts/six-transfer-20260917/execution/status.json'
NEW_CAMPAIGNS = 'artifacts/six-transfer-20260917/execution/campaigns'
SCHEDULE = 'artifacts/six-transfer-20260917/schedule.json'
STOP = 'artifacts/harness-reset-20260917/execution/strategy-stop'


def read_override(board):
    doc, ref = board.read(board.root/OVERRIDE)
    return doc if ref and doc.get('mode') == 'similar_training_fixed_six_isaac' else None


def training_projection(board, plan, selected):
    """Exact selected environments and supervisor receipts; never launch work."""
    from simple_breadth import EPISODE
    doc, ref = board.read(board.root/NEW_EXECUTION)
    if not ref or not plan.get('id') or doc.get('plan_id') != plan['id']:
        return [], {}, None, None
    start = timestamp(doc.get('started_at')); updated = timestamp(doc.get('updated_at'))
    if start is None or updated is None or updated < start:
        return [], {}, None, None
    allowed = {r['env_id'] for r in selected}
    lanes = {}; items=[]
    for lane in doc.get('lanes', []):
        env = lane.get('env_id')
        if env not in allowed: continue
        uid = env.split('/')[-1].removesuffix('-v0')
        folder = board.root/NEW_CAMPAIGNS/(uid+'-campaign')
        for ep in board.files(folder, 'episode-*'):
            if not EPISODE.fullmatch(ep.name) or not ep.is_dir(): continue
            spec, sr = board.read(ep/'agent/task_specification.json')
            scene, cr = board.read(ep/'video/scene_setup.json')
            result, rr = board.read(ep/'result.json')
            reset_at = timestamp(scene.get('reset_provenance', {}).get('recorded_utc'))
            if (spec.get('env_id') != env or scene.get('env_id', scene.get('native_env_id')) != env
                    or (result.get('env_id') not in (None, env))
                    or result.get('episode_id') not in (None, ep.name)
                    or reset_at is None or reset_at < start): continue
            key='transfer-'+uid.lower()
            items.append(dict(path=ep, env_id=env, admitted=True, key=key,
                spec=spec, scene=scene, result=result, result_ref=rr,
                sources=[r for r in (sr, cr, rr, ref) if r]))
            if lane.get('episode') == str(ep): lanes[str(ep)] = lane
    tasks=doc.get('tasks', []); totals=doc.get('totals', {})
    counts=None
    if (isinstance(tasks, list) and len({r.get('env_id') for r in tasks}) == len(tasks)
        and all(r.get('env_id') in allowed and type(r.get('complete_attempts')) is int
            and r['complete_attempts'] >= 0 for r in tasks)
        and type(totals.get('complete_attempts')) is int
        and sum(r['complete_attempts'] for r in tasks) == totals['complete_attempts']):
        counts=dict(complete_attempts=totals['complete_attempts'],
            by_task=[dict(env_id=r['env_id'],complete_attempts=r['complete_attempts']) for r in tasks])
    return items, lanes, counts, ref


def project_mainline(board, snapshot, override):
    from simple_breadth import episode_bindings, coverage_snapshot, environment_row
    from coverage_goal import goal_episode_bindings, mark_interruption, read_execution, EXECUTION
    result = copy.deepcopy(snapshot)
    status, ref = board.read(board.root/EXECUTION)
    plan, plan_ref = board.read(board.root/PLAN)
    split, split_ref = board.read(board.root/SPLIT)
    closed, closed_ref = board.read(board.root/STOP/'closed.json')
    closed_lanes = closed.get('lanes', [])
    closeout_verified = bool(closed_ref and closed.get('status') == 'all_old_workers_closed'
        and closed.get('scheduler_stopped') is True
        and closed.get('all_current_requests_returned_complete') is True
        and closed.get('counts_as_task_failure') is False
        and closed_lanes and all(isinstance(r, dict) and r.get('closed') is True
            and r.get('unsettled_requests') == [] and r.get('episode') for r in closed_lanes))
    sealed = {r['episode']: r for r in closed_lanes} if closeout_verified else {}
    candidates = split.get('training_candidates', [])
    tests = split.get('test_tasks', [])
    excluded = {r.get('env_id') for r in split.get('historical_success_exclusions', []) if isinstance(r, dict)}
    candidate_ids = [r.get('env_id') for r in candidates if isinstance(r, dict)]
    split_verified = bool(split_ref and len(tests) == 6
        and {r.get('env_id') for r in tests} == set(SIX_TASKS.values())
        and len(candidate_ids) == len(candidates) == len(set(candidate_ids))
        and all(candidate_ids) and not set(candidate_ids) & (set(SIX_TASKS.values()) | excluded)
        and all(r.get('already_succeeded') is False for r in candidates))
    selected = [dict(label=r['label'], env_id=r['env_id'], similar_to=r.get('similar_to', []),
                     minimum_complete_attempts=r.get('minimum_complete_attempts'),
                     role=r.get('queue_role')) for r in candidates
                if r.get('selected_for_minimum_stage') is True] if split_verified else []
    new_items, new_lanes, new_counts, new_ref = training_projection(board, plan, selected)
    new_paths = {str(r['path']) for r in new_items}
    schedule, schedule_ref = board.read(board.root/SCHEDULE)
    stopped, stop_ref = board.read(board.root/STOP/'status.json')
    boundaries, boundary_ref = board.read(board.root/STOP/'boundaries.json', allow_list=True)
    boundaries = {r['task']:r for r in boundaries if isinstance(r, dict) and isinstance(r.get('task'), str)} if isinstance(boundaries, list) else {}
    # Reuse the read-only process receipt validator. Its old attempt counters are
    # deliberately not published as progress toward the new training/test goal.
    execution = read_execution(board, dict(id=status.get('plan_id'), started_at=status.get('started_at', 0)))
    active_paths = {r.get('episode'):r for r in execution['reported_lanes'] if r.get('episode')}
    stop_confirmed = bool(stop_ref and stopped.get('dispatch_allowed') is False
                          and stopped.get('new_API_requests_allowed') is False)
    if stop_confirmed:
        active_paths = {r.get('episode'):r for r in stopped.get('lanes', []) if isinstance(r, dict) and r.get('episode')}
    history = coverage_snapshot(board)
    labels = {r['env_id']: r['label'] for r in history['completed']}
    labels.update({r['env_id']:r['label'] for r in selected})
    grouped = {}
    for item in [*episode_bindings(board, {}), *goal_episode_bindings(board), *new_items]:
        grouped.setdefault(item['env_id'], []).append(item)
    current, past = [], []
    for env, items in grouped.items():
        item = max(items, key=lambda x: (
            timestamp(x['scene'].get('reset_provenance', {}).get('recorded_utc')) or 0, str(x['path'])))
        key = item.get('key', item['path'].parent.name.removesuffix('-campaign'))
        board.simple_catalog[key] = (labels.get(env, env), item['path'].parent.name, 0)
        row = environment_row(board, item, labels.get(env, env), False)
        if str(item['path']) in new_paths:
            lane = new_lanes.get(str(item['path']), {})
            stage = lane.get('progress', {}).get('current_stage')
            row.update(goal=5, who='统一 SIMPLE 框架主管',
                mode='API · gpt-6-astra/xhigh · 新主线训练',
                next='完整尝试后提炼首个偏离点；同任务顺序吸收经验，累计五次。',
                problem=('当前阶段：'+stage+'；阶段声明不是成功审计。') if stage else '等待本回合下一条公开观察、动作或阶段回执。')
            if not row['terminal']:
                row['state_label'] = '新主线训练 · 完整等待推理/动作' if lane.get('real_process_alive') is True else '新主线回合 · 等待进程回执'
            row['summary'] = f"{row['name']} · {row['episode']} · 动作 {row['actions'] or 0} · {row['state_label']}"
            row['nav_label'] = row['name']+' · '+row['state_label']
            current.append(row)
            continue
        row.update(goal=0, who='统一 SIMPLE 框架主管', mode='原计划回执；不计入新主线训练或测试',
                   next='已有成功仅提取经验；旧请求在确认边界收尾，不派发重复回合。')
        interrupted = mark_interruption(board, item, row)
        closure = sealed.get(str(item['path']))
        if closure and not interrupted:
            row.update(terminal=True, state='infraerror', state_label='旧计划已收尾 · 不计任务失败',
                       summary=f"{row['name']} · {row['episode']} · 用户调整主线后收尾",
                       nav_label=row['name']+' · 旧计划已收尾')
            video = closure.get('video') or {}
            if video.get('path') == str(item['path']/'video/episode.mp4'):
                playable = board.completed_video(item['path'], key, closed_ref, '原策略画面 · 旧计划收尾录像')
                if playable:
                    row['videos'] = [dict(playable, task=row['name'], outcome=row['state_label'])]
                    row['video_note'] = '用户调整主线后封口的连续录像；不计完整任务尝试。'
        lane = active_paths.get(str(item['path']))
        boundary = boundaries.get(lane.get('task_key'), {}) if lane else {}
        if lane and boundary.get('alive') is False and not row['terminal']:
            row.update(terminal=True, state='infraerror', state_label='旧计划已收尾 · 不计任务失败',
                       summary=f"{row['name']} · {row['episode']} · 用户调整主线后收尾",
                       nav_label=row['name']+' · 旧计划已收尾')
        if lane and not row['terminal'] and not interrupted:
            row.update(state_label='旧计划收尾 · 非新主线训练/测评',
                problem=('旧计划新回合与下一次API请求已禁用；仅回收已发请求和动作。' if stop_confirmed
                         else '正在撤销原广覆盖调度；仅完整回收已发请求和动作，新指令是否生效以主管回执为准。'))
            if type(lane.get('actions')) is int and row['actions'] is None:
                row['actions'] = lane['actions']
            row['summary'] = f"{row['name']} · {row['episode']} · {row['state_label']}"
            row['nav_label'] = row['name']+' · '+row['state_label']
            current.append(row)
        else:
            past.append(row)
    current.sort(key=lambda r:r['last_action_at'] or 0, reverse=True)
    simple = result['tasks'][0]
    simple.update(name='SIMPLE · 相似任务训练 → 六项 Isaac 测试', subtasks=current, history_subtasks=past,
        scope_notice='主线固定：相似且尚未成功任务训练；原六项在一致设置下作 Isaac 测试。已有成功任务不复试。',
        summary='撤销60项各5次的覆盖计划。历史成功保留为经验，旧计划全部收尾。' if closeout_verified else '旧计划正在收尾；新训练/测试分开。',
        prerequisite_note='六项：XMovePick、BendPick、Handover、Mobile P&P、Grasp、XMoveBendPick。',
        problem=('旧计划新派发已禁用；训练排除表与 Isaac 测试设置正在绑定。' if stop_confirmed
                 else '等待统一主管的停止派发回执、训练排除表与 Isaac 测试设置绑定。'),
        next='筛选尚未成功的相似任务，复用历史原子技能；冻结技能与设置后测试原六项。',
        who='统一 SIMPLE 框架主管', backend='Isaac 在线测试目标；实际后端待运行证据',
        mode='API · gpt-6-astra/xhigh', variant='训练与固定六项测试分离；成功经验不重复采集',
        source_at=max([r['at'] for r in (ref, plan_ref, split_ref, closed_ref, stop_ref, boundary_ref) if r] or [timestamp(override.get('recorded_at')) or 0]),
        last_action_at=max((r['last_action_at'] for r in current if r['last_action_at']), default=None),
        state='active-unknown' if current else 'engineering-prep',
        state_label=f'{len(new_lanes)} 路新主线训练；旧计划已收尾' if new_lanes else '旧计划已全部收尾；新主线准备中' if closeout_verified else f'{len(current)} 个旧计划回合正在收尾；新主线另计')
    simple['version'] = hash_json({k:v for k,v in simple.items() if k != 'version'})
    result['simple_coverage'] = dict(active=True, mainline=dict(
        id=override['id'], tests=[dict(label=k, env_id=v) for k,v in SIX_TASKS.items()],
        historical_success_reuse_only=True, selected_training=selected, training_counts=new_counts,
        schedule=schedule if schedule_ref and schedule.get('schema') == 'six-transfer-active-schedule-v1' else None,
        training_status=(f'已选 {len(selected)} 项训练，各至少5次；{len(new_lanes)}路已绑定新回合，计划最多4路' if new_lanes else f'已选 {len(selected)} 项训练，各至少5次；首批2路、计划最多4路，尚未启动' if selected else '等待统一主管发布相似任务训练清单'),
        test_status='Isaac测试尚未核验；不使用事后渲染视频冒称在线测试',
        closeout_status=(f"旧{len(closed_lanes)}路已全部收尾，{sum(r.get('model_requests_completed', 0) for r in closed_lanes)}次请求已完整回收；另存的历史未知请求未重发。" if closeout_verified else '旧计划新回合与下一次API请求已禁用' if stop_confirmed else '等待旧计划停止派发回执'),
        plan_source=PLAN if plan_ref else None, plan_phase=plan.get('status')),
        environments=current, completed=[], completed_tasks=len(history['completed']),
        audited_successes=history['audited_successes'], active_environments=len(current),
        goal=None, window_metrics=None, formal_scheduling='not_started',
        **{k:execution.get(k) for k in ('actual_parallel','live_workers','paused_workers','parallel_target','source_at','reported_lanes')})
    if closeout_verified:
        result['simple_coverage'].update(actual_parallel=0, live_workers=0, paused_workers=0,
            parallel_target=0, reported_lanes=[], source_at=closed_ref['at'])
    if new_ref:
        result['simple_coverage'].update(
            actual_parallel=sum(r.get('real_process_alive') is True and (r.get('actions') or 0)>0 for r in new_lanes.values()),
            live_workers=sum(r.get('real_process_alive') is True for r in new_lanes.values()),
            paused_workers=None, parallel_target=plan.get('initial_training_parallelism'),
            source_at=new_ref['at'], reported_lanes=[], formal_scheduling='training_active',
            new_mainline_execution=True)
        simple['source_at']=max(simple['source_at'], new_ref['at'])
        simple['problem']='相似训练正在进行；固定六项Isaac测试的实际后端与接入仍待核验。'
        simple['version'] = hash_json({k:v for k,v in simple.items() if k != 'version'})
    result['notice'] = '相似任务训练 → 六项固定设置 Isaac 测试；历史成功只作经验，60×5已撤销。'
    return result
