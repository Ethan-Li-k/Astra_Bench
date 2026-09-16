"""Summarize completed grasp trials and host-only exact-replay evidence."""
import argparse
import json
from pathlib import Path


def contacts(tick):
    fingers = {'left': set(), 'right': set()}
    for contact in tick['contacts']:
        if contact['normal_force_n'] <= .01 or 'diagnostic_cube_geom' not in contact['geoms']:
            continue
        for name in contact['geoms']:
            for side in fingers:
                for finger in ('thumb', 'index', 'middle'):
                    if name.startswith(f'{side}_hand_{finger}_'):
                        fingers[side].add(finger)
    return fingers


def replay_metrics(directory, episode_id):
    replay = json.loads((directory/'replay_result.json').read_text())
    ticks = json.loads((directory/'video/host_diagnostics.json').read_text())['ticks']
    initial_z = ticks[0]['cube_world_m'][2]
    longest = current = 0
    first_success = None
    for tick in ticks:
        fingers = contacts(tick)
        qualified = tick['cube_world_m'][2]-initial_z >= .05 and any(
            len(fingers[s]) >= 2 and tick['gripper_closure'][s] > .1 for s in fingers)
        current = current+1 if qualified else 0
        longest = max(longest, current)
        if current == 25 and first_success is None:
            first_success = tick['sim_s']
    last = ticks[-1]
    result = {
        'actor_access': False, 'source_episode': episode_id, 'gpt_calls': 0,
        'replay_counts_as_new_success': False,
        'residual_difference_max_m': max(abs(c['residual_difference_m']) for c in replay['comparisons']),
        'initial_cube_z_m': initial_z,
        'max_lift_m': max(t['cube_world_m'][2]-initial_z for t in ticks),
        'final_lift_m': last['cube_world_m'][2]-initial_z,
        'longest_qualifying_hold_s': longest*.02,
        'terminal_qualifying_hold_s': current*.02,
        'first_success_sim_s': first_success, 'end_sim_s': last['sim_s'],
        'final_finger_contacts': {s: sorted(f) for s, f in contacts(last).items()},
        'final_table_contact': any(set(c['geoms']) == {'diagnostic_cube_geom', 'diagnostic_table'}
            and c['normal_force_n'] > .01 for c in last['contacts']),
        'final_closure': last['gripper_closure'],
    }
    (directory/'retention_audit.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    progress = json.loads((args.root/'campaign/progress.json').read_text())
    rows = []
    for episode_id, result in progress['episodes'].items():
        row = dict(result)
        replay = args.root/f'replay-episode{int(episode_id.split("-")[-1])}'
        audit_file = replay/'retention_audit.json'
        if (replay/'replay_result.json').exists():
            audit = json.loads(audit_file.read_text()) if audit_file.exists() else replay_metrics(replay, episode_id)
            row['audit'] = audit
            row['audited_native_success'] = bool(result['success'] and
                audit['residual_difference_max_m'] == 0 and audit['longest_qualifying_hold_s'] >= .5)
            row['terminal_success'] = bool(row['audited_native_success'] and
                                           audit['terminal_qualifying_hold_s'] >= .5)
        else:
            row['audited_native_success'] = row['terminal_success'] = None
        rows.append(row)
    summary = {'actor_access': False, 'model': 'gpt-6-astra', 'effort': 'xhigh',
        'completed_records': len(rows), 'native_successes': progress['successes'],
        'physical_attempts': sum(r['actions'] > 0 for r in rows),
        'infrastructure_only_records': sum(r['actions'] == 0 and r['error'] is not None for r in rows),
        'audited_native_successes': sum(r['audited_native_success'] is True for r in rows),
        'terminal_successes': sum(r['terminal_success'] is True for r in rows),
        'required_native_successes': progress['required_successes'],
        'scope': 'Self-learning, independently reset fixed scene; not held-out generalization or real-time evaluation.',
        'episodes': rows}
    (args.root/'audit_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != 'episodes'}))


if __name__ == '__main__':
    main()
