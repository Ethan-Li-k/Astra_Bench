#!/usr/bin/env python3
"""Compact, read-only experiment evidence interface. Never calls a model or acts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/six-transfer-20260917'
OUT = BASE / 'efficiency'
TOKEN_KEYS = ('input', 'cached_input', 'uncached_input', 'cache_write_input', 'output', 'reasoning_output')


def read(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {} if default is None else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def normalize(raw, api=False):
    names = ('input_tokens', 'output_tokens') if api else ('inputTokens', 'outputTokens')
    inp, output = (raw.get(k) for k in names)
    cached = ((raw.get('input_tokens_details') or {}).get('cached_tokens') if api
              else raw.get('cachedInputTokens'))
    written = ((raw.get('input_tokens_details') or {}).get('cache_write_tokens') if api
               else raw.get('cacheWriteInputTokens'))
    reasoning = ((raw.get('output_tokens_details') or {}).get('reasoning_tokens') if api
                 else raw.get('reasoningOutputTokens'))
    return dict(input=inp, cached_input=cached, cache_write_input=written,
                uncached_input=max(0, inp-cached) if isinstance(inp, int) and isinstance(cached, int) else None,
                output=output, reasoning_output=reasoning)


def delta(current, previous):
    # First observation is a baseline, not a claim about the preceding hour.
    if not previous:
        return None
    result = {}
    for key in TOKEN_KEYS:
        a, b = current.get(key), previous.get(key)
        result[key] = a-b if isinstance(a, int) and isinstance(b, int) and a >= b else None
    return result


def scan_cli(path, cache):
    """Incremental metadata only; do not retain message text, images or reasoning."""
    state = cache.setdefault(str(path), {})
    stat = path.stat()
    if state.get('schema') != 3 or state.get('inode') != stat.st_ino or state.get('offset', 0) > stat.st_size:
        state.clear()
    state['schema'] = 3
    state['inode'] = stat.st_ino
    tools, items = Counter(state.get('tools', {})), Counter(state.get('items', {}))
    durations = Counter(state.get('duration_ms_by_kind', {}))
    with path.open('rb') as stream:
        stream.seek(state.get('offset', 0))
        while True:
            line = stream.readline()
            if not line or not line.endswith(b'\n'):
                break  # A concurrent partial record is read on the next review.
            state['offset'] = stream.tell()
            try:
                event = json.loads(line)
            except ValueError:
                continue
            method = event.get('method')
            params = event.get('params') or {}
            if method == 'thread/tokenUsage/updated':
                usage = params.get('tokenUsage') or {}
                # total is cumulative; repeated notifications must not be summed.
                state['usage'] = normalize(usage.get('total') or {})
                state['last_request'] = normalize(usage.get('last') or {})
                state['first_request'] = state.get('first_request') or state['last_request']
                state['usage_at_ms'] = event.get('emittedAtMs')
                state['context_window'] = usage.get('modelContextWindow')
            elif method == 'item/tool/call':
                tools[params.get('tool', 'unknown')] += 1
            elif method == 'item/completed':
                item = params.get('item') or {}
                items[item.get('type', 'unknown')] += 1
                ms = item.get('durationMs')
                if isinstance(ms, (int, float)) and ms >= 0:
                    kind = item.get('tool') or item.get('type', 'unknown')
                    durations[kind] += ms
    state['tools'], state['items'] = dict(tools), dict(items)
    state['duration_ms_by_kind'] = dict(durations)
    return {k: state.get(k) for k in ('usage', 'last_request', 'first_request',
                                     'usage_at_ms', 'context_window', 'tools', 'items', 'duration_ms_by_kind')}


def api_usage(episode):
    totals = Counter(); present = Counter(); states = Counter(); seconds = []
    seen = set(); missing = 0
    for path in episode.glob('api-continuation/*/calls/*/receipt.json'):
        if path.resolve() in seen:
            continue
        seen.add(path.resolve())
        receipt = read(path); states[receipt.get('state', 'unknown')] += 1
        usage = receipt.get('usage')
        if not usage:
            missing += 1
            continue
        for key, value in normalize(usage, api=True).items():
            if isinstance(value, int):
                totals[key] += value; present[key] += 1
        start, end = receipt.get('started_at_unix'), receipt.get('finished_at_unix')
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start:
            seconds.append(end-start)
    return dict(known_usage={key: totals[key] if present[key] else None for key in TOKEN_KEYS},
                usage_field_request_counts=dict(present),
                receipt_states=dict(states), requests=len(seen), usage_missing=missing,
                request_seconds_known=sum(seconds),
                request_median_seconds=statistics.median(seconds) if seconds else None)


def brief_status(base=BASE):
    state = read(base/'execution/status.json'); lanes = []
    for lane in state.get('lanes', []):
        episode = Path(lane['episode']); progress = read(episode/'task-progress.json')
        spec = read(episode/'agent/task_specification.json')
        physical = {}
        host_samples = episode/'progress-host/samples.jsonl'
        if 'Handover' in lane['env_id'] and host_samples.exists():
            first_right = first_left = latest = None
            for line in host_samples.open():
                try:
                    sample = json.loads(line)
                except ValueError:
                    continue
                if sample.get('right_retained') and first_right is None:
                    first_right = sample.get('time')
                if sample.get('left_retained') and first_left is None:
                    first_left = sample.get('time')
                latest = sample
            physical = dict(first_right_retained_sim_s=first_right,
                            first_left_retained_sim_s=first_left,
                            latest_sample=latest,
                            source=str(host_samples),
                            milestone_does_not_imply_complete_task=True)
        lanes.append(dict(task=lane['env_id'], episode=str(episode), route=lane.get('route'),
                          state=lane.get('state'), actions=progress.get('actions', lane.get('actions')),
                          wall_seconds=max(0,time.time()-lane['started_at']) if lane.get('started_at') else None,
                          simulation_seconds=progress.get('sim_s'), stage=progress.get('current_stage'),
                          stage_is_actor_claim=True, outcome=progress.get('outcome'),
                          stop_reason=progress.get('stop_reason'),
                          host_milestones=physical,
                          curriculum_loaded=(spec.get('curriculum_contract') or {}).get('level'),
                          native_terminal_loaded=bool(spec.get('native_terminal_contract'))))
    native = []
    patterns = (
        ('mp-training-entry-20260918/bend-training-*/result.json',
         'mp-training-entry-20260918/training-lane-state.json'),
        ('official-wbc-candidate-20260917/xmove-training-*/result.json',
         'official-wbc-candidate-20260917/training-continuation/state.json'))
    patterns=list(patterns)
    explicit_pointer_paths=set()
    for spec in read(base/'plan.json').get('training_lane_sources',[]):
        parent=Path(spec['episode_parent'])
        pointer=Path(spec['pointer'])
        try:
            relative_pointer=str(pointer.relative_to(base.relative_to(ROOT)))
            explicit_pointer_paths.add(relative_pointer)
            patterns.append((str(parent.relative_to(base.relative_to(ROOT))/spec['result_glob']),relative_pointer))
        except ValueError:
            continue
    for pattern, pointer_path in patterns:
        candidates = sorted(base.glob(pattern))
        pointer = read(base/pointer_path)
        pointed = pointer.get('current_episode')
        if not pointed:
            records = pointer.get('records') or []
            if isinstance(records, dict):
                records = list(records.values())
            pointed = next((r.get('episode') for r in reversed(records)
                            if isinstance(r, dict) and isinstance(r.get('episode'), str)), None)
        result_path = None
        if pointed:
            episode = Path(pointed)
            if not episode.is_absolute():
                episode = ROOT/episode
            expected_parent = base/pattern.split('/')[0]
            if episode.resolve().parent == expected_parent.resolve():
                result_path = episode/'result.json'
        if result_path is None and candidates and pointer_path not in explicit_pointer_paths:
            result_path = candidates[-1]
        if result_path is None:
            continue
        result = read(result_path)
        episode = result_path.parent
        live = read(episode/'main-actor/public/live.json')
        if not result.get('reset_id') or live.get('reset_id') != result['reset_id']:
            live = {}
        phase = result.get('phase', pointer.get('phase'))
        stop_path = episode/'main-actor/user_stop.json'
        boundary_stop = read(stop_path)
        safely_paused = (boundary_stop.get('reason') == 'user_stop_at_completed_boundary'
            and boundary_stop.get('inference_interrupted') is False
            and boundary_stop.get('next_model_action_executed') is False)
        if safely_paused:
            phase = 'user_paused_at_known_boundary'
        elif (phase == 'policy_running' and result.get('error')
              and result.get('wall_s') is not None and pointed
              and pointer.get('phase') == 'paused'):
            # The owner has sealed this failed worker; retain its raw phase above.
            phase = 'engineering_interrupted'
        wall_seconds = (result.get('wall_s') if phase in
            ('complete', 'closed_known', 'engineering_interrupted', 'user_paused_at_known_boundary')
            else max(0,time.time()-result['started_at']) if result.get('started_at') else None)
        if safely_paused and wall_seconds is None and result.get('started_at'):
            wall_seconds = max(0, stop_path.stat().st_mtime-result['started_at'])
        native.append(dict(episode=str(episode), task=result.get('task_id', result.get('env_id')),
            role=result.get('role', 'training'), phase=phase, original_result_phase=result.get('phase'),
            reset_id=result.get('reset_id'),
            actions=live.get('actions', result.get('actions')), native_limit=result.get('native_limit'),
            stage=live.get('stage'), stage_is_actor_claim=True,
            native_success=result.get('native_success'),
            native_terminal_observed=result.get('native_terminal_observed'),
            task_failure=result.get('task_failure'),
            counts_as_training=result.get('counts_as_training'),
            wall_seconds=wall_seconds, route=result.get('account_route'),
            stop_reason=boundary_stop.get('reason') if safely_paused else result.get('stop_reason'),
            error=result.get('error')))
    roles = read(base/'task-roles-v2.json')
    plan = read(base/'plan.json')
    return dict(updated_at=time.time(), legacy_execution_updated_at=state.get('updated_at'),
                lanes=lanes, native_training_lanes=native,
                minimum_training_parallelism=plan.get('minimum_training_parallelism'),
                dashboard_pipeline=read(ROOT/'artifacts/api-first-20260916/web/runboard.json').get('runboard',{}).get('pipeline',{}),
                training_launch_allowed=plan.get('new_training_launch_allowed') is True,
                test_launch_allowed=plan.get('test_launch_allowed') is True,
                automatic_family_unlock_enabled=plan.get('automatic_family_unlock_enabled') is True,
                family_policy=roles.get('unlock'),
                family_gate_evidence_counts={r['label']:len(r.get('unlock_evidence', []))
                    for r in roles.get('training_tasks', [])},
                family_gate_note='Evidence counts are not independently validated success or test admission.')


def review():
    now = time.time(); cache = read(OUT/'scan-cache.json'); previous = read(OUT/'latest.json')
    old = {r['episode']: r for r in previous.get('episodes', [])}
    status = brief_status(); active = {r['episode']: r for r in status['lanes']}
    active.update({r['episode']: r for r in status['native_training_lanes']
                   if r.get('phase') in ('construct_native_env', 'policy_running') and not r.get('error')})
    episodes = []
    candidates = [(p, p) for p in (BASE/'execution/campaigns').glob('*-campaign/episode-*') if p.is_dir()]
    for pattern in ('mp-training-entry-20260918/bend-training-*',
                    'official-wbc-candidate-20260917/xmove-training-*'):
        candidates.extend((p, p/'main-actor') for p in BASE.glob(pattern)
                          if p.is_dir() and (p/'main-actor').is_dir())
    for episode, actor_root in sorted(candidates):
        cli_path = actor_root/'app_server/rpc_out.jsonl'
        api = api_usage(actor_root)
        if not cli_path.exists() and not api['requests']:
            continue
        cli = scan_cli(cli_path, cache) if cli_path.exists() else {}
        result = read(episode/'result.json'); progress = read(episode/'task-progress.json')
        if not progress and actor_root != episode:
            live = read(actor_root/'public/live.json')
            if live.get('reset_id') and live.get('reset_id') == result.get('reset_id'):
                progress = live
        actions = progress.get('actions', result.get('actions', 0)) or 0
        prior = old.get(str(episode), {})
        launch = read(episode.parent/(episode.name+'-launch.json'))
        new_in_window = bool(previous.get('updated_at') and
            (launch.get('started_at') or result.get('started_at') or 0) >= previous['updated_at'])
        zero = {key:0 for key in TOKEN_KEYS} if new_in_window else None
        data = dict(episode=str(episode), active=str(episode) in active, actions=actions,
                    wall_seconds=active.get(str(episode),{}).get('wall_seconds',result.get('wall_s')),
                    new_actions=actions-prior['actions'] if prior and actions >= prior.get('actions', 0) else None,
                    cli=cli, api=api,
                    cli_delta=delta(cli.get('usage') or {}, (prior.get('cli') or {}).get('usage') or zero),
                    api_delta=delta(api['known_usage'], (prior.get('api') or {}).get('known_usage') or zero),
                    stop_reason=result.get('stop_reason'), outcome=progress.get('outcome'))
        if data['active']:
            items = cli.get('items') or {}; tools = cli.get('tools') or {}
            data['shell_calls_per_action'] = round(items.get('commandExecution', 0)/actions, 2) if actions else None
            data['existing_interfaces_over_10_calls'] = {k:v for k,v in tools.items() if v > 10}
        episodes.append(data)
    ranked = sorted((r for r in episodes if r['active']),
                    key=lambda r: (r['cli'].get('last_request') or {}).get('input') or 0, reverse=True)
    findings = []
    for row in ranked:
        calls = (row['cli'].get('items') or {}).get('commandExecution', 0)
        if calls > 10:
            findings.append(dict(episode=row['episode'], kind='repeated_shell_overhead_candidate',
                evidence=dict(shell_calls=calls, acknowledged_actions=row['actions'],
                    ratio=row.get('shell_calls_per_action'), last_request_input=(row['cli'].get('last_request') or {}).get('input')),
                next_action='Inspect repeated observation extraction/action construction; reuse an existing compact interface. Counts alone do not prove wasted calls.'))
    report = dict(schema='rsi-efficiency-review-v1', updated_at=now,
                  interval_seconds=now-previous['updated_at'] if previous.get('updated_at') else None,
                  first_observation_is_baseline=not bool(previous), status=status, episodes=episodes,
                  findings=findings, account_snapshot=read(OUT/'account-snapshot.json'),
                  caveats=['Cached input is not equivalent to uncached cost; no monetary total inferred.',
                           'Cache-write is reported separately, never added to input or uncached input; uncached means input minus cache-read.',
                           'Reasoning output is a subset of output, not additional tokens.',
                           'Missing usage is unknown, never zero. Shared account usage includes other tasks.',
                           'Root/manager chat token usage and other-person same-setting baseline are unavailable.',
                           'No model calls, action execution or source evidence deletion performed.'])
    write(OUT/'scan-cache.json', cache); write(OUT/'latest.json', report)
    write(OUT/'history'/f'{int(now)}.json', report)
    return dict(report_path=str(OUT/'latest.json'), interval_seconds=report['interval_seconds'],
                window_deltas=[dict(episode=r['episode'],cli=r['cli_delta'],api=r['api_delta'])
                    for r in episodes if any(v for block in (r['cli_delta'],r['api_delta'])
                                              for v in (block or {}).values() if isinstance(v,int))],
                active=[dict(episode=r['episode'], actions=r['actions'], cli=r['cli'].get('usage'),
                             last_input=(r['cli'].get('last_request') or {}).get('input'),
                             shell_per_action=r.get('shell_calls_per_action')) for r in ranked],
                findings=findings[:1], fourfold_comparison='unverified: no matched baseline')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'review'])
    args = parser.parse_args()
    print(json.dumps(brief_status() if args.command == 'status' else review(), ensure_ascii=False, indent=2))
