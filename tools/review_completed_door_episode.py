"""Host review using the existing R020 physical auditor; no gate enrollment."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path

from tools.coordination.ikea_gate import audit_trace, video_probe
from tools.audit_simple_campaigns import turn_completeness


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',type=Path,required=True)
    args=parser.parse_args(); ep=args.episode.resolve()
    read=lambda name: json.loads((ep/name).read_text())
    result=read('result.json');scene=read('video/scene_setup.json');manifest=read('video/render_manifest.json')
    assert result['success'] and result['native_outcome']=='success' and not result['error']
    assert result['skill_updated'] and result['stop_reason']=='native_success'
    assert result['model']=='gpt-6-astra' and result['effort']=='xhigh'
    assert result['account_route']=='authorized_account_2'
    turns=[f'turn_{n:03d}.json' for n in range(1,result['codex_turns']+1)]
    turn_complete, turn_integrity = turn_completeness(ep, result)
    assert turn_complete, turn_integrity
    route=read('account_route_verified.json')
    assert route['model']=='gpt-6-astra' and route['effort']=='xhigh'
    assert route['codex_home'].endswith('/RSI/codex-account-2/home')
    reset=scene['reset_provenance'];assert reset['method']=='fresh_environment_reset'
    assert reset['seed']==int(ep.name.split('-')[-1])
    for other in ep.parent.glob('episode-*/video/scene_setup.json'):
        if other.parent.parent==ep:continue
        prior=json.loads(other.read_text()).get('reset_provenance',{})
        assert prior.get('reset_id')!=reset['reset_id']
        if prior.get('launch'):assert prior['launch']!=reset['launch']
    physics=scene.get('frame_collision_override',{})
    assert physics.get('id')=='asset003-exact-frame-four-boxes-v1'
    assert physics['source_mesh_sha256']=='bd01dac54cb36a782dcb5d589cc7b8e4faaaffff6ecd4ade70358ee8a50679a1'
    stats=audit_trace(ep/'video/robot_trace.jsonl',manifest['initial_render_state'],result['sim_s'])
    history=[json.loads(s) for s in (ep/'rollout/history.jsonl').read_text().splitlines()]
    actions=[e['command_id'] for row in history if row['tool']=='scalebfm_act' for e in row['execution']]
    assert len(set(actions))==len(actions)==result['actions']==stats['commands']
    video=video_probe(ep/'video/episode.mp4');frames=(stats['ticks']+1)//2
    assert int(video['nb_frames'])==frames and video['r_frame_rate']=='25/1'
    assert abs(float(video['duration'])-frames/25)<.041
    rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
    initial=rows[0]['host_render_state']['qpos_by_joint']['articulate_joint_1'][0]
    maximum=-math.inf; minimum_height=math.inf; maximum_tilt=0.;contact_count=0
    pushed=False;since=None;dwell=0.
    for row in rows:
        state=row['host_render_state'];joint=state['qpos_by_joint'];q=joint['floating_base_joint']
        angle=math.degrees(joint['articulate_joint_1'][0]-initial)
        maximum=max(maximum,angle);minimum_height=min(minimum_height,q[2])
        maximum_tilt=max(maximum_tilt,math.degrees(math.acos(max(-1,min(1,1-2*(q[4]**2+q[5]**2))))))
        contact_count+=state['hand_door_contact'];pushed|=state['hand_door_contact']
        if pushed and angle>=30:
            if since is None:since=row['sim_s']
            dwell=max(dwell,row['sim_s']-since)
        else:since=None
    experiences=[json.loads(s) for s in (ep.parent/'memory/experience.jsonl').read_text().splitlines()]
    revision=next(x for x in reversed(experiences) if x['episode_id']==ep.name)
    version=ep.parent/'memory/versions'/f"{revision['version']:04d}.md"
    assert hashlib.sha256(version.read_bytes()).hexdigest()==revision['skill_sha256']
    assert hashlib.sha256((ep/'SKILL.md').read_bytes()).hexdigest()==result['starting_skill_sha256']
    evidence=['result.json',*turns,'SKILL.md','video/scene_setup.json','video/render_manifest.json',
              'video/robot_trace.jsonl','video/episode.mp4','account_route_verified.json',
              'rollout/history.jsonl','rollout/skill_selection.jsonl']
    if (ep/'rollout/policy_stall.jsonl').exists():evidence.append('rollout/policy_stall.jsonl')
    review={'audited_task_success':True,'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'actor_access':False,'task':'SIMPLE asset003 push-open variant with exact-frame collision repair',
        'criteria':'hand contact; >=30deg relative to closed reset; continuous >=1s; standing throughout',
        'backend':'SIMPLE/MuJoCo; paused during inference, not RTC','model':'gpt-6-astra','effort':'xhigh',
        'human_feedback_used':bool(result.get('human_feedback_used',False)),'human_demonstration_used':False,
        'process_instruction_note':'Nonterminal stall process correction is not a human task pose/image label or motion demonstration.',
        'reset':reset,'independent_reset_verified':True,'full_turn_and_skill_update':True,
        'turn_record_integrity':turn_integrity,
        'single_action_writer':True,'no_replay_or_diagnostic_initial_state':True,
        'recording_audit':stats,'max_opening_deg':maximum,'final_opening_deg':angle,
        'longest_qualified_dwell_s':dwell,'hand_contact_samples':contact_count,
        'min_base_height_m':minimum_height,'max_base_tilt_deg':maximum_tilt,'video':video,
        'physics_revision':physics,'unmodified_native_benchmark':False,
        'skill_version':revision['version'],'skill_sha256':revision['skill_sha256'],
        'evidence_sha256':{name:hashlib.sha256((ep/name).read_bytes()).hexdigest() for name in evidence},
        'ikea_gate_registration':'This review does not enroll. Existing R020 schema2 now supports the named repair; use a separately attested receipt if enrollment is needed. Never attest original_physics=true for this repair.'}
    path=ep/'success_review.json'
    if path.exists():raise FileExistsError('Preserve existing review; do not silently overwrite')
    path.write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps({k:v for k,v in review.items() if k not in ['physics_revision','evidence_sha256','reset']}))


if __name__=='__main__':main()
