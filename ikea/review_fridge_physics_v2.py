"""Independent raw-contact recomputation for a future sealed fridge episode."""
import math


def robot_hand(name):
    return isinstance(name,str) and any(name==f'{side}_wrist_yaw_link' or name.startswith(f'{side}_hand_')
                                        for side in ('left','right'))


def physical_audit(samples,initial_time):
    if not samples:raise ValueError('No recorded physical samples')
    previous_time=initial_time;previous={'left':0.,'right':0.}
    driven={'left':0.,'right':0.};since={'left':None,'right':None}
    maximum_hold={'left':0.,'right':0.};contact_ticks={'left':0,'right':0}
    valid_time=True;consistent=True;no_safety=True
    for row in samples:
        t=row['sim_s'];angles={s:row['doors'][s]['open_rad'] for s in previous}
        if not all(math.isfinite(x) for x in [t,row['base_z'],row['tilt_rad'],*angles.values()]):
            raise ValueError('Nonfinite physical evidence')
        valid_time &= abs(t-previous_time-.02)<1e-6
        stable=row['base_z']>.55 and 0<=row['tilt_rad']<math.radians(35) and row['safety_reason'] is None
        consistent &= row['stable'] is stable
        no_safety &= row['safety_reason'] is None
        active=set()
        for contact in row['contacts']:
            force=contact['normal_force_n']
            if not math.isfinite(force):raise ValueError('Nonfinite contact force')
            if contact['door'] in previous and robot_hand(contact['robot_body']) and force>.01:
                active.add(contact['door'])
        for side,angle in angles.items():
            if side in active:
                driven[side]+=max(0.,angle-previous[side]);contact_ticks[side]+=1
            qualifies=angle>=math.pi/4 and driven[side]>=math.radians(2.) and stable
            if qualifies:
                if since[side] is None:since[side]=t
                maximum_hold[side]=max(maximum_hold[side],t-since[side])
            else:since[side]=None
            consistent &= row['doors'][side]['hand_contact'] is (side in active)
            previous[side]=angle
        previous_time=t
    final_hold={s:previous_time-start if start is not None else 0. for s,start in since.items()}
    passing=[s for s in previous if previous[s]>=math.pi/4 and driven[s]>=math.radians(2.) and final_hold[s]>=1.]
    checks=dict(continuous_50hz_audit=valid_time,raw_contact_and_stability_consistent=consistent,
        no_backend_safety_stop=no_safety,same_door_hand_drive2deg_terminal_open45_hold1=bool(passing))
    return dict(passed=all(checks.values()),checks=checks,qualified_doors=passing,
        terminal_hold_s=final_hold,maximum_hold_s=maximum_hold,contact_ticks=contact_ticks,
        hand_driven_motion_rad=driven,final_open_rad=previous,ticks=len(samples))
