#!/usr/bin/env python3
"""One-shot, read-only handoff check. No daemon, model, launch, signal or plan edit.
Call after the existing owner seals a terminal; the existing Grasp waiter owns dispatch.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/six-transfer-20260917'
OUT = BASE / 'pipeline-unblock-20260918'


def read(path):
    return json.loads(Path(path).read_text())


def safe_read(path):
    try:
        return read(path)
    except (OSError, ValueError):
        return {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owner_ack_checker():
    path = BASE/'mp-training-entry-20260918/continue_as_training_reviewed.py'
    spec = importlib.util.spec_from_file_location('existing_native_closure', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # stdlib imports only; __main__/prepare never called
    return module.complete_ack_receipt


def closure(episode, checker=None):
    """Reuse the existing native ACK check, then verify public tool/model closure."""
    episode = Path(episode)
    try:
        result = read(episode/'result.json')
        receipts = sorted((episode/'main-actor/api-continuation').glob('*/calls/*/receipt.json'))
        route=safe_read(episode/'main-actor/api-route-receipt.json')
        provider=route.get('safe_provider_evidence') or {}
        latest=read(receipts[-1]) if receipts else {}
        if (route.get('reset_id') and route['reset_id']==result.get('reset_id')
                and route.get('terminal_class')=='known_http_rejection'
                and provider.get('response_body_complete') is True
                and 400 <= (provider.get('http_status') or 0) < 500
                and latest.get('error_type')=='ProviderHTTPError'
                and isinstance(latest.get('finished_at_unix'),(int,float))
                and abs(latest['finished_at_unix']-(route.get('finished_at') or 0))<2):
            return dict(state='blocked_known_provider_rejection',
                reason=f"HTTP {provider['http_status']} rejected the request; original receipt retained. Owner must verify ACKs before the authorized main-account continuation.",
                episode=str(episode),reset_id=result['reset_id'],
                http_status=provider['http_status'],request_replayed=False,
                evidence=str(episode/'main-actor/api-route-receipt.json'))
        if any(read(p).get('state') != 'completed' for p in receipts):
            return dict(state='blocked_unknown_request', reason='Original API request unresolved; no replay.', episode=str(episode))
        if result.get('error'):
            return dict(state='blocked_engineering', reason=result['error'], episode=str(episode))
        requests = sorted((episode/'main-actor/agent/rpc_calls').glob('*_request.json'))
        if not requests or any(not p.with_name(p.name.replace('_request', '_result')).is_file() for p in requests):
            raise ValueError('Missing public tool ACK')
        for p in requests:
            read(p.with_name(p.name.replace('_request', '_result')))
        turns = sorted((episode/'main-actor').glob('turn_*.json'))
        model_closed = bool(receipts) and all(read(p).get('state') == 'completed' for p in receipts)
        if turns:
            model_closed = read(turns[-1]).get('status') == 'completed' and not read(turns[-1]).get('error')
        if not model_closed:
            return dict(state='blocked_model_boundary', reason='No completed model boundary.', episode=str(episode))
        if checker is None and (episode/'main-actor/native-actions.jsonl').is_file():
            path = BASE/'official-wbc-candidate-20260917/terminal-return-min-two-20260918/collect.py'
            spec = importlib.util.spec_from_file_location('existing_wbc_closure', path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            result, _ = module.verify(episode)  # existing WBC read-only verifier, never collect/main
            ack = dict(reset_id=result['reset_id'], ack_count=result['actions'],
                       native_success=result['native_success'], result=str(episode/'result.json'),
                       actions=str(episode/'main-actor/native-actions.jsonl'))
        else:
            ack = (checker or owner_ack_checker())(episode)
        return dict(state='closed_success' if ack['native_success'] else 'closed_failure', episode=str(episode),
                    reset_id=ack['reset_id'], actions=ack['ack_count'], evidence=ack,
                    optional_review_blocks=False, repeat_successful_training=False)
    except (OSError, ValueError, KeyError, RuntimeError, AssertionError) as error:
        return dict(state='blocked_evidence', reason=str(error), episode=str(episode))


def assess(snapshot):
    """Pure decision view; explicit plan gates remain authoritative."""
    plan = snapshot['plan']
    lanes = snapshot.get('lanes', [])
    target = snapshot.get('parallel_target', 2)
    active = {r['episode'] for r in lanes if r.get('worker_alive') and r.get('episode')}
    blocked_lanes = {r.get('lane_id') for r in lanes if r.get('lane_id') and r.get('state', '').startswith('blocked_')}
    successes = {r.get('env_id') for r in lanes if r.get('state') == 'closed_success'}
    global_allowed = plan.get('new_training_launch_allowed') is True
    scope = set(plan.get('launch_scope', []))
    free = max(0, target-len(active))
    handoffs, blockers = [], []
    for c in snapshot.get('candidates', []):
        reason = None
        if c.get('env_id') in successes or c.get('already_succeeded'):
            reason = 'success_is_experience_only'
        elif not global_allowed:
            reason = 'explicit_plan_training_disabled'
        elif c.get('env_id') not in scope:
            reason = 'outside_current_training_scope'
        elif c.get('lane_id') in blocked_lanes:
            reason = 'this_lane_has_unresolved_boundary'
        elif not c.get('ready'):
            reason = c.get('blocking', 'assets_or_entry_not_ready')
        elif c.get('active_episode') in active:
            reason = 'already_running'
        elif free == 0:
            reason = 'native_capacity_full'
        if reason:
            blockers.append(dict(env_id=c.get('env_id'), lane_id=c.get('lane_id'), reason=reason, owner=c.get('owner')))
            continue
        identity = [snapshot.get('event_id'), c.get('lane_id'), c['env_id'], c['owner'], c.get('entry')]
        handoffs.append(dict(event_id=hashlib.sha256(json.dumps(identity).encode()).hexdigest(),
            env_id=c['env_id'], lane_id=c.get('lane_id'), owner=c['owner'], entry=c.get('entry'),
            action='existing_waiter_will_dispatch' if c.get('owner_waiter_alive') else 'owner_start_existing_entry',
            recheck_current_gate=True, new_independent_reset=True, replay=False,
            optional_review_blocks=False, executable_by_this_tool=False))
        free -= 1
    return dict(contract='rsi-pipeline-health-v1', at=snapshot.get('at', time.time()),
        event_id=snapshot.get('event_id'), parallel_target=target, actual_native_workers=len(active),
        available_slots=max(0, target-len(active)), under_target=len(active)<target,
        lanes=lanes, handoffs=handoffs, blockers=blockers,
        related_tests_allowed=plan.get('test_launch_allowed') is True,
        no_global_block_from_lane_failure=True, launches_performed=0,
        readiness_warnings=snapshot.get('readiness_warnings',[]),
        integration='Existing owner calls once after sealed result; Grasp existing single-owner two-slot dispatcher dispatches when capacity is free; one shared five-attempt budget. No new manager or model audit.',
        limit='Read-only; absent owner/waiter requires explicit owner action. This report does not authorize bypassing plan or prove a new reset ran.')


def process_snapshot():
    outputs, pids = {}, set()
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args = path.read_bytes().decode().split('\0'); pid = int(path.parent.name); pids.add(pid)
            if '--output' not in args:
                continue
            output = args[args.index('--output')+1]
            native = any(Path(x).name == 'run.py' or Path(x).name.startswith('check_training_loop') for x in args)
            if native and str(BASE) in output:
                outputs.setdefault(output, []).append(pid)
        except (OSError, UnicodeError, ValueError, IndexError):
            pass
    return outputs, pids


def live_snapshot(event_episode=None):
    plan = read(BASE/'plan.json'); outputs, pids = process_snapshot(); lanes = []
    for output, process_ids in outputs.items():
        result = safe_read(Path(output)/'result.json')
        lanes.append(dict(episode=output, env_id=result.get('task_id'), worker_alive=True,
                          worker_pids=process_ids, state='active_native_worker'))
    event = None
    if event_episode:
        episode = Path(event_episode).resolve()
        if not episode.is_relative_to(BASE):
            raise ValueError('Event episode must be an RSI six-transfer artifact')
        result = safe_read(episode/'result.json')
        event = hashlib.sha256((str(episode)+sha(episode/'result.json')).encode()).hexdigest()
        if str(episode) not in outputs:
            lanes.append(dict(closure(episode), env_id=result.get('task_id'), worker_alive=False))
    # Classify only inactive known lane outputs; one lane's boundary never closes the plan.
    for relative in ('mp-training-entry-20260918/training-lane-state.json',
                     'official-wbc-candidate-20260917/training-continuation/state.json',
                     'grasp-training-entry-20260918/training-lane-state.json',
                     'grasp-training-entry-20260918/training-lane-state-slot2.json'):
        state = safe_read(BASE/relative)
        output = state.get('current_episode')
        if output and output not in outputs and not any(r.get('episode') == output for r in lanes):
            episode = Path(output).resolve()
            if episode.is_relative_to(BASE):
                result = safe_read(episode/'result.json')
                lanes.append(dict(closure(episode), env_id=result.get('task_id') or state.get('env_id'),
                    lane_id=('grasp_slot2' if 'slot2' in relative else 'grasp_slot1') if 'grasp-training' in relative else relative, worker_alive=False))
    grasp = BASE/'grasp-training-entry-20260918'
    dispatcher = safe_read(grasp/'dispatcher-state.json')
    resource = safe_read(grasp/'scene2-path-receipt.json')
    candidates, slot_blocks = grasp_candidates(grasp, dispatcher, resource, pids)
    lanes.extend(slot_blocks)
    return dict(at=time.time(), event_id=event, plan=plan, lanes=lanes,
                candidates=candidates, parallel_target=2, readiness_warnings=resource.get('remaining_source_missing_references',[]))


def grasp_candidates(grasp, dispatcher, resource, pids, states=None):
    """Read the existing owner's two reservations; never allocate a third budget."""
    ready = resource.get('launch_ready') is True
    remaining = dispatcher.get('remaining_effective_attempts', 0)
    reserved = dispatcher.get('reserved_effective_attempts', 0)
    available = max(0, remaining-reserved) if isinstance(remaining,int) and isinstance(reserved,int) else 0
    candidates, blocks = [], []
    for slot, filename in enumerate(('training-lane-state.json', 'training-lane-state-slot2.json')):
        state = states[slot] if states is not None else safe_read(grasp/filename)
        if not state or str(slot) in dispatcher.get('active', {}):
            continue
        lane_id = f'grasp_slot{slot+1}'
        blocked = dispatcher.get('blocked_slots', {}).get(str(slot))
        if blocked:
            blocks.append(dict(lane_id=lane_id, state='blocked_owner_boundary', reason=blocked,
                worker_alive=False, episode=state.get('current_episode')))
        candidates.append(dict(env_id='simple/G1WholebodyTabletopGraspMP-v0', lane_id=lane_id,
            owner='/root/official_mp_fastpath', entry=str(grasp/'launch.sh'),
            ready=ready and available>0, blocking='existing_owner_budget_reserved_or_asset_not_ready',
            owner_waiter_alive=dispatcher.get('pid',state.get('pid')) in pids,
            active_episode=state.get('current_episode'), state_source=str(grasp/filename),
            already_succeeded=any(r.get('native_success') is True for r in dispatcher.get('records',[]))))
        if not blocked:
            available=max(0,available-1)
    return candidates, blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event-episode', type=Path)
    parser.add_argument('--snapshot', type=Path, help='isolated fixture instead of reading live processes')
    parser.add_argument('--output', type=Path, help='optional receipt only within pipeline-unblock artifact directory')
    args = parser.parse_args()
    report = assess(read(args.snapshot) if args.snapshot else live_snapshot(args.event_episode))
    if args.output:
        path = args.output.resolve()
        if not path.is_relative_to(OUT.resolve()):
            raise ValueError('Output outside assigned pipeline evidence directory')
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n'); temp.replace(path)
    print(json.dumps(report, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
