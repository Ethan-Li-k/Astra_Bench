"""Independent original-episode audit; saved-state reconstruction has no task credit."""
from pathlib import Path
import datetime,json,hashlib,math
from tools.audit_simple_campaigns import turn_completeness
from tools.coordination.ikea_gate import video_probe
r=Path('/home/galbot/lizekai/RSI');ep=r/'artifacts/R019/xmovepicksim-campaign/episode-0001'
read=lambda n:json.loads((ep/n).read_text())
result=read('result.json');scene=read('video/scene_setup.json');manifest=read('video/render_manifest.json')
assert result['success'] and result['skill_updated'] and not result['error']
assert result['model']=='gpt-6-astra' and result['effort']=='xhigh' and result['account_route']=='authorized_account_2'
assert read('account_route_verified.json')['codex_home'].endswith('/RSI/codex-account-2/home')
full,integrity=turn_completeness(ep,result);assert full,integrity
reset=scene['reset_provenance'];assert reset['method']=='fresh_environment_reset' and reset['seed']==1
assert scene['object_state_and_forces_preserved'] and not scene['object_identifier_changes']
rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
assert rows[0]['host_render_state']['qpos_by_joint']==manifest['initial_render_state']['qpos_by_joint']
gp=r/'artifacts/R019/recovery-20260916/xmovepicksim1-geometry/result.json';g=json.loads(gp.read_text())
assert g['trace_sha256']==hashlib.sha256((ep/'video/robot_trace.jsonl').read_bytes()).hexdigest()
assert g['reset_hash']==reset['post_settle_qpos_qvel_sha256']
commands=set();heights=[];tilts=[];flag_mismatch=[]
for i,row in enumerate(rows):
 state=row['host_render_state'];j=state['qpos_by_joint'];base=j['floating_base_joint']
 assert all(math.isfinite(v) for values in j.values() for v in values)
 if i:assert abs(row['sim_s']-rows[i-1]['sim_s']-.02)<1e-7
 if row['status'].get('command_id'):commands.add(row['status']['command_id'])
 heights.append(base[2]);tilts.append(math.degrees(math.acos(max(-1,min(1,1-2*(base[4]**2+base[5]**2))))))
 eligible=j['cracker_box_joint'][2]-g['native_reference_height_m']>=.03
 if eligible!=state['native_task_success']:flag_mismatch.append(i)
assert not flag_mismatch and rows[-1]['host_render_state']['native_task_success']
assert rows[0]['native_outcome']=='in_progress' and rows[-1]['native_outcome']=='success'
assert min(heights)>.55 and max(tilts)<25
assert abs(rows[-1]['sim_s']-rows[0]['sim_s']-result['sim_s'])<1e-6
assert g['samples'][-1]['retained'] and g['samples'][-1]['bottom_rise_m']>.03
assert g['longest_opposed_unsupported_full_box_clearance_s']>1
hold=g['command_stats']['retain_037:0']
assert hold['samples']==hold['retained_samples'] and hold['last_sim_s']-hold['first_sim_s']>=1.49
assert hold['min_bottom_rise_m']>.02
history=[json.loads(s) for s in (ep/'rollout/history.jsonl').read_text().splitlines()]
actions=[x['command_id'] for row in history if row['tool']=='scalebfm_act' for x in row['execution']]
assert len(actions)==len(set(actions))==result['actions']==38 and set(actions)==commands
video=video_probe(ep/'video/episode.mp4');frames=(len(rows)+1)//2
assert int(video['nb_frames'])==frames and video['r_frame_rate']=='25/1' and abs(float(video['duration'])-frames/25)<.041
revision=next(x for x in reversed([json.loads(s) for s in (ep.parent/'memory/experience.jsonl').read_text().splitlines()]) if x['episode_id']==ep.name)
assert hashlib.sha256((ep.parent/'memory/versions'/f"{revision['version']:04d}.md").read_bytes()).hexdigest()==revision['skill_sha256']
assert hashlib.sha256((ep/'SKILL.md').read_bytes()).hexdigest()==result['starting_skill_sha256']
assert not result['human_feedback_used'] and not result['human_demonstration_used']
evidence=['result.json',*[f'turn_{i:03d}.json' for i in range(1,result['codex_turns']+1)],'video/scene_setup.json','video/render_manifest.json','video/robot_trace.jsonl','video/episode.mp4','account_route_verified.json','rollout/history.jsonl','rollout/skill_selection.jsonl','policy_instruction_budget.json']
review=dict(actor_access=False,audited_task_success=True,reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 task=scene['env_id'],completion_contract='native_simple_height_criterion_with_independent_retained_grasp_audit',
 backend='SIMPLE/MuJoCo checkpoint standing reset and PD; inference pauses physics, not RTC',
 reset=reset,independent_reset_verified=True,single_action_writer=True,full_turn_and_skill_update=True,turn_record_integrity=integrity,
 no_replay_or_diagnostic_initial_state=True,actions=38,sim_s=result['sim_s'],video=video,
 native_success_flags_recomputed_for_all_saved_samples=True,native_success_flag_mismatches=flag_mismatch,
 native_threshold_height_m=.03,final_origin_rise_from_native_reference_m=g['samples'][-1]['origin_rise_m'],
 final_full_box_bottom_rise_from_settled_m=g['samples'][-1]['bottom_rise_m'],
 longest_loaded_opposed_unsupported_clearance_s=g['longest_opposed_unsupported_full_box_clearance_s'],
 separate_prethreshold_hold=hold,final_support_bodies=[c['other_body'] for c in g['final_contacts']],
 saved_state_geometry_audit=str(gp),min_base_height_m=min(heights),max_base_tilt_deg=max(tilts),
 reward_numeric_reconstruction=dict(exact=False,mismatch_count=len(g['reward_mismatches']),
   maximum_absolute_difference=max(abs(x['expected']-x['recorded']) for x in g['reward_mismatches']),
   explanation='Original native engine reads mjData body.xpos after mj_step, whereas reconstructed geometry calls mj_forward on saved post-integration qpos. This is a sampling-stage difference inferred from local source; final physics-substep qvel/xpos were not retained, so exact reward values cannot be reconstructed. The attempted exact check failed and is preserved. All success flags independently agree; task audit relies additionally on geometry and original loaded contacts, not equality of reward values.'),
 visual_review='Original obs0035/0037 and final0038 stereo inspected; box remains between opposing fingers with visible final clearance above table. Geometry excludes table/distractor support and pure tipping.',
 failed_probes='Closure.25 lift031/hold032 did not show acquisition; .35 with changed actual geometry gave subsequent retained lift. Within one reset, not independent failed attempts.',
 limitations='Separate1.5s retention hold precedes final native height crossing; no additional post-threshold dwell. No loaded walking, placing, fixed-policy reliability or cross-reset generalization claim. Original reward sampling cannot be exactly replayed from saved qpos.',
 human_feedback_used=False,human_demonstration_used=False,skill_version=revision['version'],skill_sha256=revision['skill_sha256'],instruction_budget=revision['instruction_budget'],
 evidence_sha256={n:hashlib.sha256((ep/n).read_bytes()).hexdigest() for n in evidence},geometry_audit_sha256=hashlib.sha256(gp.read_bytes()).hexdigest())
dest=ep/'success_review.json';assert not dest.exists();dest.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({k:v for k,v in review.items() if k not in ['reset','evidence_sha256','reward_numeric_reconstruction']}))
