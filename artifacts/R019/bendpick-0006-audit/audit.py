"""Host-only saved-state audit; does not execute a policy or add an attempt."""
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from rsi.simple_environment import create_native_task_backend
from rsi.simple_recording import restore_named_render_state

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = Path(__file__).parent
EP = ROOT / 'artifacts/R019/bendpick-campaign/episode-0006'
rows = [json.loads(s) for s in (EP/'video/robot_trace.jsonl').read_text().splitlines()]
times = np.array([r['sim_s'] for r in rows])
assert np.allclose(np.diff(times), .02, atol=1e-9)
box = np.array([r['host_render_state']['qpos_by_joint']['cracker_box_joint'][:3] for r in rows])
base = np.array([r['host_render_state']['qpos_by_joint']['floating_base_joint'] for r in rows])
tilt = np.degrees(np.arccos(np.clip(1-2*(base[:,4]**2+base[:,5]**2),-1,1)))
reward = np.array([r['host_render_state']['native_task_reward'] for r in rows])
lift_start = 192.1849999998977  # Recorded action059 start, not a policy target.
lift_rows = [r for r in rows if r['sim_s'] >= lift_start-1e-9]
recorded_support = []
for r in lift_rows:
    contacts = [c for c in r['host_render_state']['external_robot_contacts_host_only']
                if c['other_body']=='cracker_box' and c['normal_force_n']>.1]
    names = {c['robot_body'] for c in contacts}
    recorded_support.append('left_hand_thumb_2_link' in names and
        bool(names & {'left_hand_index_1_link','left_hand_middle_1_link'}))

b = create_native_task_backend('simple/G1WholebodyBendPickTeleop-v0', seed=6)
try:
    m,d = b.model,b.data
    target = m.body('cracker_box').id
    gids = [g for g in range(m.ngeom) if m.geom_bodyid[g]==target and
            (m.geom_contype[g] or m.geom_conaffinity[g])]
    local = {}
    for g in gids:
        assert m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH
        mesh=int(m.geom_dataid[g]); start=int(m.mesh_vertadr[mesh]); n=int(m.mesh_vertnum[mesh])
        local[g]=m.mesh_vert[start:start+n].copy()
    states=[]
    for r in lift_rows:
        restore_named_render_state(m,d,r['host_render_state'])
        zmin=min(float((v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g])[:,2].min())
                 for g,v in local.items())
        support=[]
        for c in d.contact:
            a,other=int(c.geom1),int(c.geom2)
            if a not in gids:
                a,other=other,a
            if a in gids and other not in gids and c.dist<=.0001:
                support.append(m.body(int(m.geom_bodyid[other])).name)
        states.append({'sim_s':r['sim_s'],'box_bottom_world_z_m':zmin,
                       'contact_bodies_geometry_only':sorted(set(support))})
    restore_named_render_state(m,d,rows[0]['host_render_state'])
    initial_bottom=min(float((v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g])[:,2].min())
                       for g,v in local.items())
    # Positive clearance is relative to the box's settled supporting plane; same native table.
    clear=np.array([s['box_bottom_world_z_m']-initial_bottom for s in states])
    trailing=0
    for s in reversed(states):
        if s['contact_bodies_geometry_only'] and all(n.startswith('left_hand_') for n in s['contact_bodies_geometry_only']):trailing+=1
        else:break
    above=reward>=.8
    tail=0
    for ok in reversed(above):
        if ok:tail+=1
        else:break
    result={'actor_access':False,'saved_state_reconstruction_only':True,'new_attempt_credit':False,
        'source_trace_sha256':hashlib.sha256((EP/'video/robot_trace.jsonl').read_bytes()).hexdigest(),
        'samples':len(rows),'sim_s':float(times[-1]-times[0]),'sample_dt_s':.02,
        'min_base_height_m':float(base[:,2].min()),'max_base_tilt_deg':float(tilt.max()),
        'standing_all_samples':bool(np.all(base[:,2]>=.55) and np.all(tilt<=25)),
        'initial_box_origin_z_m':float(box[0,2]),'final_box_origin_z_m':float(box[-1,2]),
        'final_rise_from_recording_start_m':float(box[-1,2]-box[0,2]),
        'native_reward_final':float(reward[-1]),'native_threshold':.8,
        'native_height_baseline_note':'Native baseline is initialized by its first reward call during settling; it differs slightly from recording start.',
        'native_threshold_trailing_sample_span_s':max(0.,(tail-1)*.02),
        'lift_samples':len(lift_rows),'opposing_loaded_contacts_all_lift_samples':all(recorded_support),
        'opposing_loaded_contacts_samples':sum(recorded_support),
        'initial_box_bottom_z_m':initial_bottom,'final_bottom_clearance_from_initial_support_m':float(clear[-1]),
        'last_table_or_other_support_free_sample_span_s':max(0.,(trailing-1)*.02),
        'final_contact_bodies':states[-1]['contact_bodies_geometry_only'],
        'full_height_explicit_hold_action':False,
        'limitations':['50Hz saved states, not continuous-time proof; recomputed contacts are geometry only, recorded forces are the original physical forces.', 'No separate terminal hold or robustness test is added to this episode.']}
    (OUT/'lift_states.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in states))
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
finally:
    b.close()
