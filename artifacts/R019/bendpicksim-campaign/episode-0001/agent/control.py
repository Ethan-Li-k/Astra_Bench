import json,sys,numpy as np
from scipy.spatial.transform import Rotation as R
ROOT='/home/galbot/lizekai/RSI/artifacts/R019/bendpicksim-campaign/episode-0001'
def obs(n): return json.load(open(f'{ROOT}/rollout/episode/observations/{n:04d}/observation.json'))
def rot(q):return R.from_quat(np.roll(q,-1))
def summary(n):
 o=obs(n);print('obs',o['observation_id'],'sim_s',round(o['sim_s'],3),'closure',o['gripper_commanded_closure'],'status',o['command_status'].get('status'),'stop',o['stop_reason'])
 for k,v in o['four_point_world'].items():print(k,np.round(v['position_world_m'],5).tolist(),'rpy',np.round(rot(v['quaternion_wxyz']).as_euler('xyz'),4).tolist())
def build(n,idx,deltas,dr=None,closure=0.,duration=1.,hand='left',reason=''):
 o=obs(n);name=hand+'_wrist_yaw_link';start=o['four_point_world'];dr=np.array(dr or [0,0,0]);w=[]
 for i,d in enumerate(deltas):
  target=json.loads(json.dumps(start if len(deltas)>1 else o['four_point_reference_world']))
  target[name]['position_world_m']=(np.array(start[name]['position_world_m'])+d).tolist()
  target[name]['quaternion_wxyz']=np.roll((R.from_rotvec(dr*(i+1)/len(deltas))*rot(start[name]['quaternion_wxyz'])).as_quat(),1).tolist()
  w.append(dict(active=dict(position=[name],orientation=[name]),duration_s=duration,grippers=dict(left=closure if hand=='left' else 0.,right=closure if hand=='right' else 0.),target=target))
 a=dict(observation_path=f'{ROOT}/rollout/episode/observations/{n:04d}/observation.json',output_dir=f'{ROOT}/rollout/call_{idx:04d}',response=dict(mode='four_point',reason=reason,request_id=f'bendpicksim1_a{idx:03d}',trajectory=w));json.dump(a,open(f'command_{idx:03d}.json','w'),indent=2);return a
if __name__=='__main__': summary(int(sys.argv[1]))
def bounds(n,hand='left',p=None,q=None):
 o=obs(n);poses=o['finger_geometry']['hand_collision_model']['body_poses_world'];g=json.load(open(o['finger_geometry']['hand_collision_model']['path']))['bodies'];wp=o['four_point_world'][hand+'_wrist_yaw_link'];wr=rot(wp['quaternion_wxyz']);bp=np.array(wp['position_world_m']);tr=rot(q) if q is not None else wr;tp=np.array(p) if p is not None else bp
 for name,shapes in g.items():
  if not name.startswith(hand):continue
  pts=[];body=poses[name];br=rot(body['quaternion_wxyz']);b=np.array(body['position_world_m'])
  for s in shapes:
   if s['kind']=='convex_mesh':pts.extend(br.apply(s['vertices_body_m'])+b)
  if not pts:continue
  local=wr.inv().apply(np.array(pts)-bp);v=tr.apply(local)+tp
  print(name,'min',v.min(0).round(4).tolist(),'max',v.max(0).round(4).tolist())
