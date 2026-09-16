"""Host-only saved-state audit: no actor replay and no new task credit."""
from pathlib import Path
import json, hashlib
import mujoco
import numpy as np
from rsi.simple_environment import create_native_task_backend
from rsi.simple_recording import restore_named_render_state

root=Path('/home/galbot/lizekai/RSI')
ep=root/'artifacts/R019/xmovepick-campaign/episode-0003'
out=root/'artifacts/R019/recovery-20260916/xmovepick3-geometry'
out.mkdir(exist_ok=False)
rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
scene=json.loads((ep/'video/scene_setup.json').read_text())
backend=create_native_task_backend(scene['env_id'],seed=3)
try:
    reset_hash=backend.scene_setup['reset_provenance']['post_settle_qpos_qvel_sha256']
    assert reset_hash==scene['reset_provenance']['post_settle_qpos_qvel_sha256']
    model,data=backend.model,backend.data
    reference=float(backend.env.task._init_target_height)
    target=model.body('apple').id
    parts=[]
    for g in range(model.ngeom):
        if model.geom_bodyid[g]!=target or not (model.geom_contype[g] or model.geom_conaffinity[g]):continue
        assert model.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH
        m=int(model.geom_dataid[g]);a=int(model.mesh_vertadr[m]);n=int(model.mesh_vertnum[m])
        parts.append((g,model.mesh_vert[a:a+n].copy()))
    assert parts
    initial_bottom=None; mismatches=[]; samples=[]; longest=0.;since=None
    cmd_stats={}; final_contacts=[]; initial_contacts=[]
    for i,row in enumerate(rows):
        state=row['host_render_state'];restore_named_render_state(model,data,state)
        verts=np.concatenate([v@data.geom_xmat[g].reshape(3,3).T+data.geom_xpos[g] for g,v in parts])
        bottom=float(verts[:,2].min())
        if initial_bottom is None:initial_bottom=bottom
        contacts=[]
        for c in data.contact:
            a,b=[int(model.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
            if target in (a,b):contacts.append({'other_body':model.body(b if a==target else a).name,'distance_m':float(c.dist)})
        nonhand=[c for c in contacts if not c['other_body'].startswith(('left_hand_','right_hand_'))]
        names={c['robot_body'] for c in state['external_robot_contacts_host_only'] if c['other_body']=='apple' and c['normal_force_n']>.01}
        opposed=any(any(n.startswith(s+'_hand_thumb_') for n in names) and any(n.startswith((s+'_hand_middle_',s+'_hand_index_')) for n in names) for s in ['left','right'])
        rise=float(data.xpos[target,2])-reference
        reward=float(np.clip(rise/.1,0,1))
        if abs(reward-state['native_task_reward'])>1e-7 or (reward>=.9)!=state['native_task_success']:
            mismatches.append({'index':i,'expected':reward,'recorded':state['native_task_reward']})
        retained=opposed and not nonhand and bottom-initial_bottom>.001
        if retained:
            if since is None:since=row['sim_s']
            longest=max(longest,row['sim_s']-since)
        else:since=None
        cmd=row['status'].get('command_id')
        if cmd:
            st=cmd_stats.setdefault(cmd,dict(samples=0,retained_samples=0,min_bottom_rise_m=1e9,max_bottom_rise_m=-1e9,first_sim_s=row['sim_s']))
            st['samples']+=1;st['retained_samples']+=int(retained);st['last_sim_s']=row['sim_s']
            st['min_bottom_rise_m']=min(st['min_bottom_rise_m'],bottom-initial_bottom)
            st['max_bottom_rise_m']=max(st['max_bottom_rise_m'],bottom-initial_bottom)
        if i==0:initial_contacts=contacts
        if i==len(rows)-1:final_contacts=contacts
        if i==0 or i==len(rows)-1 or (i and cmd!=rows[i-1]['status'].get('command_id')):
            samples.append(dict(index=i,sim_s=row['sim_s'],command_id=cmd,origin_rise_m=rise,bottom_rise_m=bottom-initial_bottom,opposing_loaded_fingers=sorted(names),no_nonhand_support=not nonhand,retained=retained,bounds_world_m=[verts.min(0).tolist(),verts.max(0).tolist()]))
    report=dict(actor_access=False,diagnostic_only=True,new_attempt_credit=False,
        hypothesis='Native origin-height success may be a tilt/bump; require unsupported full-box clearance and loaded opposing fingers through an independently commanded hold.',
        method='Identical deterministic diagnostic reset checked by complete post-settle qpos/qvel hash, then restore saved named qpos and mj_forward only. Original forces/timing preserved. No old actions or tracker replay.',
        additional_physics_after_initialization=0,reset_hash=reset_hash,native_reference_height_m=reference,
        recomputed_samples=len(rows),reward_mismatches=mismatches,initial_contacts=initial_contacts,final_contacts=final_contacts,
        initial_bottom_m=initial_bottom,longest_opposed_unsupported_full_box_clearance_s=longest,
        final_retained_span_s=rows[-1]['sim_s']-since if since is not None else 0,
        samples=samples,command_stats=cmd_stats,
        trace_sha256=hashlib.sha256((ep/'video/robot_trace.jsonl').read_bytes()).hexdigest(),
        limitations='Geometric clearance relative to original settled box bottom; native stop has no additional post-threshold hold. Current collision assets reused read-only; no task score for reconstruction.')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('samples','command_stats','reward_mismatches')}),flush=True)
    print(json.dumps({'last_commands':list(cmd_stats.items())[-5:],'final':samples[-1]}),flush=True)
    assert longest>1 and samples[-1]['retained']
finally:backend.close()
