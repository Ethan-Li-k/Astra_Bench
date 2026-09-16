import json,pathlib,sys,numpy as np
root=pathlib.Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0019/rollout')
r=next(x for p in sorted(pathlib.Path('rpc_calls').glob('*result.json'),reverse=True) if 'observation_path' in (x:=json.load(open(p))))
o=json.load(open(r['observation_path']))
n=int(pathlib.Path(r['observation_path']).parent.name)
s={'n':n,'observation_path':r['observation_path'],'output_dir':r.get('next_call',{}).get('output_dir'),'native_outcome':r.get('native_outcome'),'rollout_finished':r.get('rollout_finished'),'remaining_steps':r.get('remaining_steps'),'step_id':r.get('step_id'),'stop_reason':r.get('stop_reason'),'sim_s':o['sim_s'],'poses':o['four_point_world'],'closure':o['gripper_commanded_closure']}
if n:
 rows=[json.loads(l) for l in open(root/'episode'/f'robot_motion_{n:04}.jsonl')];p=np.array([t['positions_world_m'] for t in rows]);q=np.array([t['joint_position_rad'] for t in rows]);c=np.array([t['commanded_joint_target_rad'] for t in rows]);d=p-p[0]
 e=json.load(open(root/'episode'/f'execution_{n:04}.json'))['receipts'][-1]
 s['motion']={'status':e['status'],'error_m':e['actual_position_error_m_by_link'],'delta_mm':np.round(d[-1]*1000,2).tolist(),'peak_rise_mm':np.round(d.max(axis=0)[:,2]*1000,2).tolist(),'max_displacement_mm':np.round(np.linalg.norm(d,axis=2).max(axis=0)*1000,2).tolist(),'joint_finite':bool(np.isfinite(q).all() and np.isfinite(c).all()),'joint_range':[float(q.min()),float(q.max())],'command_range':[float(c.min()),float(c.max())],'peak_joint_residual_rad':float(np.max(np.abs(q-c)))}
print(json.dumps({'summary':s,'obs':o}))
