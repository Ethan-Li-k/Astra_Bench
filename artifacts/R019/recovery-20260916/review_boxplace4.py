"""Independent temporal/provenance review after saved-state geometry audit."""
from pathlib import Path
import json, math, hashlib, datetime
from tools.coordination.ikea_gate import video_probe

root=Path('/home/galbot/lizekai/RSI');ep=root/'artifacts/R019/boxplace-campaign/episode-0004'
read=lambda n:json.loads((ep/n).read_text())
result,scene,manifest=read('result.json'),read('video/scene_setup.json'),read('video/render_manifest.json')
assert result['success'] and result['skill_updated'] and not result['error']
assert result['native_outcome']=='success' and result['stop_reason']=='native_success'
assert result['model']=='gpt-6-astra' and result['effort']=='xhigh' and result['account_route']=='authorized_account_2'
assert result['completion_contract']['id']=='acquired-lift-then-released-container-support-v1'
assert read('account_route_verified.json')['codex_home'].endswith('/RSI/codex-account-2/home')
turns=[f'turn_{i:03d}.json' for i in range(1,result['codex_turns']+1)]
assert turns and all(read(t)['status']=='completed' and not read(t).get('error') for t in turns)
reset=scene['reset_provenance'];assert reset['method']=='fresh_environment_reset' and reset['seed']==4
for p in ep.parent.glob('episode-*/video/scene_setup.json'):
    if p.parent.parent==ep:continue
    prior=json.loads(p.read_text()).get('reset_provenance',{})
    assert prior.get('reset_id')!=reset['reset_id'] and prior.get('launch')!=reset['launch']
rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
assert rows[0]['host_render_state']['qpos_by_joint']==manifest['initial_render_state']['qpos_by_joint']
initial_z=rows[0]['host_render_state']['qpos_by_joint']['cracker_box_joint'][2]
acquired=False;lift_since=release_since=gap_since=None;first_acquired=None
max_lift=0.;min_height=math.inf;max_tilt=0.;commands=set();positive_opposed=0;qualified=False
for i,row in enumerate(rows):
    t=row['sim_s'];state=row['host_render_state'];joints=state['qpos_by_joint'];base=joints['floating_base_joint']
    assert all(math.isfinite(v) for values in joints.values() for v in values)
    min_height=min(min_height,base[2]);max_tilt=max(max_tilt,math.degrees(math.acos(max(-1,min(1,1-2*(base[4]**2+base[5]**2))))))
    if row['status'].get('command_id'):commands.add(row['status']['command_id'])
    if not i:continue  # Recording begins just before evaluator attachment.
    assert abs(t-rows[i-1]['sim_s']-.02)<1e-7
    gate=state['placement_completion_host_only'];s=gate['sample'];assert abs(s['time']-t)<1e-7
    assert abs(s['rise_m']-(joints['cracker_box_joint'][2]-initial_z))<1e-7
    max_lift=max(max_lift,s['rise_m'])
    names={c['robot_body'] for c in state['external_robot_contacts_host_only'] if c['other_body']=='cracker_box' and c['normal_force_n']>.01}
    if s['grasped']:
        assert any(any(n.startswith(side+'_hand_thumb_') for n in names) and any(n.startswith((side+'_hand_index_',side+'_hand_middle_')) for n in names) for side in ['left','right'])
        positive_opposed+=1
    lifted=s['grasped'] and s['rise_m']>=.05 and not s['nonhand_support']
    lift_since=(t if lift_since is None else lift_since) if lifted else None
    if lift_since is not None and t-lift_since>=.5:
        acquired=True
        if first_acquired is None:first_acquired=t
    placed=s['native_success'] and s['container_contact'] and not s['robot_contact'] and not s['other_support']
    if acquired and (s['other_support'] or (s['nonhand_support'] and not s['container_contact'])):acquired=False
    if acquired and not s['grasped'] and not placed:
        gap_since=t if gap_since is None else gap_since
        if s['other_support'] or t-gap_since>.3:acquired=False
    else:gap_since=None
    release_since=(t if release_since is None else release_since) if acquired and placed else None
    if release_since is not None and t-release_since>=1:qualified=True
    assert gate['acquired']==acquired
    if gate['outcome']=='success':assert qualified
assert qualified and acquired and rows[-1]['native_outcome']=='success'
assert abs(rows[-1]['sim_s']-rows[0]['sim_s']-result['sim_s'])<1e-6
assert min_height>.55 and max_tilt<25
history=[json.loads(s) for s in (ep/'rollout/history.jsonl').read_text().splitlines()]
actions=[e['command_id'] for r in history if r['tool']=='scalebfm_act' for e in r['execution']]
assert len(actions)==len(set(actions))==result['actions']==51 and set(actions)==commands
geometry=json.loads((root/'artifacts/R019/recovery-20260916/boxplace4-geometry/result.json').read_text())
assert geometry['trace_sha256']==hashlib.sha256((ep/'video/robot_trace.jsonl').read_bytes()).hexdigest()
assert geometry['samples'][-1]['box_com_xy_inside_basket_convex_footprint']
assert all(c['other_body']=='brasket' for c in geometry['samples'][-1]['geometry_contacts_only'])
video=video_probe(ep/'video/episode.mp4');frames=(len(rows)+1)//2
assert int(video['nb_frames'])==frames and video['r_frame_rate']=='25/1'
assert abs(float(video['duration'])-frames/25)<.041
rev=next(x for x in reversed([json.loads(s) for s in (ep.parent/'memory/experience.jsonl').read_text().splitlines()]) if x['episode_id']==ep.name)
assert hashlib.sha256((ep.parent/'memory/versions'/f"{rev['version']:04d}.md").read_bytes()).hexdigest()==rev['skill_sha256']
assert hashlib.sha256((ep/'SKILL.md').read_bytes()).hexdigest()==result['starting_skill_sha256']
evidence=['result.json',*turns,'video/scene_setup.json','video/robot_trace.jsonl','video/episode.mp4','video/render_manifest.json','account_route_verified.json','rollout/history.jsonl','rollout/skill_selection.jsonl','policy_instruction_budget.json']
review={'actor_access':False,'audited_task_success':True,'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'task':'simple/G1WholebodyBendPickAndPlaceTeleop-v0','completion_contract':result['completion_contract'],
    'backend':'SIMPLE/MuJoCo checkpoint PD; paused during reasoning, not RTC',
    'independent_reset_verified':True,'reset':reset,'full_turn_and_skill_update':True,'single_action_writer':True,'no_replay_or_diagnostic_initial_state':True,
    'temporal_gate_recomputed_from_recorded_samples':True,'loaded_opposing_finger_samples':positive_opposed,
    'maximum_box_origin_rise_m':max_lift,'acquired_at_sim_s':first_acquired-rows[0]['sim_s'],
    'final_released_container_support_span_s':rows[-1]['sim_s']-release_since,
    'min_base_height_m':min_height,'max_base_tilt_deg':max_tilt,'actions':51,'sim_s':result['sim_s'],'video':video,
    'geometry_audit':'artifacts/R019/recovery-20260916/boxplace4-geometry/result.json',
    'visual_review':'Final public stereo left image0051 inspected: open hand and box positioned within the basket outline, supported in/on basket. Original native criterion alone was not used.',
    'limitations':'Hand opened but no separate terminal withdrawal action; original force samples and independent geometry show no robot support at final state. Box protrudes above rim; full interior-volume containment is not asserted. Single reset, no walking with the box, not the unchanged native completion benchmark.',
    'human_feedback_used':False,'human_demonstration_used':False,'unmodified_native_benchmark':False,
    'skill_version':rev['version'],'skill_sha256':rev['skill_sha256'],'instruction_budget':rev['instruction_budget'],
    'evidence_sha256':{n:hashlib.sha256((ep/n).read_bytes()).hexdigest() for n in evidence}}
path=ep/'success_review.json';assert not path.exists();path.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({k:v for k,v in review.items() if k not in ('reset','evidence_sha256')}))
