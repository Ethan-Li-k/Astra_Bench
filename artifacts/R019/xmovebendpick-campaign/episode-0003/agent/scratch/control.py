import json, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
ROOT=Path('/home/galbot/lizekai/RSI/artifacts/R019/xmovebendpick-campaign/episode-0003')
NAMES=['left_wrist_yaw_link','right_wrist_yaw_link','left_ankle_roll_link','right_ankle_roll_link']
P=ROOT/'agent/current.json'
def obs():
 p=json.load(open(P))['observation_path'];return p,json.load(open(p))
def rotation(q): return R.from_quat(np.array(q)[[1,2,3,0]])
def pose_summary(o):
 return {k:dict(p=np.round(v['position_world_m'],4).tolist(),rpy=np.round(rotation(v['quaternion_wxyz']).as_euler('xyz'),3).tolist()) for k,v in o['four_point_world'].items()}
def plan(n,knots,reason,active=None,orient=None,closure=None):
 p,o=obs();b=o['four_point_world'];t=[]
 for knot in knots:
  target=json.loads(json.dumps(b))
  for k,d in knot.get('d',{}).items():target[NAMES[k]]['position_world_m']=(np.array(b[NAMES[k]]['position_world_m'])+d).tolist()
  for k,q in knot.get('q',{}).items():target[NAMES[k]]['quaternion_wxyz']=q
  t.append(dict(active={'position':[NAMES[k] for k in (range(4) if active is None else active)],'orientation':[NAMES[k] for k in (range(4) if orient is None else orient)]},duration_s=knot.get('t',1),grippers=closure or o['gripper_goal_closure'],target=target))
 args=dict(observation_path=p,output_dir=str(ROOT/'rollout'/f'action-{n:03}'),response=dict(mode='four_point',request_id=f'xmbp003-a{n:03}',reason=reason,trajectory=t))
 json.dump(args,open(ROOT/'agent/plan.json','w'))
 with open(ROOT/'agent/NOTES.md','a') as f:f.write(f'\nA{n:03}: Problem/goal: stable approach and retained box lift >=8cm. Avoid stale geometry, premature closure and grasp inferred from wrist rise. {reason}\n')
 print(json.dumps(args))
def project(o,i,pts):
 c=o['images'][i]['calibration'];ri=c['render_intrinsics'];a=(np.array(pts)-c['position_world_m'])@np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)
 return np.column_stack((ri['cx']+ri['fx']*a[:,0]/-a[:,2]-.5,ri['cy']-ri['fy']*a[:,1]/-a[:,2]-.5))
def tri(o,a,b):
 rays=[];orig=[]
 for i,uv in enumerate([a,b]):
  c=o['images'][i]['calibration'];ri=c['render_intrinsics'];v=np.array([(uv[0]+.5-ri['cx'])/ri['fx'],-(uv[1]+.5-ri['cy'])/ri['fy'],-1]);v=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@v;v/=np.linalg.norm(v);rays.append(v);orig.append(np.array(c['position_world_m']))
 t=np.linalg.lstsq(np.column_stack((rays[0],-rays[1])),orig[1]-orig[0],rcond=None)[0];pts=[orig[i]+t[i]*rays[i] for i in range(2)];return (pts[0]+pts[1])/2,np.linalg.norm(pts[0]-pts[1])
if __name__=='__main__':
 _,o=obs();print('STATE',o['sim_s'],o['robot_root'],pose_summary(o));print('closure',o['gripper_commanded_closure']);print('status',o['command_status'])
