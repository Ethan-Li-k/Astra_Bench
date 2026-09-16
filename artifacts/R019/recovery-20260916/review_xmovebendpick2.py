"""Supervisor-only readback audit; no physics or actor input."""
import datetime, hashlib, json, subprocess
from collections import Counter
from pathlib import Path
from tools.audit_simple_campaigns import turn_completeness

root = Path('/home/galbot/lizekai/RSI')
ep = root/'artifacts/R019/xmovebendpick-campaign/episode-0002'
result = json.loads((ep/'result.json').read_text())
complete, integrity = turn_completeness(ep, result)
assert complete and result['skill_updated'] and not result['error']
assert result['stop_reason'] == 'episode_step_budget' and not result['success']
rows = [json.loads(x) for x in (ep/'rollout/history.jsonl').read_text().splitlines()]
acts = [x for x in rows if x['tool'] == 'scalebfm_act']
assert len(acts) == result['actions'] == 58
trace_count = 0
max_closure = 0
for line in (ep/'video/robot_trace.jsonl').open():
    row = json.loads(line)
    if trace_count == 0: first = row
    last = row
    max_closure = max(max_closure, *row['gripper_command'].values())
    trace_count += 1
assert abs(max_closure-.2)<1e-9
video = json.loads(subprocess.check_output([
    'ffprobe','-v','error','-select_streams','v:0','-show_entries',
    'stream=duration,nb_frames,r_frame_rate','-of','json',str(ep/'video/episode.mp4')]))['streams'][0]
assert int(video['nb_frames']) > 0 and abs(float(video['duration'])-result['sim_s']) < .1
revision = ep.parent/'memory/versions/0002.md'
updates = []
for path in sorted((ep/'agent/rpc_calls').glob('*_request.json')):
    value = json.loads(path.read_text())
    if value.get('tool') == 'skill_update':
        reply = path.with_name(path.name.replace('_request','_result'))
        updates.append(dict(request=str(path.relative_to(root)), result=str(reply.relative_to(root))))
review = dict(
    actor_access=False, reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    audited_task_success=False, termination_class='budget_truncation',
    why='Low-table approach and free-lane wrist adjustments progressed, but shallow upper-edge enclosure048/049 displaced the box under closure0.10/0.20. Open re-entry053 tipped it again; no retained pickup before physical budget. Actual transient attitude/position differed from rigid-hand clearance predictions.',
    evidence=['result.json','turn_001.json','rollout/history.jsonl','rollout/policy_stall.jsonl',
              'rollout/episode/observations/0049/observation.json',
              'rollout/episode/observations/0058/observation.json','video/episode.mp4','video/robot_trace.jsonl'],
    visual_review='Original0049 and0058 left images inspected: box at tabletop, partly occluded at shallow closure; final view shows box independently supported by table and open displaced hand. No retained lift.',
    excluded_hypotheses=[
        'No slow-inference cutoff, quota error, premature policy termination or runtime safety stop: full terminal and revision completed.',
        'Unlike episode1, closure0.10/0.20 was tested; visible displacement and shallow opposition do not isolate grip friction as the cause.',
        'Not an entirely immobile approach: measured ankle forward displacement exists, but whole-foot clearance and general gait are not established.',
        'One endpoint target_reached is insufficient to establish transient clearance or box co-motion.'
    ],
    unresolved=['Controller active-set effects versus changed stance/contact remain confounded.',
                'Perception uncertainty, whole-hand sweep and reachable wrist attitude need further separation.'],
    next_change='Fresh reset3 pins completed actor v2. Review recent measured-table achieved-attitude acquisition as a conditional geometry/verification candidate; establish current low-table reachable stance and opposition depth exceeding localization uncertainty before closure. Adapt actual posture/whole-hand sweep; no copied coordinates/closure, hot injection or single-factor causality. New robot-root observation is separately versioned.',
    actions=result['actions'], sim_s=result['sim_s'], budget_s=240,
    budget_boundary_note='Host physical step budget recognized after the last blocking action; recorded elapsed241.86s, not silently rounded to240s.',
    full_turn_and_skill_update=complete, turn_record_integrity=integrity,
    action_status_counts=dict(Counter(e['status'] for a in acts for e in a['execution'])),
    robot_trace_samples=trace_count, maximum_commanded_closure=max_closure,
    measured_forward_ankle_displacement_m={name:last['measured_four_point_position_world_m'][index][0]-first['measured_four_point_position_world_m'][index][0]
                                          for name,index in [('left',2),('right',3)]},
    video=video, skill_version=2, skill_sha256=hashlib.sha256(revision.read_bytes()).hexdigest(),
    skill_update_receipts=updates, human_feedback_used=False, human_demonstration_used=False,
    counts_toward_three_comparable_autonomous_failures=False,
    comparable_failure_exclusion='Physical-budget termination is not a completed task failure for human-help gating.',
    shared_core_promotion=False)
target=ep/'failure_review.json'
assert not target.exists()
target.write_text(json.dumps(review,indent=2)+'\n')
(ep/'public-progress.json').write_text(json.dumps(dict(state='completed',updated_utc=review['reviewed_utc'],
    owner='SIMPLE supervisor',snapshot_not_heartbeat=True,current_problem='Complete physical budget; shallow closure displaced box, no retained grasp',
    result_classification='budget_truncation',next_step='Reviewed v2; next reset tests current achieved-attitude and uncertainty-aware opposition with conditional public source'),indent=2)+'\n')
print(json.dumps(review,indent=2))
