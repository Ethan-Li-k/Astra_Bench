"""Independent host-only audit; consumes sealed evidence without simulation or actor access."""
import argparse
import datetime
import json
import math
from pathlib import Path
import subprocess
from review_door_episode import read, rows, sha, ROOT


from review_fridge_physics_v2 import physical_audit

def subscription_turn_audit(route,turns,declared_count):
    ids=[t.get('id') for t in turns]
    return dict(model_effort=route.get('model')=='gpt-6-astra' and route.get('effort')=='xhigh',
        second_account_launcher=route.get('launcher')==str(ROOT.parent/'codex-account-2/run.sh'),
        no_inference_deadline=route.get('inference_deadline','missing') is None,
        real_completed_turns=bool(turns) and all(t.get('status')=='completed' for t in turns),
        unique_turns=all(isinstance(i,str) and i for i in ids) and len(ids)==len(set(ids)),
        all_turns_accounted=len(turns)==declared_count,
        policy_thread_recorded=isinstance(route.get('thread'),str) and bool(route['thread']))


def review(ep):
    ep = ep.resolve()
    if ep.parent != ROOT / 'campaign' or ep.name != 'fridge-0001':
        raise ValueError('IKEA refrigerator campaign required')
    if not (ep / 'result.json').exists():
        raise ValueError('No sealed result; never audit an in-flight episode as complete')
    result, provenance, reset, summary = [read(ep / name) for name in
        ('result.json', 'provenance.json', 'reset-provenance.json', 'host-audit/summary.json')]
    samples = rows(ep / 'host-audit/audit.jsonl')
    physical = physical_audit(samples, reset['sim_s'])
    trace = rows(ep / 'video/robot_trace.jsonl')
    history = rows(ep / 'rollout/history.jsonl')
    commands = [e['command_id'] for row in history if row['tool'] == 'scalebfm_act' for e in row['execution']]
    trace_commands = {x['status']['command_id'] for x in trace if x['status'].get('command_id')}
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=nb_frames,r_frame_rate,duration,width,height', '-of', 'json',
                            str(ep / 'video/episode.mp4')], text=True, capture_output=True, check=True)
    video = json.loads(probe.stdout)['streams'][0]
    route=read(ep/'model-route.json')
    turns=[read(p) for p in sorted(ep.glob('turn-*.json'))]
    turn_check=subscription_turn_audit(route,turns,result['complete_model_turns'])
    runtime = Path(provenance['runtime_manifest'])
    snapshot_root = ep / 'host-source-snapshot'
    snapshot = read(snapshot_root / 'manifest.json')
    memory = ep.parent / 'fridge-subscription-memory-v1'
    revisions = rows(memory / 'experience.jsonl') if (memory / 'experience.jsonl').exists() else []
    revision = next((x for x in reversed(revisions) if x['episode_id'] == ep.name), None)
    revision_valid = bool(revision and sha(memory / 'versions' / f"{revision['version']:04d}.md") == revision['skill_sha256'])
    checks = dict(
        independent_reset=reset['independent_physical_reset'] is True,
        declared_backend=reset['backend'] == 'MuJoCo' and reset['original_usd'] is False and reset['variant'] == 'usd-aligned-fridge-hinged-no-gasket-v1',
        model_effort=provenance['model'] == 'gpt-6-astra' and provenance['effort'] == 'xhigh',
        controller_model38000=reset['model_38000_sha256'] == 'd87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa',
        named_joint_mapping=len(reset['joint_mapping']) == len({x['name'] for x in reset['joint_mapping']}) == 29,
        source_aligned_scene_hash=sha(ROOT / 'scenes/usd-aligned-fridge-hinged-no-gasket-v1/scene.xml') == reset['scene_sha256'] == provenance['scene_sha256'],
        skill_hash=sha(ep / 'SKILL.md') == sha(memory/'versions/0000.md') == read(ROOT/'engineering-evidence/subscription-fridge-v1-preflight/result.json')['source_sha256']['skills/fridge-open-v1/SKILL.md'],
        frozen_runtime_hashes=all(sha(runtime.parent / p) == h for p, h in read(runtime).items()),
        adapter_snapshot_hashes=all(sha(snapshot_root / Path(p).name) == h for p, h in snapshot['files'].items()),
        subscription_entrypoint=sha(snapshot_root / 'run_subscription_fridge_v1.py') == provenance['policy_sha256'],
        one_reset_in_history=sum(x['tool'] == 'loco_start' for x in history) == 1,
        unique_actions=len(commands) == len(set(commands)) == result['actions'] and bool(commands),
        trace_commands_match=trace_commands == set(commands),
        video_trace_continuity=len(trace) == len(samples) + 1 and all(abs(y['sim_s'] - x['sim_s'] - .02) < 1e-6 for x, y in zip(trace, trace[1:])),
        video_trace_end=abs(trace[0]['sim_s'] - reset['sim_s']) < 1e-6 and abs(trace[-1]['sim_s'] - samples[-1]['sim_s']) < 1e-6,
        result_sim_time=abs(trace[-1]['sim_s'] - reset['sim_s'] - result['sim_s']) < 1e-6,
        encoded_frames=int(video['nb_frames']) == (len(trace) + 1) // 2 and video['r_frame_rate'] == '25/1',
        encoded_duration=abs(float(video['duration']) - int(video['nb_frames']) / 25) < .001,
        completed_subscription_turns=all(turn_check.values()),
        terminal_success=result['outcome'] == 'success' and result['stop_reason'] == 'native_success' and result['error'] is None,
        skill_updated=result['skill_updated'] is True and revision_valid,
        declared_no_human_feedback=provenance['human_feedback_used'] is False and provenance['human_demonstration_used'] is False
            and provenance['human_feedback_sources']==[],
        closed_reset=len(reset['fridge_angles_after_settle'])==2
            and all(math.isfinite(x) and abs(x)<1e-6 for x in reset['fridge_angles_after_settle'])
            and set(summary['initial_angles_rad'])=={'left','right'}
            and all(abs(x)<1e-6 for x in summary['initial_angles_rad'].values()),
        completion_contract=summary['contract']==provenance['completion_contract']=='ikea-fridge-upper-hand-drive2deg-open45-hold1-stable-v2',
        prerequisite_apple_audited=read(ROOT/'campaign'/provenance['prerequisite_apple_episode']/'independent-review.json')['audited_task_success'] is True,
        physics=physical['passed'])
    evidence = ['result.json', 'provenance.json', 'reset-provenance.json', 'SKILL.md', 'model-route.json',
                'host-audit/audit.jsonl', 'host-audit/summary.json', 'video/robot_trace.jsonl', 'video/episode.mp4',
                'rollout/history.jsonl', 'rollout/skill_selection.jsonl', 'host-source-snapshot/manifest.json']
    return dict(audited_task_success=all(checks.values()), actor_access=False, episode=ep.name,
                task='IKEA original refrigerator upper door geometry, derived no-gasket hinged physics',
                backend='MuJoCo', original_usd=False, human_feedback_used=False, unassisted_direct=True, reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                terminal_kind=result['terminal_kind'], checks=checks, rejected_checks=[k for k, v in checks.items() if not v],
                subscription_turn_checks=turn_check, physical=physical, video=video, skill_version=revision['version'] if revision else None,
                evidence_sha256={p: sha(ep / p) for p in evidence},
                limitations=['50Hz recorded telemetry, not continuous-time proof.',
                             'Derived hinges, assumed4kg leaf masses, friction and collision partitions; no gasket, magnetic seal or latch.',
                             'Source plain slab doors retained; no handle was added. This is not original USD physics or Isaac.',
                             'Opening a door does not establish apple transport, placing or releasing.'])



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode', type=Path)
    args = p.parse_args()
    report = review(args.episode)
    with (args.episode / 'independent-review.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('audited_task_success', 'episode', 'rejected_checks', 'physical')}))
