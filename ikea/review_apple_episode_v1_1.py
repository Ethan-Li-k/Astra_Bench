"""Independent host-only audit; consumes sealed evidence without simulation or actor access."""
import argparse
import datetime
import json
import math
from pathlib import Path
import subprocess
from review_door_episode import read, rows, sha, ROOT


def physical_audit(samples, initial_center, initial_bottom, initial_time):
    if not samples:
        raise ValueError('No physical evidence')
    since = None
    longest = 0.
    previous = initial_time
    continuous = consistent = standing = True
    opposed_ticks = 0
    for row in samples:
        t = row['sim_s']
        continuous &= abs(t - previous - .02) < 1e-6
        previous = t
        lift = row['apple_center'][2] - initial_center[2]
        bottom_rise = row['apple_bottom'] - initial_bottom
        stable = row['base_z'] > .55 and row['tilt_rad'] < math.radians(35) and row['stable']
        standing &= stable
        fingers = {'left': set(), 'right': set()}
        for contact in row['contacts']:
            if contact['normal_force_n'] <= .01:
                continue
            for side in fingers:
                for finger in ('thumb', 'index', 'middle'):
                    if contact['other_body'].startswith(f'{side}_hand_{finger}_'):
                        fingers[side].add(finger)
        opposition = any('thumb' in names and bool(names & {'index', 'middle'}) for names in fingers.values())
        opposed_ticks += int(opposition)
        consistent &= abs(lift - row['lift_m']) < 1e-7 and abs(bottom_rise - row['bottom_rise_m']) < 1e-7
        consistent &= opposition == row['loaded_opposition']
        consistent &= all(math.isfinite(x) for x in [t, lift, bottom_rise, row['base_z'], row['tilt_rad']])
        qualified = lift >= .08 and bottom_rise >= .04 and stable and opposition and not row['external_support']
        if qualified:
            if since is None:
                since = t
            longest = max(longest, t - since)
        else:
            since = None
    dwell = previous - since if since is not None else 0.
    checks = dict(continuous_50hz=continuous, measurement_consistency=consistent,
                  stable_throughout=standing, terminal_lift_at_least_8cm=lift >= .08,
                  terminal_bottom_rise_at_least_4cm=bottom_rise >= .04,
                  terminal_loaded_finger_opposition=opposition,
                  no_terminal_external_support=not samples[-1]['external_support'],
                  terminal_qualified_hold_at_least_1s=dwell >= 1.)
    return dict(passed=all(checks.values()), checks=checks, ticks=len(samples),
                opposed_contact_ticks=opposed_ticks, final_lift_m=lift,
                final_bottom_rise_m=bottom_rise, longest_hold_s=longest,
                terminal_hold_s=dwell, min_base_z_m=min(x['base_z'] for x in samples),
                max_tilt_deg=math.degrees(max(x['tilt_rad'] for x in samples)))


def review(ep):
    ep = ep.resolve()
    if ep.parent != ROOT / 'campaign' or not ep.name.startswith('apple-'):
        raise ValueError('IKEA apple campaign required')
    if not (ep / 'result.json').exists():
        raise ValueError('No sealed result; never audit an in-flight episode as complete')
    result, provenance, reset, summary, terms = [read(ep / name) for name in
        ('result.json', 'provenance.json', 'reset-provenance.json', 'host-audit/summary.json', 'batch-terms.json')]
    samples = rows(ep / 'host-audit/audit.jsonl')
    physical = physical_audit(samples, summary['initial_center'], summary['initial_bottom'], reset['sim_s'])
    trace = rows(ep / 'video/robot_trace.jsonl')
    history = rows(ep / 'rollout/history.jsonl')
    commands = [e['command_id'] for row in history if row['tool'] == 'scalebfm_act' for e in row['execution']]
    trace_commands = {x['status']['command_id'] for x in trace if x['status'].get('command_id')}
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=nb_frames,r_frame_rate,duration,width,height', '-of', 'json',
                            str(ep / 'video/episode.mp4')], text=True, capture_output=True, check=True)
    video = json.loads(probe.stdout)['streams'][0]
    receipts = [read(p) for p in sorted((ep / 'api-calls').glob('*/receipt.json'), key=lambda p: int(p.parent.name))]
    final_path = ep / 'api-calls' / f"{result['api_calls']:02d}" / 'public_output.json'
    final_output = read(final_path) if receipts and final_path.exists() else []
    calls = [x for x in final_output if x['type'] == 'function_call']
    runtime = Path(provenance['runtime_manifest'])
    snapshot_root = ep / 'host-source-snapshot'
    snapshot = read(snapshot_root / 'manifest.json')
    memory = ep.parent / 'apple-api-memory'
    revisions = rows(memory / 'experience.jsonl') if (memory / 'experience.jsonl').exists() else []
    revision = next((x for x in reversed(revisions) if x['episode_id'] == ep.name), None)
    revision_valid = bool(revision and sha(memory / 'versions' / f"{revision['version']:04d}.md") == revision['skill_sha256'])
    checks = dict(
        independent_reset=reset['independent_physical_reset'] is True,
        declared_backend=reset['backend'] == 'MuJoCo' and reset['original_usd'] is False and reset['variant'] == 'source-aligned-apple-convex-0.18kg-v1',
        model_effort=provenance['model'] == 'gpt-6-astra' and provenance['effort'] == 'xhigh',
        controller_model38000=reset['model_38000_sha256'] == 'd87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa',
        named_joint_mapping=len(reset['joint_mapping']) == len({x['name'] for x in reset['joint_mapping']}) == 29,
        source_aligned_scene_hash=sha(ROOT / 'scenes/usd-aligned-door-west-no-latch-v3/scene.xml') == reset['scene_sha256'] == provenance['scene_sha256'] == terms['scene_sha256'],
        skill_hash=sha(ep / 'SKILL.md') == terms['skill_sha256'],
        frozen_runtime_hashes=all(sha(runtime.parent / p) == h for p, h in read(runtime).items()),
        adapter_snapshot_hashes=all(sha(snapshot_root / Path(p).name) == h for p, h in snapshot['files'].items()),
        registered_entrypoint=sha(snapshot_root / 'run_api_policy.py') == terms['entrypoint_sha256'],
        one_reset_in_history=sum(x['tool'] == 'loco_start' for x in history) == 1,
        unique_actions=len(commands) == len(set(commands)) == result['actions'] and bool(commands),
        trace_commands_match=trace_commands == set(commands),
        video_trace_continuity=len(trace) == len(samples) + 1 and all(abs(y['sim_s'] - x['sim_s'] - .02) < 1e-6 for x, y in zip(trace, trace[1:])),
        video_trace_end=abs(trace[0]['sim_s'] - reset['sim_s']) < 1e-6 and abs(trace[-1]['sim_s'] - samples[-1]['sim_s']) < 1e-6,
        result_sim_time=abs(trace[-1]['sim_s'] - reset['sim_s'] - result['sim_s']) < 1e-6,
        encoded_frames=int(video['nb_frames']) == (len(trace) + 1) // 2 and video['r_frame_rate'] == '25/1',
        encoded_duration=abs(float(video['duration']) - int(video['nb_frames']) / 25) < .001,
        complete_model_calls=len(receipts) == result['api_calls'] and all(x['state'] == 'completed' and x['returned_model'] == 'gpt-6-astra' and x['returned_reasoning']['effort'] == 'xhigh' and x['http_status'] == 200 for x in receipts),
        sequential_api_ids=[x['call_index'] for x in receipts] == list(range(1, len(receipts) + 1)),
        complete_conclusion=len(calls) == 1 and calls[0]['name'] == 'conclude',
        terminal_success=result['outcome'] == 'success' and result['stop_reason'] == 'native_success' and result['error'] is None,
        skill_updated=result['skill_updated'] is True and revision_valid,
        no_human_task_feedback=not provenance['human_feedback_used'] and not provenance['human_demonstration_used'],
        physics=physical['passed'])
    evidence = ['result.json', 'provenance.json', 'reset-provenance.json', 'SKILL.md', 'batch-terms.json',
                'host-audit/audit.jsonl', 'host-audit/summary.json', 'video/robot_trace.jsonl', 'video/episode.mp4',
                'rollout/history.jsonl', 'rollout/skill_selection.jsonl', 'host-source-snapshot/manifest.json']
    return dict(audited_task_success=all(checks.values()), actor_access=False, episode=ep.name,
                task='IKEA original tabletop apple lift and retained grasp, derived MuJoCo physics',
                backend='MuJoCo', original_usd=False, reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                terminal_kind=result['terminal_kind'], checks=checks, rejected_checks=[k for k, v in checks.items() if not v],
                physical=physical, video=video, skill_version=revision['version'] if revision else None,
                evidence_sha256={p: sha(ep / p) for p in evidence},
                limitations=['50Hz recorded telemetry, not continuous-time proof.',
                             'Convex collision and assumed .18kg mass differ from source SDF and unspecified mass.',
                             'This lift does not establish carrying or refrigerator placement.'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode', type=Path)
    args = p.parse_args()
    report = review(args.episode)
    with (args.episode / 'independent-review.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('audited_task_success', 'episode', 'rejected_checks', 'physical')}))
