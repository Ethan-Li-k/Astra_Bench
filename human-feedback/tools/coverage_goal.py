"""Read-only 24-hour goal projection; no scheduler, model call or second ledger."""
import copy
import math
import re
from dashboard import hash_json, timestamp

PLAN = 'artifacts/harness-reset-20260917/plan.json'
EXECUTION = 'artifacts/harness-reset-20260917/execution/status.json'
INVENTORY = 'artifacts/harness-reset-20260917/task-inventory/exact60.json'
CAMPAIGNS = 'artifacts/harness-reset-20260917/execution/campaigns'


def mark_interruption(board, item, row):
    """Recognize explicit owner receipts; a stale timestamp alone is not a stop."""
    stopped, ref = board.read(item['path']/'infrastructure-stop.json')
    if not ref or stopped.get('complete_attempt') is not False:
        return False
    unknown = (stopped.get('state') == 'infrastructure_interrupted_unknown_request'
        and stopped.get('episode') == str(item['path'])
        and stopped.get('physical_failure') is False and stopped.get('automatic_replay') is False)
    no_post = (stopped.get('no_request_sent') is True and stopped.get('actions') == 0
        and stopped.get('reset_id') == row.get('reset_id') and bool(row.get('reset_id')))
    if not (unknown or no_post):
        return False
    label = '基础设施中断 · 请求结果未知' if unknown else '请求发出前已停止 · 不计尝试'
    row.update(terminal=True, audit_pending=False, state='infraerror', state_label=label,
        interruption=True, complete_attempt=False, success=0, result_success=None,
        source_at=max(row.get('source_at') or 0, ref['at']),
        problem=('旧现场已消失；已完成动作保留，请求结果待核查，不重发、不记物理失败。' if unknown
                 else '接线错误发生在API请求与物理动作之前；已停止，不计模型失败或完整尝试。'),
        next='保留原始回执与已有画面；由统一主管修复基础设施，新尝试必须独立重置。')
    row['sources'].append(ref)
    row['summary'] = f"{row['name']} · {row['episode']} · {label} · 已确认动作 {row['actions'] if row['actions'] is not None else 0}"
    row['nav_label'] = row['name']+' · '+label
    return True


def goal_episode_bindings(board):
    """Only the new supervisor's exact inventory and fixed campaign root."""
    from simple_breadth import EPISODE, ENV
    inventory, _ = board.read(board.root/INVENTORY)
    bindings = []
    for entry in inventory.get('tasks', []):
        if not isinstance(entry, dict):
            continue
        uid, env = entry.get('task_uid'), entry.get('env_id')
        if (not isinstance(uid, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', uid)
                or not isinstance(env, str) or not ENV.fullmatch(env)):
            continue
        folder = board.root/CAMPAIGNS/(uid+'-campaign')
        for ep in board.files(folder, 'episode-*'):
            if not EPISODE.fullmatch(ep.name) or not ep.is_dir():
                continue
            spec, sr = board.read(ep/'agent/task_specification.json')
            scene, cr = board.read(ep/'video/scene_setup.json')
            result, rr = board.read(ep/'result.json')
            ids = [d[k] for d in (spec, scene, result) for k in ('env_id', 'native_env_id') if d.get(k)]
            if (spec.get('env_id') != env or scene.get('env_id', scene.get('native_env_id')) != env
                    or set(ids) != {env} or result.get('episode_id') not in (None, ep.name)):
                continue
            bindings.append(dict(path=ep, env_id=env, admitted=True, key='goal-'+uid.replace('_','-'),
                spec=spec, scene=scene, result=result, result_ref=rr,
                sources=[r for r in (sr, cr, rr) if r]))
    return bindings


def read_execution(board, plan):
    """Project the supervisor's public ledger, never create a competing count."""
    status, ref = board.read(board.root/EXECUTION)
    inventory, iref = board.read(board.root/INVENTORY)
    ids = [r.get('env_id') for r in inventory.get('tasks', []) if isinstance(r, dict)]
    identity_ok = len(ids) == 60 and len(set(ids)) == 60 and all(isinstance(i, str) for i in ids)
    output = dict(source=EXECUTION, source_at=ref['at'] if ref else None,
                  inventory_source=INVENTORY, exact_mapping_verified=bool(iref and identity_ok),
                  official_60_benchmark=False, window_metrics=None, actual_parallel=None,
                  live_workers=None, paused_workers=None, parallel_target=None,
                  reported_lanes=[], task_progress=[], count_status='等待统一主管完整回合回执')
    if not ref:
        return output
    at = timestamp(status.get('updated_at'))
    if (at is None or at < plan['started_at'] or status.get('plan_id') != plan['id']
            or status.get('started_at') != plan['started_at']):
        output['count_status'] = '主管回执尚未绑定本次窗口'
        return output
    output['source_at'] = at
    output['execution_stage'] = status.get('stage') if isinstance(status.get('stage'), str) else None
    if type(status.get('parallel_target')) is int and 1 <= status['parallel_target'] <= 60:
        output['parallel_target'] = status['parallel_target']
    allowed_states = {'running', 'acting', 'modelwaiting', 'inference_waiting', 'physicsrunning', 'action_executing'}
    lanes = status.get('lanes', [])
    if isinstance(lanes, list):
        for row in lanes:
            if not isinstance(row, dict):
                continue
            clean = {k:row.get(k) for k in ('task_key', 'env_id', 'episode', 'route', 'state', 'actions', 'complete_attempts')
                     if row.get(k) is None or type(row.get(k)) in (str, int, float, bool)}
            clean['reported_running'] = row.get('state') in allowed_states and type(row.get('pid')) is int and row['pid'] > 0
            output['reported_lanes'].append(clean)
    if type(status.get('actual_parallel')) is int and 0 <= status['actual_parallel'] <= 60:
        output['actual_parallel'] = status['actual_parallel']
    tasks = status.get('tasks', [])
    if not isinstance(tasks, list):
        output['count_status'] = '主管任务计数格式待核验'
        return output
    task_ids = [r.get('env_id') for r in tasks if isinstance(r, dict)] if isinstance(tasks, list) else []
    valid_tasks = (identity_ok and len(task_ids) == len(tasks) and len(set(task_ids)) == len(task_ids)
                   and set(task_ids) <= set(ids))
    if not valid_tasks:
        output['count_status'] = '任务清单或计数绑定待核验；不将注册变体数当已覆盖任务'
        return output
    for row in tasks:
        output['task_progress'].append({k:row.get(k) for k in ('env_id', 'complete_attempts', 'successes', 'blocking')
                                        if row.get(k) is None or type(row.get(k)) in (str, int, float, bool)})
    totals = status.get('totals', {})
    names = ('complete_attempts', 'attempted_tasks', 'tasks_at_least_five')
    if not isinstance(totals, dict) or not all(type(totals.get(k)) is int and totals[k] >= 0 for k in names):
        output['count_status'] = '主管尚未提供本窗口完整三项计数'
        return output
    if (totals['tasks_at_least_five'] > totals['attempted_tasks'] or totals['attempted_tasks'] > 60
            or totals['complete_attempts'] < 5*totals['tasks_at_least_five']):
        output['count_status'] = '主管计数内部不一致，等待复核'
        return output
    if (any(type(r.get('complete_attempts')) is not int or r['complete_attempts'] < 0 for r in tasks)
            or sum(r['complete_attempts'] for r in tasks) != totals['complete_attempts']):
        output['count_status'] = '逐任务完整次数与主管汇总不一致，等待复核'
        return output
    if (sum(r['complete_attempts'] > 0 for r in tasks) != totals['attempted_tasks']
            or sum(r['complete_attempts'] >= 5 for r in tasks) != totals['tasks_at_least_five']):
        output['count_status'] = '逐任务覆盖数与主管汇总不一致，等待复核'
        return output
    output['window_metrics'] = {k:totals[k] for k in names}
    if (isinstance(lanes, list) and all(isinstance(r, dict) for r in lanes)
            and len({r.get('env_id') for r in lanes}) == len(lanes)):
        checks = {
            'active_lanes': sum(r.get('real_process_alive') is True for r in lanes),
            'service_paused_lanes': sum(r.get('real_process_alive') is True and r.get('service_paused') is True for r in lanes),
            'acting_lanes': sum(r.get('real_process_alive') is True and r.get('service_paused') is False
                and type(r.get('actions')) is int and r['actions'] > 0 for r in lanes),
        }
        if all(type(totals.get(k)) is int and totals[k] == n for k, n in checks.items()):
            output.update(live_workers=checks['active_lanes'], paused_workers=checks['service_paused_lanes'],
                          actual_parallel=checks['acting_lanes'])
    output['count_status'] = '读取统一主管完整终态计数；网页不独立累加'
    if output['execution_stage'] == 'automatic_review_blocked':
        output['count_status'] = 'API调度启动被自动审批拒绝；等待主管已发出的网关与仿真数据范围确认。新批次尚未启动。'
    return output


def read_plan(board):
    doc, ref = board.read(board.root / PLAN)
    if not ref or doc.get('id') != 'simple-60x5-24h-20260917':
        return None
    keys = ('started_at', 'deadline_at', 'target_tasks',
            'minimum_complete_attempts_per_task', 'target_complete_attempts',
            'initial_parallel_target')
    if any(type(doc.get(k)) not in (int, float) or not math.isfinite(doc[k]) for k in keys):
        return None
    if (doc['deadline_at'] <= doc['started_at'] or doc['target_tasks'] != 60
            or doc['minimum_complete_attempts_per_task'] != 5
            or doc['target_complete_attempts'] != 300 or doc['initial_parallel_target'] < 1):
        return None
    return {k: doc.get(k) for k in (*keys, 'id', 'preferred_route', 'model', 'effort', 'stage')}


def project_goal(board, snapshot, plan):
    # Existing canonical episode/media projection remains authoritative for each
    # observation. Historical successes never become this window's denominator.
    from simple_breadth import episode_bindings, coverage_snapshot, environment_row
    result = copy.deepcopy(snapshot)
    simple = result['tasks'][0]
    history = coverage_snapshot(board)
    grouped = {}
    for item in [*episode_bindings(board, {}), *goal_episode_bindings(board)]:
        grouped.setdefault(item['env_id'], []).append(item)
    inventory, _ = board.read(board.root/'artifacts/R019/simple-success-inventory-20260917/inventory.json')
    labels = {r['task']: r['label'] for r in inventory.get('tasks', [])}
    environments, old_rows = [], []
    for env, items in grouped.items():
        item = max(items, key=lambda x: (
            timestamp(x['scene'].get('reset_provenance', {}).get('recorded_utc')) or 0,
            str(x['path'])))
        if env == 'push_door':
            continue  # The legacy synthetic push-door variant is history only.
        campaign = item['path'].parent.name
        key = item.get('key', campaign.removesuffix('-campaign'))
        board.simple_catalog[key] = (labels.get(env, env), campaign, 5)
        row = environment_row(board, item, labels.get(env, env), False)
        reset_at = timestamp(item['scene'].get('reset_provenance', {}).get('recorded_utc'))
        in_window = reset_at is not None and plan['started_at'] <= reset_at < plan['deadline_at']
        row.update(goal=5, retired=False, who='统一 SIMPLE 调度主管',
                   mode='API 优先；实际路线以回合回执为准',
                   window_eligible_reset=in_window, historical=not in_window,
                   next='完整等待本回合终态；每项新窗口内至少五次完整尝试，历史成功用于经验。')
        if row['state'] == 'complete':
            row['state_label'] = '本回合独立审计成功 · 五次覆盖另计'
        row['nav_label'] = row['name'] + ' · ' + row['state_label']
        if mark_interruption(board, item, row):
            old_rows.append(row)
        elif in_window or not row['terminal']:
            environments.append(row)
        else:
            old_rows.append(row)
    environments.sort(key=lambda r: r['last_action_at'] or 0, reverse=True)
    simple.update(name='SIMPLE · 24 小时覆盖', subtasks=environments,
                  history_subtasks=old_rows, scope_notice='60 个精确任务，每项至少 5 次新独立完整尝试；历史不抵扣。',
                  summary='先逐项覆盖，再轮转补足五次；成功、证据充分的失败、系统中断分开。',
                  prerequisite_note='60 项精确映射与完整计数读取统一主管回执，不把本地所有注册变体凑成 60 项。',
                  next='API 并行推进；复用相似经验，每次结束补充首个偏离点与下一次改变。',
                  problem='新窗口计数等待统一主管完整终态回执；接口准备与实际运行分别显示。',
                  who='统一 SIMPLE 调度主管', backend='物理与视觉后端按各回合回执显示',
                  mode='API 优先 · 60项各五次完整尝试',
                  variant='本项目选定60个注册环境；不冒称官方固定60项',
                  last_action_at=max((r['last_action_at'] for r in environments if r['last_action_at']), default=None),
                  source_at=plan['started_at'],
                  state='active-unknown' if environments else 'engineering-prep',
                  state_label=f'{len(environments)} 个当前或待收尾回合；实际并发待主管回执')
    simple['version'] = hash_json({k: v for k, v in simple.items() if k != 'version'})
    completed = [dict(env_id=r['env_id'], label=r['label'], successes=len(r['successes']),
                      scope='历史学习经验；不抵扣新窗口五次', state='historical_success')
                 for r in history['completed']]
    execution = read_execution(board, plan)
    for lane in execution['reported_lanes']:
        for row in environments:
            if (row['terminal'] or lane.get('env_id') != row['native_env_id']
                    or lane.get('episode') != str(board.root/row['environment_id'])):
                continue
            if type(lane.get('actions')) is int and lane['actions'] == 0 and row['actions'] is None:
                row['actions'] = 0
            if lane.get('state') == 'api_service_paused':
                row.update(state='infraerror', state_label='API接线暂停 · 原场景保留',
                    problem='主管报告API调用边界暂停，尚不算任务失败。原场景保留，未知请求不重发。',
                    next='由统一主管核查精确异常边界，修复接线后继续实验。')
            elif lane.get('state') == 'initializing_or_model_planning':
                row.update(state='active-unknown', state_label='API初始化或规划 · 尚无动作回执')
            row['summary'] = f"{row['name']} · {row['episode']} · 动作 {row['actions'] if row['actions'] is not None else '未知'} · {row['state_label']}"
            row['nav_label'] = row['name']+' · '+row['state_label']
    simple['problem'] = execution['count_status']
    simple['source_at'] = execution['source_at'] or plan['started_at']
    if execution.get('execution_stage') == 'automatic_review_blocked':
        simple['state'] = 'infraerror'
        simple['state_label'] = '等待API外发范围确认 · 新批次尚未启动'
        simple['next'] = '统一主管已发出确认问题；确认后启动同一调度器。继续本地检查，不重发未知请求。'
    if execution['actual_parallel'] is not None:
        simple['state_label'] += f" · 主管回执实际并发 {execution['actual_parallel']}"
    simple['version'] = hash_json({k: v for k, v in simple.items() if k != 'version'})
    result['simple_coverage'] = dict(active=True, goal=plan, environments=environments,
        completed=completed, completed_tasks=len(completed), audited_successes=history['audited_successes'],
        active_environments=sum(not r['terminal'] for r in environments),
        pending_audit=sum(r['audit_pending'] for r in environments),
        next=[], deferred=[], untriaged=[], psi_amo={}, preflights=[],
        inventory_note='历史成功保留作经验；新目标按窗口内完整终态计数。',
        formal_scheduling='paused', **execution)
    result['notice'] = 'API 优先 · 60任务×5次完整尝试 · 历史经验持续复用 · 排队、预检和中断不凑次数。'
    return result
