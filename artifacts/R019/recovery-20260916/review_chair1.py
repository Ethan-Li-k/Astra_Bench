"""One completed episode audit; host-only, no actor or simulation execution."""
from pathlib import Path
import datetime
import hashlib
import json
import math
from tools.coordination.ikea_gate import video_probe
from rsi.simple_environment import create_native_task_backend
import numpy as np

root = Path('/home/galbot/lizekai/RSI')
ep = root/'artifacts/R019/chair-campaign/episode-0001'
read = lambda name: json.loads((ep/name).read_text())
result, scene, manifest = read('result.json'), read('video/scene_setup.json'), read('video/render_manifest.json')
assert result['success'] and result['native_outcome'] == 'success'
assert result['skill_updated'] and not result['error'] and result['stop_reason'] == 'native_success'
assert result['model'] == 'gpt-6-astra' and result['effort'] == 'xhigh'
assert result['account_route'] == 'authorized_account_2'
assert read('account_route_verified.json')['codex_home'].endswith('/RSI/codex-account-2/home')
turn_names = [f'turn_{i:03d}.json' for i in range(1, result['codex_turns']+1)]
assert turn_names and all(read(t)['status'] == 'completed' and not read(t).get('error') for t in turn_names)
reset = scene['reset_provenance']
assert reset['method'] == 'fresh_environment_reset' and reset['seed'] == 1
assert scene['object_state_and_forces_preserved'] and not scene['object_identifier_changes']
for path in ep.parent.glob('episode-*/video/scene_setup.json'):
    if path.parent.parent == ep:
        continue
    prior = json.loads(path.read_text()).get('reset_provenance', {})
    assert reset['reset_id'] != prior.get('reset_id')
    assert reset['launch'] != prior.get('launch')
rows = [json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
assert rows[0]['host_render_state']['qpos_by_joint'] == manifest['initial_render_state']['qpos_by_joint']
assert rows[0]['native_outcome'] == 'in_progress'
commands, contacts = set(), []
# Read native initialization reference in an isolated deterministic diagnostic reset.
# No policy, no old commands and no credit for the diagnostic backend.
backend=create_native_task_backend('simple/G1WholebodyPushOfficeChairTeleop-v0',seed=1)
try:
    assert backend.scene_setup['reset_provenance']['post_settle_qpos_qvel_sha256']==reset['post_settle_qpos_qvel_sha256'], 'Diagnostic reset differs; cannot borrow native reference'
    chair_reference=backend.env.task.chair_init_pos.copy()
    table_position=backend.data.xpos[backend.model.body('table').id].copy()
finally:backend.close()
reward, since, dwell, first_success = 0., None, 0., None
chair_positions=[];chair_tilts=[]
heights, tilts, angles = [], [], []
for i, row in enumerate(rows):
    state = row['host_render_state']; joints = state['qpos_by_joint']
    cq=joints['articulate_floating_base'];chair_positions.append(cq[:3]);chair_tilts.append(math.degrees(math.acos(max(-1.,min(1.,1-2*(cq[4]**2+cq[5]**2))))));angle=cq[0]-chair_reference[0];angles.append(angle)
    q = joints['floating_base_joint']; heights.append(q[2])
    assert all(math.isfinite(v) for values in joints.values() for v in values)
    assert abs(sum(v*v for v in q[3:])-1) < 1e-4
    tilts.append(math.degrees(math.acos(max(-1., min(1., 1-2*(q[4]**2+q[5]**2))))))
    if i:
        assert abs(row['sim_s']-rows[i-1]['sim_s']-.02) < 1e-7
        # Native Sonic step calls compute_reward, then check_success calls it again.
        expected_return = reward+.06 if abs(angle) > .8 else 0.
        reward = expected_return+.06 if abs(angle) > .8 else 0.
        assert abs(state['native_task_reward']-expected_return) < 1e-7
        assert state['native_task_success'] == (reward >= .9)
    else:
        assert abs(angle) < .02 and not state['native_task_success']
    if abs(angle) > .8:
        since = row['sim_s'] if since is None else since
        dwell = max(dwell, row['sim_s']-since)
    else:
        since = None
    if state['native_task_success'] and first_success is None:
        first_success = row['sim_s']-rows[0]['sim_s']
    if row['status'].get('command_id'):
        commands.add(row['status']['command_id'])
    contacts.extend(c for c in state['external_robot_contacts_host_only'] if c['normal_force_n'] > 0)
assert rows[-1]['native_outcome'] == 'success' and rows[-1]['host_render_state']['native_task_success']
assert abs(rows[-1]['sim_s']-rows[0]['sim_s']-result['sim_s']) < 1e-6
history = [json.loads(s) for s in (ep/'rollout/history.jsonl').read_text().splitlines()]
actions = [e['command_id'] for r in history if r['tool'] == 'scalebfm_act' for e in r['execution']]
assert len(actions) == len(set(actions)) == result['actions'] == len(commands) == 38
assert set(actions) == commands and contacts
assert any('hand' in c['robot_body'] and c['other_body'].startswith('link_') for c in contacts)
assert max(chair_tilts)<5 and max(p[2] for p in chair_positions)-min(p[2] for p in chair_positions)<.03
start_distance=float(np.linalg.norm(np.array(chair_positions[0][:2])-table_position[:2]))
end_distance=float(np.linalg.norm(np.array(chair_positions[-1][:2])-table_position[:2]))
assert end_distance<start_distance-.5 and angles[-1]>.8
assert min(heights) > .55 and max(tilts) < 25
video = video_probe(ep/'video/episode.mp4')
frames = (len(rows)+1)//2
assert int(video['nb_frames']) == frames and video['r_frame_rate'] == '25/1'
assert abs(float(video['duration'])-frames/25) < .041
revision = next(r for r in reversed([json.loads(s) for s in (ep.parent/'memory/experience.jsonl').read_text().splitlines()]) if r['episode_id'] == ep.name)
version = ep.parent/'memory/versions'/f"{revision['version']:04d}.md"
assert hashlib.sha256(version.read_bytes()).hexdigest() == revision['skill_sha256']
assert hashlib.sha256((ep/'SKILL.md').read_bytes()).hexdigest() == result['starting_skill_sha256']
evidence = ['result.json', *turn_names, 'video/robot_trace.jsonl', 'video/episode.mp4',
            'video/scene_setup.json', 'video/render_manifest.json', 'account_route_verified.json',
            'rollout/history.jsonl', 'rollout/skill_selection.jsonl', 'policy_instruction_budget.json']
review = dict(audited_task_success=True, actor_access=False,
    reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    task='simple/G1WholebodyPushOfficeChairTeleop-v0', completion_contract='native_simple_criterion',
    backend='SIMPLE/MuJoCo with checkpoint standing reset and PD; physics paused during inference, not RTC',
    independent_reset_verified=True, reset=reset, full_turn_and_skill_update=True,
    no_replay_or_diagnostic_initial_state=True, single_action_writer=True,
    criteria='Native absolute chair X displacement>0.8m from initialized reference and accumulated reward>=0.9; original double reward calls retained. Additionally verified actual approach toward table, upright chair and standing robot. No added hold criterion.',
    reward_recomputed_for_every_recorded_control_step=True,
    final_chair_x_displacement_m=angles[-1], maximum_absolute_chair_x_displacement_m=max(map(abs,angles)),
    native_chair_reference=chair_reference.tolist(), table_position_host_only=table_position.tolist(),
    chair_table_distance_initial_m=start_distance, chair_table_distance_final_m=end_distance, max_chair_tilt_deg=max(chair_tilts),
    observed_threshold_span_s=dwell, first_native_success_sim_s=first_success,
    min_base_height_m=min(heights), max_base_tilt_deg=max(tilts),
    positive_external_robot_contact_samples=len(contacts),
    min_positive_contact_force_n=min(c['normal_force_n'] for c in contacts),
    max_positive_contact_force_n=max(c['normal_force_n'] for c in contacts),
    video=video, actions=len(actions), sim_s=result['sim_s'],
    visual_review='Final public observation0038 both eyes inspected: upright chair back between robot open hands and fixed table, with clear forward displacement. Public action/lesson records stationary pushes separated by unloaded repositioning, including support slip counterexamples.',
    limitations='Terminal success while open hands remain on chair; no post-release hold. Repositioning included foot slip and poorly tracked yaw; this does not establish general gait or loaded walking. Deterministic diagnostic initialization only supplied native reference/table position; no policy/action replay or additional attempt credit.',
    human_feedback_used=False, human_demonstration_used=False,
    skill_version=revision['version'], skill_sha256=revision['skill_sha256'],
    instruction_budget=revision['instruction_budget'],
    evidence_sha256={n:hashlib.sha256((ep/n).read_bytes()).hexdigest() for n in evidence})
path = ep/'success_review.json'
assert not path.exists(), 'Preserve prior audit'
path.write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps({k:v for k,v in review.items() if k not in ('evidence_sha256','reset')}))
