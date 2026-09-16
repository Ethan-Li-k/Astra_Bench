"""Host-only independent completed apple8 review, no policy or physics execution."""
from pathlib import Path
import datetime,json,hashlib,math
from tools.audit_simple_campaigns import turn_completeness
from tools.coordination.ikea_gate import video_probe
r=Path('/home/galbot/lizekai/RSI');ep=r/'artifacts/R019/apple-campaign/episode-0008'
read=lambda s:json.loads((ep/s).read_text())
result=read('result.json');scene=read('video/scene_setup.json');manifest=read('video/render_manifest.json')
assert result['success'] and result['native_outcome']=='success' and result['skill_updated'] and not result['error']
assert result['stop_reason']=='native_success' and result['model']=='gpt-6-astra' and result['effort']=='xhigh'
assert result['account_route']=='authorized_account_2' and read('account_route_verified.json')['codex_home'].endswith('/RSI/codex-account-2/home')
full,integrity=turn_completeness(ep,result);assert full,integrity
reset=scene['reset_provenance'];assert reset['method']=='fresh_environment_reset' and reset['seed']==8
for other in ep.parent.glob('episode-*/video/scene_setup.json'):
 if other.parent.parent==ep:continue
 prior=json.loads(other.read_text()).get('reset_provenance',{})
 assert prior.get('reset_id')!=reset['reset_id'] and prior.get('launch')!=reset['launch']
assert scene['object_state_and_forces_preserved'] and not scene['object_identifier_changes']
rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
assert rows[0]['host_render_state']['qpos_by_joint']==manifest['initial_render_state']['qpos_by_joint']
heights=[];tilts=[];commands=set();span_start=None;max_loaded_span=0.
for i,row in enumerate(rows):
 q=row['host_render_state']['qpos_by_joint']['floating_base_joint'];heights.append(q[2]);tilts.append(math.degrees(math.acos(max(-1,min(1,1-2*(q[4]**2+q[5]**2))))))
 if i:assert abs(row['sim_s']-rows[i-1]['sim_s']-.02)<1e-7
 if row['status'].get('command_id'):commands.add(row['status']['command_id'])
 state=row['host_render_state'];c=[x['robot_body'] for x in state['external_robot_contacts_host_only'] if x['other_body']=='apple' and x['normal_force_n']>0]
 rise=state['qpos_by_joint']['apple_joint'][2]-rows[0]['host_render_state']['qpos_by_joint']['apple_joint'][2]
 retained=rise>.02 and any('thumb' in n for n in c) and any('middle' in n or 'index' in n for n in c)
 if retained:
  if span_start is None:span_start=row['sim_s']
  max_loaded_span=max(max_loaded_span,row['sim_s']-span_start)
 else:span_start=None
assert rows[0]['native_outcome']=='in_progress' and rows[-1]['native_outcome']=='success'
assert min(heights)>.55 and max(tilts)<25 and max_loaded_span>1
assert abs(rows[-1]['sim_s']-rows[0]['sim_s']-result['sim_s'])<1e-6
history=[json.loads(s) for s in (ep/'rollout/history.jsonl').read_text().splitlines()]
actions=[x['command_id'] for row in history if row['tool']=='scalebfm_act' for x in row['execution']]
assert len(actions)==len(set(actions))==result['actions']==len(commands)==117 and set(actions)==commands
geometry_path=r/'artifacts/R019/recovery-20260916/apple8-geometry/result.json';g=json.loads(geometry_path.read_text())
assert not g['reward_mismatches'] and g['recomputed_control_steps']==len(rows)-1
assert g['terminal_bowl_only_contact'] and g['samples'][-1]['all_apple_xy_inside_bowl_footprint']
assert g['max_apple_origin_rise_m']>.05 and not rows[-1]['host_render_state']['external_robot_contacts_host_only']
assert g['trace_sha256']==hashlib.sha256((ep/'video/robot_trace.jsonl').read_bytes()).hexdigest()
video=video_probe(ep/'video/episode.mp4');frames=(len(rows)+1)//2
assert int(video['nb_frames'])==frames and video['r_frame_rate']=='25/1' and abs(float(video['duration'])-frames/25)<.041
revision=next(x for x in reversed([json.loads(s) for s in (ep.parent/'memory/experience.jsonl').read_text().splitlines()]) if x['episode_id']==ep.name)
version=ep.parent/'memory/versions'/f"{revision['version']:04d}.md";assert hashlib.sha256(version.read_bytes()).hexdigest()==revision['skill_sha256']
assert hashlib.sha256((ep/'SKILL.md').read_bytes()).hexdigest()==result['starting_skill_sha256']
assert result['human_feedback_used'] and not result['human_demonstration_used']
assert result['human_feedback_sources'][0]['sha256']=='2aa49674accf01bb4229aa4215b8b178b9261d99d1c1d40b758368e6f46ef696'
evidence=['result.json',*[f'turn_{i:03d}.json' for i in range(1,result['codex_turns']+1)],'video/scene_setup.json','video/render_manifest.json','video/robot_trace.jsonl','video/episode.mp4','account_route_verified.json','rollout/history.jsonl','rollout/skill_selection.jsonl','policy_instruction_budget.json']
review={'audited_task_success':True,'actor_access':False,'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':'simple/G1WholebodyPickAndPlaceAppleTeleop-v0','completion_contract':'native_simple_criterion','backend':'SIMPLE/MuJoCo with checkpoint standing reset and PD; paused inference, not RTC','model':'gpt-6-astra','effort':'xhigh','reset':reset,'independent_reset_verified':True,'single_action_writer':True,'full_turn_and_skill_update':True,'turn_record_integrity':integrity,'no_replay_or_diagnostic_initial_state':True,'criteria':'Original apple-bowl contact without hand, reward+.1 each call, original two reward calls per step, threshold.2; additionally independently reviewed controlled retained pickup, transport and actual placement in bowl. No new release-hold threshold imposed.','reward_recomputed_for_every_recorded_control_step':True,'saved_state_geometry_audit':str(geometry_path),'max_apple_origin_rise_m':g['max_apple_origin_rise_m'],'longest_loaded_opposition_above_2cm_s':max_loaded_span,'terminal_bowl_only_contact':True,'whole_apple_horizontal_projection_inside_bowl_footprint':True,'horizontal_margin_m':-g['samples'][-1]['apple_xy_signed_margin_m'],'terminal_native_qualified_span_s':g['final_qualified_span_s'],'visual_review':'Public obs0102 left shows apple between opposing open fingers; obs0108 left and later views support retained lift; obs0117 both eyes show apple within bowl and opening hand. No host facts sent to actor.','min_base_height_m':min(heights),'max_base_tilt_deg':max(tilts),'actions':117,'sim_s':result['sim_s'],'video':video,'human_feedback_used':True,'human_demonstration_used':False,'human_feedback_sources':result['human_feedback_sources'],'skill_version':revision['version'],'skill_sha256':revision['skill_sha256'],'instruction_budget':revision['instruction_budget'],'limitations':'Only0.06s terminal bowl support is recorded; no subsequent withdrawal/stability hold due native stop. Apple protrudes above shallow bowl rim; no full-volume containment claim. Feedback/calibration/posture/reset changes confounded, no single-variable causal claim or generalization beyond this reset.','failed_subattempts':'First higher/forward closure and lift at obs0084-0089 failed; second open retreat, lowering and re-entry gave different enclosure before retained pickup. Same reset, not separate failure count.','evidence_sha256':{n:hashlib.sha256((ep/n).read_bytes()).hexdigest() for n in evidence},'geometry_audit_sha256':hashlib.sha256(geometry_path.read_bytes()).hexdigest()}
p=ep/'success_review.json';assert not p.exists();p.write_text(json.dumps(review,indent=2)+'\n');print(json.dumps({k:v for k,v in review.items() if k not in ('reset','evidence_sha256')}))
