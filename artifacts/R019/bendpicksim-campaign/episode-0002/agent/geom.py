import json, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as Rot
from scipy.spatial import ConvexHull
ROOT=Path(__file__).parent
EP=ROOT.parent/'rollout/episode'
def obs(path=None):return json.load(open(path or sorted((EP/'observations').glob('*/observation.json'))[-1]))
def R(q):return Rot.from_quat(np.roll(q,-1)).as_matrix()
def quat(m):return np.roll(Rot.from_matrix(m).as_quat(),1).tolist()
def proj(o,pts,side):
 c=o['images'][side]['calibration'];m=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3);p=(np.array(pts)-c['position_world_m'])@m;k=c['render_intrinsics'];return np.c_[k['cx']+k['fx']*p[:,0]/-p[:,2]-.5,k['cy']-k['fy']*p[:,1]/-p[:,2]-.5]
def tri(o,a,b):
 rays=[];cs=[]
 for s,uv in enumerate([a,b]):
  c=o['images'][s]['calibration'];k=c['render_intrinsics'];d=np.array([(uv[0]+.5-k['cx'])/k['fx'],-(uv[1]+.5-k['cy'])/k['fy'],-1]);d=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@d;d/=np.linalg.norm(d);rays.append(d);cs.append(np.array(c['position_world_m']))
 t=np.linalg.lstsq(np.c_[rays[0],-rays[1]],cs[1]-cs[0],rcond=None)[0];p=[cs[i]+t[i]*rays[i] for i in range(2)];return (p[0]+p[1])/2,np.linalg.norm(p[0]-p[1])
def meshes(o,side):
 g=json.load(open(o['finger_geometry']['hand_collision_model']['path']));poses=o['finger_geometry']['hand_collision_model']['body_poses_world'];out={}
 for b,items in g['bodies'].items():
  if not b.startswith(side):continue
  for i,s in enumerate(items):
   if s['kind']=='convex_mesh':v=np.array(s['vertices_body_m'])
   elif s['kind']=='box':
    from itertools import product
    v=np.array(list(product([-1,1],repeat=3)))*s['size_m'];v=v@np.array(s['rotation_body_from_geom']).T+s['position_body_m']
   else:raise ValueError(s)
   out[b+str(i)]=v@R(poses[b]['quaternion_wxyz']).T+poses[b]['position_world_m']
 return out
def report(o):
 for n,p in o['four_point_world'].items():print(n,np.round(p['position_world_m'],4),'rpy',np.round(Rot.from_matrix(R(p['quaternion_wxyz'])).as_euler('xyz'),3))
 print('sim',o['sim_s'],'root',o['robot_root'],'closure',o['gripper_commanded_closure']);print('elbows',[(n,round(v,3)) for n,v in zip(o['joint_names'],o['joint_position_rad']) if 'elbow' in n])
if __name__=='__main__':report(obs())
