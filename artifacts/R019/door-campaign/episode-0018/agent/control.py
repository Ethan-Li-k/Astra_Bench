import json,sys,copy,numpy as np
from pathlib import Path
ROOT=Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0018/rollout/episode')
NAMES=['left_wrist_yaw_link','right_wrist_yaw_link','left_ankle_roll_link','right_ankle_roll_link']
def obs(i):return json.load(open(ROOT/f'observations/{i:04d}/observation.json'))
def prepare(i,kind,args,reason):
 o=obs(i); base=o['four_point_world']; initial=obs(0)['four_point_world']; targets=[]
 if kind=='step':
  side,dx,follow=args[:3]; lift=args[3] if len(args)>3 else .22; foot=side+'_ankle_roll_link'; active=NAMES[:2]+[foot]
  for f in [.5,1.]:
   t=copy.deepcopy(base)
   for n in NAMES[:2]:
    p=t[n]['position_world_m'];p[0]+=follow*f;p[2]+=(initial[n]['position_world_m'][2]-p[2])*f
   t[foot]['position_world_m'][0]+=dx
   t[foot]['position_world_m'][2]+=lift if f==.5 else 0
   targets.append((1.,t))
 elif kind=='transfer':
  side,dx,lift,dy=args;foot=side+'_ankle_roll_link';active=NAMES[:2]+[foot]
  for k,(dur,wy,wx) in enumerate([(.5,dy/2,0),(1,dy,.02),(1,dy,.04)]):
   t=copy.deepcopy(base)
   for n in NAMES[:2]:
    p=t[n]['position_world_m'];p[0]+=wx;p[1]+=wy;p[2]+=(initial[n]['position_world_m'][2]-p[2])*(k+1)/3
   if k>0:t[foot]['position_world_m'][0]+=dx
   if k==1:t[foot]['position_world_m'][2]+=lift
   targets.append((dur,t))
 elif kind=='move':
  changes,knots,duration=args;active=list(changes)
  for k in range(1,knots+1):
   t=copy.deepcopy(base)
   for n,d in changes.items():t[n]['position_world_m']=(np.array(base[n]['position_world_m'])+np.array(d)*k/knots).tolist()
   targets.append((duration/knots,t))
 for _,t in targets:
  for n in NAMES:
   q=np.array(t[n]['quaternion_wxyz']);t[n]['quaternion_wxyz']=(q/np.linalg.norm(q)).tolist()
 prev=base
 for _,t in targets:
  for n in NAMES:
   seg=np.linalg.norm(np.array(t[n]['position_world_m'])-prev[n]['position_world_m']);chunk=np.linalg.norm(np.array(t[n]['position_world_m'])-base[n]['position_world_m'])
   assert seg<=(.06 if 'wrist' in n else .3)+1e-8,(n,seg)
   assert chunk<=(.2 if 'wrist' in n else .3)+1e-8,(n,chunk)
  prev=t
 response={'mode':'four_point','request_id':f'e0018_{i+1:02d}_{kind}','reason':reason,'trajectory':[{'duration_s':d,'grippers':{'left':0,'right':0},'active':{'position':active,'orientation':[]},'target':t} for d,t in targets]}
 out={'observation_path':str(ROOT/f'observations/{i:04d}/observation.json'),'output_dir':str(ROOT.parent/f'call_{i+1:04d}'),'response':response}
 Path(f'plan_{i+1:04d}.json').write_text(json.dumps(out,indent=2))
 with open('NOTES.md','a') as f:f.write(f'\n当前问题/下一检验 action{i+1}: {reason}\n总目标：继续原生推门目标。不可重犯的错误：不以timeout或停滞提前结束；不盲目重放。\n')
 print(json.dumps(out))
def inspect(i):
 o=obs(i);prior=obs(max(0,i-1));print('obs',o['observation_id'],'sim_s',o['sim_s'],'stop',o['stop_reason'])
 print('tracking',{k:o['command_status'].get(k) for k in ['status','actual_error_m','actual_rotation_error_rad']})
 for n in NAMES:
  p=np.array(o['four_point_world'][n]['position_world_m']);b=np.array(prior['four_point_world'][n]['position_world_m']);print(n,'p',p.round(6).tolist(),'delta_mm',((p-b)*1000).round(2).tolist(),'q',np.round(o['four_point_world'][n]['quaternion_wxyz'],6).tolist())
 if i:
  e=json.load(open(ROOT/f'execution_{i:04d}.json'));print('receipt_status',e['receipts'][-1]['status']);
  r=json.load(open(ROOT.parent/f'call_{i:04d}/tool_result.json'));print('native',{k:r.get(k) for k in ['native_outcome','rollout_finished','step_id','remaining_steps']})
  trace=ROOT/f'robot_motion_{i:04d}.jsonl'; rows=[json.loads(s) for s in trace.read_text().splitlines()];print('trace_keys',list(rows[0]))
  if 'positions_world_m' in rows[0]:
   for n in NAMES:
    pts=np.array([r['positions_world_m'][NAMES.index(n)] for r in rows]);b=np.array(prior['four_point_world'][n]['position_world_m']);print('trace',n,'delta_min/max_mm',((pts.min(0)-b)*1000).round(2).tolist(),((pts.max(0)-b)*1000).round(2).tolist(),'max_norm_mm',round(np.linalg.norm(pts-b,axis=1).max()*1000,2))
  for key in ['joint_position_rad','commanded_joint_target_rad']:
   if key in rows[0]:
    a=np.array([r[key] for r in rows]);print(key,'finite',bool(np.isfinite(a).all()),'min/max',a.min().round(4),a.max().round(4))
 print('closure',o['gripper_commanded_closure'])
if __name__=='__main__':
 if sys.argv[1]=='inspect':inspect(int(sys.argv[2]))
 elif sys.argv[1]=='prepare':prepare(int(sys.argv[2]),sys.argv[3],json.loads(sys.argv[4]),sys.argv[5])
