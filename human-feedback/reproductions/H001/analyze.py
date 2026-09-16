"""Read-only analysis of completed H001 physics; no simulator or actor creation."""
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import datetime
import numpy as np
from PIL import Image

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SRC=ROOT/'artifacts/R019/apple-campaign/episode-0003'
AUDIT=OUT/'host_audit/attempt-002'
ATTEMPT=OUT/'attempt-002'
FLAGS={'reproduction_only':True,'task_success_credit':False}

def dump(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False))

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    result=json.loads((ATTEMPT/'result.json').read_text())
    assert result['error'] is None and result['actions_completed']==65,result
    summary=json.loads((AUDIT/'trajectory_summary.json').read_text())
    boundaries=json.loads((AUDIT/'boundaries.json').read_text())
    thresholds=json.loads((OUT/'thresholds.json').read_text())
    assert sha(OUT/'thresholds.json')==result['threshold_sha256']
    source_actions=json.loads((OUT/'source_commands/actions.json').read_text())
    action_checks=[];image_checks=[]
    for i in range(66):
        if i:
            execution=json.loads((ATTEMPT/f'rollout/episode/execution_{i:04d}.json').read_text())
            old_execution=json.loads((SRC/f'rollout/episode/execution_{i:04d}.json').read_text())
            action_checks.append({'action':i,'response_exact':execution['response']==old_execution['response'],
                'source_request_sha256_unchanged':sha(SRC/'agent/rpc_calls'/source_actions[i-1]['rpc'])==source_actions[i-1]['request_sha256']})
        for camera in ('head_stereo_left','head_stereo_right'):
            a=SRC/f'rollout/episode/observations/{i:04d}/{camera}.png'
            b=ATTEMPT/f'rollout/episode/observations/{i:04d}/{camera}.png'
            a_hash,b_hash=sha(a),sha(b)
            row={'action':i,'camera':camera,'original_sha256':a_hash,'reproduced_sha256':b_hash,'exact':a_hash==b_hash}
            if a_hash!=b_hash:
                diff=np.abs(np.asarray(Image.open(a),dtype=float)-np.asarray(Image.open(b),dtype=float))
                row.update(mean_absolute_rgb_0_255=float(diff.mean()),fraction_pixels_channel_difference_gt_10=float((diff.max(-1)>10).mean()))
            image_checks.append(row)
    dump(AUDIT/'all_action_and_image_checks.json',dict(FLAGS,actions=action_checks,images=image_checks))
    assert all(r['response_exact'] and r['source_request_sha256_unchanged'] for r in action_checks)
    by_step={r['action']:r for r in boundaries}
    time62,time64=by_step[62]['sim_s'],by_step[64]['sim_s']
    def assess(trace):
        rows=[]
        with trace.open() as f:
            for line in f:
                row=json.loads(line)
                if time62-1e-8<=row['sim_s']<=time64+1e-8:rows.append(row)
        first,last=rows[0],rows[-1]
        apple0=first['host_render_state']['qpos_by_joint']['apple_joint'][2]
        wz0=first['measured_four_point_position_world_m'][1][2]
        wrist_lift=last['measured_four_point_position_world_m'][1][2]-wz0
        apple_lift=max(r['host_render_state']['qpos_by_joint']['apple_joint'][2]-apple0 for r in rows)
        hand_contacts=[{'sim_s':r['sim_s'],'contact':c} for r in rows
            for c in r['host_render_state'].get('external_robot_contacts_host_only',[])
            if 'hand' in c['robot_body'] and 'apple' in str(c['other_body']).lower()]
        native=any(r['host_render_state']['native_task_success'] for r in rows)
        return {'sample_count':len(rows),'window_sim_s':[first['sim_s'],last['sim_s']],
            'wrist_lift_m':wrist_lift,'maximum_apple_lift_m':apple_lift,
            'apple_delta_final_m':np.subtract(last['host_render_state']['qpos_by_joint']['apple_joint'][:3],first['host_render_state']['qpos_by_joint']['apple_joint'][:3]).tolist(),
            'native_success_any':native,'hand_apple_contacts_if_recorded':hand_contacts,
            'contact_field_available':all('external_robot_contacts_host_only' in r['host_render_state'] for r in rows),
            'failure_observed_by_prefrozen_criterion':wrist_lift>=thresholds['failure_observation']['minimum_wrist_lift_m'] and apple_lift<=thresholds['failure_observation']['maximum_apple_lift_m'] and not native}
    original_assessment=assess(SRC/'video/robot_trace.jsonl')
    new_assessment=assess(AUDIT/'video/robot_trace.jsonl')
    within=summary['first_divergence'] is None
    failure_reproduced=within and original_assessment['failure_observed_by_prefrozen_criterion'] and new_assessment['failure_observed_by_prefrozen_criterion']
    all_images_exact=all(r['exact'] for r in image_checks)
    # Compare common full trace fields independently of the online threshold checker.
    common_exact={'sim_s':True,'reference':True,'measured_four_point_position_world_m':True,'gripper_command':True,
                  'qpos_by_joint':True,'mocap_pos':True,'mocap_quat':True,'control_chain':True,'status':True}
    count=0
    with (SRC/'video/robot_trace.jsonl').open() as a,(AUDIT/'video/robot_trace.jsonl').open() as b:
        for new_line in b:
            old=json.loads(a.readline());new=json.loads(new_line);count+=1
            for key in common_exact:
                old_value=old.get(key,old['host_render_state'].get(key))
                new_value=new.get(key,new['host_render_state'].get(key))
                common_exact[key]&=old_value==new_value
    dump(AUDIT/'failure_assessment.json',dict(FLAGS,original=original_assessment,new=new_assessment,
        observed_prefix_within_thresholds=within,failure_reproduced=failure_reproduced,
        all_132_rgb_files_exact=all_images_exact,common_trace_fields_exact=common_exact,samples=count,
        root_cause_confirmed=False,original_full_state_available=False,
        distinction='Failure of lift/co-motion is tested; palm-height causal mechanism and single-change remedy are not tested.'))
    evidence=OUT/'evidence'; evidence.mkdir(exist_ok=True)
    evidence_index=[]
    for step in [0,50,57,59,60,61,62,63,64,65]:
        for camera in ('head_stereo_left','head_stereo_right'):
            directory=evidence/f'keyframes/{step:04d}';directory.mkdir(parents=True,exist_ok=True)
            for label,root in [('original',SRC),('reproduced',ATTEMPT)]:
                source=root/f'rollout/episode/observations/{step:04d}/{camera}.png'
                dest=directory/f'{label}_{camera}.png';shutil.copyfile(source,dest)
                evidence_index.append({'step':step,'camera':camera,'label':label,'source':str(source),'copy':str(dest),'sha256':sha(dest),'pixels_unmodified':True})
    dump(evidence/'index.json',dict(FLAGS,images=evidence_index,host_state_included=False))
    # Extract the original head camera portion from the newly recorded physical video.
    # This is a derivative of the completed physics, never an additional trial.
    start=by_step[57]['sim_s']-by_step[0]['sim_s']
    duration=by_step[65]['sim_s']-by_step[57]['sim_s']
    command=['ffmpeg','-hide_banner','-loglevel','error','-n','-ss',f'{start:.8f}','-i',str(AUDIT/'video/episode.mp4'),
             '-t',f'{duration:.8f}','-vf','crop=640:360:640:64','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
             '-movflags','+faststart',str(evidence/'closure-lift-head-left.mp4')]
    with (OUT/'logs/video-extract.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    dump(evidence/'video-provenance.json',dict(FLAGS,command=command,
        source=str(AUDIT/'video/episode.mp4'),source_recording='new MuJoCo physical attempt-002',
        derived_video_is_new_physics=False,start_sim_s=by_step[57]['sim_s'],end_sim_s=by_step[65]['sim_s'],
        camera='head_stereo_left',no_annotations_or_privileged_overlay=True))
    summary_public=dict(FLAGS,phase='complete_baseline_frozen' if failure_reproduced else 'complete_with_mismatch_or_unconfirmed_failure',
        updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        backend='SIMPLE MuJoCo',physics_actions_completed=65,attempts=2,first_attempt='250 settling ticks; audit XML export error before action 1',
        gpt_actor_calls=0,paid_api_calls=0,model='gpt-6-astra',effort='xhigh',
        account_route='second_account_existing_session',codex_home='/home/galbot/lizekai/RSI/codex-account-2/home',
        baseline_human_feedback_used=False,human_feedback_read_for_case_context_only=True,human_demonstration_used=False,
        frozen_threshold_sha256=sha(OUT/'thresholds.json'),
        reproduction_match={'classification':'recorded_observables_exact' if all(common_exact.values()) and all_images_exact else 'see_host_audit',
                            'sample_count':count,'actions_identical':65,'rgb_exact_count':sum(r['exact'] for r in image_checks),'rgb_count':132,
                            'material_divergence':not within,'full_hidden_state_equivalence_claimed':False},
        failure_observed=new_assessment['failure_observed_by_prefrozen_criterion'],failure_reproduced=failure_reproduced,
        root_cause_confirmed=False,uncertain_root_causes=['用户同一平面的参照部位待澄清','手掌/对向指面垂直关系是否为决定性原因','闭合几何、接触与视角遮挡各自作用','没有运行单变量下降对照'],
        commands_log=str(OUT/'logs/commands.jsonl'),physics_log=str(OUT/'logs/physics-attempt-002.log'),
        source_actions=str(OUT/'source_commands/actions.json'),physical_trace=str(AUDIT/'physics_history.jsonl'),
        tracker_history=str(AUDIT/'tracker_history.npz'),host_audit=str(AUDIT),
        full_video=str(AUDIT/'video/episode.mp4'),camera_video=str(evidence/'closure-lift-head-left.mp4'),
        raw_keyframes=str(evidence/'index.json'),report=str(OUT/'REPORT.md'),
        next_experiment='Await plane-reference clarification; then separately authorize original reset/prefix plus only preclosure height gate/descent change; no corrective actor run here.',
        main_task='No campaign restarted or interrupted; supervisor owns formal tasks.',
        desktop_notification='pending')
    dump(OUT/'status.json',summary_public)
    dump(OUT/'NEXT_EXPERIMENT.json',dict(FLAGS,status='specification_only_not_executed',
        prerequisite='用户澄清同一平面所指部位；主控或新授权续接。不得将掌心替换为指腹。',
        baseline='Frozen attempt-002 from native reset seed=3, same controller and actions 1–65; no human feedback in commands.',
        independent_variable='Only the visual relative-height judgment before closure and the open-hand descent it triggers.',
        keep_fixed=['same native task/reset seed=3 and checkpoint standing settle','model_38000 hash, UMI-4, PD, wrist PI, 200/50Hz rates, body/hand name mapping',
                    'same unmodified actions through action59 and tracker/PI history','same cameras and action safety/arrival limits','same closure/lift sequence insofar as compatible with changed descent height'],
        implementation_constraint='After descent, translate only the downstream right-wrist height anchors consistently to avoid undoing the treatment; keep XY, orientation, closure ramps and relative lift increments fixed where feasible. Explicitly log any unavoidable deviation; never force original absolute Z after a new descent.',
        actor_inputs=['RGB from the same original cameras','named robot proprioception and calibration','verbatim user semantic feedback after clarification'],
        forbidden_inputs=['host object positions/contact/reward','oracle height or host-derived target','host_audit files or hidden comparison numbers'],
        correction_human_feedback_used=True,human_demonstration_used=False,
        validation='New physics; verify visible sustained apple-hand co-motion and separation, preserve failures/success videos; evaluator stays host-only. A single paired trial does not establish a general rule.',
        actor_created=False,execution_authorized_in_this_task=False))
    print(json.dumps({'failure_reproduced':failure_reproduced,'samples':count,'images_exact':sum(r['exact'] for r in image_checks),
                      'common_trace_fields_exact':common_exact,'host_failure_assessment':new_assessment},ensure_ascii=False))

if __name__=='__main__':main()
