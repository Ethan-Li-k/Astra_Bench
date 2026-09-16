"""Offline host-only assessment and physical-video derivatives, never actor input."""
from pathlib import Path
import json
import sys
import subprocess
import hashlib
import numpy as np

OUT=Path(__file__).resolve().parent
BASE=OUT.parents[2]/'human-feedback/reproductions/H001'

def dump(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2))

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main(number):
    trial=OUT/f'trial-{number:03d}'
    audit=OUT/f'host_audit/trial-{number:03d}'
    result=json.loads((trial/'result.json').read_text())
    trace=audit/'video/robot_trace.jsonl'
    if not trace.exists():raise RuntimeError('No physical trace; cannot count as a physical correction')
    rows=[json.loads(s) for s in trace.open()]
    end_prefix=result['prefix_end_sim_s']
    if end_prefix is None:raise RuntimeError('Prefix failed; no new correction trial')
    prefix=[r for r in rows if r['sim_s']<=end_prefix+1e-8]
    new=[r for r in rows if r['sim_s']>=end_prefix-1e-8]
    oldfile=BASE/'host_audit/attempt-002/video/robot_trace.jsonl'
    fields=('sim_s','reference','measured_four_point_position_world_m','gripper_command','status')
    exact={k:True for k in fields+('qpos_by_joint','mocap_pos','mocap_quat','control_chain')}
    with oldfile.open() as f:
        for r in prefix:
            old=json.loads(f.readline())
            for k in exact:
                a=r.get(k,r['host_render_state'].get(k));b=old.get(k,old['host_render_state'].get(k))
                exact[k] &= a==b
    initial_z=rows[0]['host_render_state']['qpos_by_joint']['apple_joint'][2]
    dwell_start=None;max_dwell=0.;intervals=[];last_contact_time=None;current_interval=None
    contact_samples=0;multi_samples=0;max_lift=0.;max_right_lift=0.;native=False
    first_wz=new[0]['measured_four_point_position_world_m'][1][2]
    samples=[]
    for r in new:
        host=r['host_render_state'];z=host['qpos_by_joint']['apple_joint'][2]
        lift=z-initial_z;max_lift=max(max_lift,lift)
        families={'left':set(),'right':set()}
        contacts=[]
        for c in host.get('external_robot_contacts_host_only',[]):
            if 'apple' in str(c['other_body']).lower() and c['normal_force_n']>.01 and 'hand' in c['robot_body']:
                contacts.append(c)
                for side in families:
                    for finger in ('thumb','index','middle'):
                        if c['robot_body'].startswith(f'{side}_hand_{finger}_'):families[side].add(finger)
        multi=any(len(families[s])>=2 and r['gripper_command'][s]>.1 for s in families)
        contact_samples+=bool(contacts);multi_samples+=multi
        retained=lift>=.05 and multi and not r['status'].get('safety_stop',False)
        if retained:
            if dwell_start is None:dwell_start=r['sim_s']
            max_dwell=max(max_dwell,r['sim_s']-dwell_start)
        elif dwell_start is not None:
            intervals.append([dwell_start,last_contact_time]);dwell_start=None
        if retained:last_contact_time=r['sim_s']
        native |= host['native_task_success']
        max_right_lift=max(max_right_lift,r['measured_four_point_position_world_m'][1][2]-first_wz)
        samples.append({'sim_s':r['sim_s'],'apple_lift_m':lift,'contact_families':{s:sorted(v) for s,v in families.items()},
            'hand_contact':bool(contacts),'two_finger_grasp':multi,'retained_threshold_met':retained})
    if dwell_start is not None:intervals.append([dwell_start,last_contact_time])
    boundaries=json.loads((audit/'action_boundaries.json').read_text()) if (audit/'action_boundaries.json').exists() else []
    tracking=[]
    previous_observation=json.loads((trial/'public/rollout/episode/observations/0059/observation.json').read_text())
    for b in boundaries:
        o=json.loads(Path(b['observation_path']).read_text())
        tracking.append({'new_action':b['new_action'],'sim_s':o['sim_s'],
            'status':o['command_status'].get('status'),'actual_error_m':o['command_status'].get('actual_error_m'),
            'orientation_error_rad':o['command_status'].get('actual_rotation_error_rad'),
            'right_wrist_delta_z_m':o['four_point_world']['right_wrist_yaw_link']['position_world_m'][2]-previous_observation['four_point_world']['right_wrist_yaw_link']['position_world_m'][2],
            'position_error_by_link':o.get('four_point_position_error_world_m'),
            'observation_path':b['observation_path']})
        previous_observation=o
    report={'trial':number,'actor_access':False,'reset':True,'new_actions':result['new_physical_actions'],
        'prefix_samples':len(prefix),'new_samples_including_boundary':len(new),
        'prefix_exact_common_fields':exact,'same_recorded_prefix':all(exact.values()),
        'retained_grasp_host_criterion':max_dwell>=.5-1e-8 and result['stop_reason']!='robot_safety_stop',
        'maximum_apple_lift_m':max_lift,'maximum_right_wrist_lift_from_prefix_m':max_right_lift,
        'maximum_single_action_right_wrist_upward_m':max([t['right_wrist_delta_z_m'] for t in tracking],default=0),
        'maximum_continuous_retained_grasp_s':max_dwell,'retained_intervals_sim_s':intervals,
        'hand_apple_contact_samples':contact_samples,'two_finger_grasp_samples':multi_samples,
        'native_success_during_new_actions':native,'actor_visible_retained_lift':(result['actor_report'] or {}).get('visible_retained_lift'),
        'visible_review':'pending root inspection of public RGB and separate hold',
        'tracking':tracking,'error':result['error'],'formal_campaign_success_credit':False,
        'state_history_limit':'No claim of full historical dependency/state equivalence; common recorded fields checked',
        'contact_sampling_limit':'20ms host samples; substep contact not inferred'}
    dump(audit/'assessment.json',report);dump(audit/'grasp_samples.json',samples)
    evidence=OUT/f'evidence/trial-{number:03d}';evidence.mkdir(parents=True,exist_ok=True)
    src=audit/'video/episode.mp4'
    duration=rows[-1]['sim_s']-rows[0]['sim_s']
    commands=[]
    for name,start,length in [('full-head-left.mp4',0,duration+.04),
            ('correction-head-left.mp4',max(0,end_prefix-rows[0]['sim_s']-3),rows[-1]['sim_s']-end_prefix+3.04)]:
        dest=evidence/name
        if not dest.exists():
            cmd=['ffmpeg','-hide_banner','-loglevel','error','-n','-ss',str(start),'-i',str(src),
                '-t',str(length),'-vf','crop=640:360:640:64','-an','-c:v','libx264','-crf','18',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
            with (OUT/f'logs/video-{number:03d}-{name}.log').open('w') as log:
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            commands.append(cmd)
        subprocess.run(['ffmpeg','-v','error','-i',str(dest),'-f','null','-'],check=True,stdout=subprocess.DEVNULL)
    dump(evidence/'video-provenance.json',{'source':str(src),'source_sha256':sha(src),
        'continuous_physics_recording':True,'physics':'SIMPLE / MuJoCo','non_RTC':True,
        'fixed_prefix_actions':59,'new_actions':result['new_physical_actions'],
        'derivatives_are_new_trials':False,'head_camera':'head_stereo_left','commands':commands,
        'diagnostic_camera_only_in_host_full_video':True,'start_sim_s':rows[0]['sim_s'],'end_sim_s':rows[-1]['sim_s'],
        'new_action_start_sim_s':end_prefix})
    result['host_evaluation']=str(audit/'assessment.json');result['videos']={
        'full_diagnostic_and_head':str(src),'full_public_camera':str(evidence/'full-head-left.mp4'),
        'representative_correction_clip':str(evidence/'correction-head-left.mp4')}
    dump(trial/'result.json',result)
    print(json.dumps({k:v for k,v in report.items() if k!='tracking'},ensure_ascii=False))

if __name__=='__main__':main(int(sys.argv[1]))
