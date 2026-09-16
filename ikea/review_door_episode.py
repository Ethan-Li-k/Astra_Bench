"""Read-only, host-only audit of a sealed IKEA API episode; never actor input."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def physical_audit(samples, initial_time):
    if not samples:
        raise ValueError('No physical audit samples')
    contact_seen = False
    since = None
    longest = 0.
    previous_time, previous_angle = initial_time, 0.
    contact_movement = 0.
    times_valid = True
    all_stable = True
    stability_consistent = True
    for row in samples:
        t, angle = row['sim_s'], row['door_open_rad']
        if not all(math.isfinite(row[k]) for k in ('sim_s', 'door_open_rad', 'base_z', 'tilt_rad')):
            raise ValueError('Nonfinite physical evidence')
        times_valid &= abs(t - previous_time - .02) < 1e-6
        stable = row['base_z'] > .55 and row['tilt_rad'] < math.radians(35)
        # A backend safety reason can additionally set stable=false.
        stability_consistent &= not row['stable'] or stable
        stable &= bool(row['stable'])
        all_stable &= stable
        if row['hand_contact']:
            contact_seen = True
            contact_movement += max(0., angle - previous_angle)
        if contact_seen and angle >= math.pi / 6 and stable:
            if since is None:
                since = t
            longest = max(longest, t - since)
        else:
            since = None
        previous_time, previous_angle = t, angle
    final_dwell = previous_time - since if since is not None else 0.
    checks = dict(continuous_50hz_audit=times_valid,
                  stable_throughout=all_stable,
                  stability_fields_consistent=stability_consistent,
                  hand_contact_observed=contact_seen,
                  positive_door_motion_during_hand_contact=contact_movement > 1e-5,
                  terminal_opening_at_least_30deg=previous_angle >= math.pi / 6,
                  terminal_hold_at_least_1s=final_dwell >= 1.)
    return dict(checks=checks, passed=all(checks.values()), ticks=len(samples),
                contact_ticks=sum(bool(x['hand_contact']) for x in samples),
                contact_positive_motion_deg=math.degrees(contact_movement),
                max_open_deg=math.degrees(max(x['door_open_rad'] for x in samples)),
                final_open_deg=math.degrees(previous_angle),
                longest_qualified_hold_s=longest, terminal_qualified_hold_s=final_dwell,
                min_base_z_m=min(x['base_z'] for x in samples),
                max_tilt_deg=math.degrees(max(x['tilt_rad'] for x in samples)))


def review(episode):
    ep = episode.resolve()
    if ep.parent != ROOT / 'campaign':
        raise ValueError('Only IKEA campaign episodes may be reviewed')
    result_path = ep / 'result.json'
    if not result_path.exists():
        raise ValueError('No sealed result; preserve the running or incomplete episode')
    result, provenance, reset = [read(ep / name) for name in
                                ('result.json', 'provenance.json', 'reset-provenance.json')]
    samples = rows(ep / 'host-audit/audit.jsonl')
    physical = physical_audit(samples, reset['sim_s'])
    trace = rows(ep / 'video/robot_trace.jsonl')
    history = rows(ep / 'rollout/history.jsonl')
    commands = [e['command_id'] for row in history if row['tool'] == 'scalebfm_act'
                for e in row['execution']]
    trace_commands = {x['status']['command_id'] for x in trace if x['status'].get('command_id')}
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-show_entries', 'stream=nb_frames,r_frame_rate,duration,width,height',
                            '-of', 'json', str(ep / 'video/episode.mp4')],
                           text=True, capture_output=True, check=True)
    video = json.loads(probe.stdout)['streams'][0]
    receipts = [read(path) for path in sorted((ep / 'api-calls').glob('*/receipt.json'), key=lambda p: int(p.parent.name))]
    final_output = read(ep / 'api-calls' / f"{result['api_calls']:02d}" / 'public_output.json') if receipts else []
    final_calls = [x for x in final_output if x['type'] == 'function_call']
    registration = read(provenance['registration'])
    terms = read(ep / 'batch-terms.json')
    frozen = Path(provenance['runtime_manifest'])
    frozen_hashes = read(frozen)
    memory = ep.parent / 'api-memory'
    revisions = rows(memory / 'experience.jsonl') if (memory / 'experience.jsonl').exists() else []
    revision = next((x for x in reversed(revisions) if x['episode_id'] == ep.name), None)
    revision_valid = bool(revision and sha(memory / 'versions' / f"{revision['version']:04d}.md") == revision['skill_sha256'])
    source_snapshot = ep / 'host-source-snapshot'
    snapshot = read(source_snapshot / 'manifest.json')
    # Snapshot format is retained verbatim in evidence; entrypoint hash is independently pinned by registration terms.
    checks = dict(
        independent_closed_reset=reset['independent_physical_reset'] is True and abs(reset['door_angle_after_settle']) < 1e-6,
        correct_derived_backend=reset['backend'] == 'MuJoCo' and reset['original_usd'] is False,
        model_effort=provenance['model'] == 'gpt-6-astra' and provenance['effort'] == 'xhigh',
        controller_model38000=reset['model_38000_sha256'] == 'd87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa',
        named_29_joint_mapping=len(reset['joint_mapping']) == len({x['name'] for x in reset['joint_mapping']}) == 29,
        scene_hash=sha(ROOT / 'scenes/usd-aligned-door-west-no-latch-v3/scene.xml') == reset['scene_sha256'] == provenance['scene_sha256'] == terms['scene_sha256'],
        skill_hash=sha(ep / 'SKILL.md') == terms['skill_sha256'],
        frozen_runtime_hashes=all(sha(frozen.parent / p) == h for p, h in frozen_hashes.items()),
        frozen_entrypoint=sha(source_snapshot / 'run_api_policy.py') == terms['entrypoint_sha256'],
        one_reset_in_history=sum(x['tool'] == 'loco_start' for x in history) == 1,
        unique_action_ids=len(commands) == len(set(commands)) == result['actions'] and bool(commands),
        trace_command_match=trace_commands == set(commands),
        video_trace_continuity=len(trace) == len(samples) + 1 and all(abs(y['sim_s'] - x['sim_s'] - .02) < 1e-6 for x, y in zip(trace, trace[1:])),
        video_trace_end=abs(trace[0]['sim_s'] - reset['sim_s']) < 1e-6 and abs(trace[-1]['sim_s'] - samples[-1]['sim_s']) < 1e-6,
        result_sim_time=abs(trace[-1]['sim_s'] - reset['sim_s'] - result['sim_s']) < 1e-6,
        encoded_frames=int(video['nb_frames']) == (len(trace) + 1) // 2 and video['r_frame_rate'] == '25/1',
        encoded_duration=abs(float(video['duration']) - int(video['nb_frames']) / 25) < .001,
        all_api_calls_completed=len(receipts) == result['api_calls'] and all(x['state'] == 'completed' and x['returned_model'] == 'gpt-6-astra' and x['returned_reasoning']['effort'] == 'xhigh' and x['http_status'] == 200 for x in receipts),
        unique_sequential_api_calls=[x['call_index'] for x in receipts] == list(range(1, len(receipts) + 1)),
        final_model_conclusion=len(final_calls) == 1 and final_calls[0]['name'] == 'conclude',
        terminal_success=result['outcome'] == 'success' and result['stop_reason'] == 'native_success' and result['error'] is None,
        skill_revision=result['skill_updated'] is True and revision_valid,
        no_human_task_feedback=not provenance['human_feedback_used'] and not provenance['human_demonstration_used'],
        physics=physical['passed'])
    evidence = ['result.json', 'provenance.json', 'reset-provenance.json', 'batch-terms.json', 'SKILL.md',
                'length-check.json', 'rollout/history.jsonl', 'rollout/skill_selection.jsonl',
                'host-audit/audit.jsonl', 'host-audit/summary.json', 'video/robot_trace.jsonl',
                'video/episode.mp4', 'host-source-snapshot/manifest.json']
    return dict(audited_task_success=all(checks.values()), actor_access=False,
                task='IKEA Door_West derived no-latch push-open', backend='MuJoCo', original_usd=False,
                reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                episode=ep.name, terminal_kind=result['terminal_kind'], checks=checks,
                rejected_checks=[k for k, v in checks.items() if not v], physical=physical,
                video=video, registration=registration, source_snapshot=snapshot,
                skill_revision=revision['version'] if revision else None,
                evidence_sha256={p: sha(ep / p) for p in evidence},
                limitation='Host audit is independent of the native success flag, but uses recorded simulator telemetry; not an Isaac or unlocking result.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode', type=Path)
    args = parser.parse_args()
    report = review(args.episode)
    path = args.episode / 'independent-review.json'
    with path.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('audited_task_success', 'episode', 'rejected_checks', 'physical')}, ensure_ascii=False))
