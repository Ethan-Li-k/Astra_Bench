import json,sys,numpy as np,itertools
from scipy.spatial.transform import Rotation
root='/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0019/rollout/episode';n=int(sys.argv[1]);side=sys.argv[2]
o=json.load(open(f'{root}/observations/{n:04}/observation.json'));fg=o['finger_geometry']['hand_collision_model'];g=json.load(open(fg['path']));out=[]
for name,gs in g['bodies'].items():
 if not name.startswith(side):continue
 pose=fg['body_poses_world'][name];q=pose['quaternion_wxyz'];R=Rotation.from_quat(q[1:]+q[:1]).as_matrix();p=np.array(pose['position_world_m']);pts=[]
 for geom in gs:
  if geom['kind']=='convex_mesh':v=np.array(geom['vertices_body_m'])
  elif geom['kind']=='box':v=np.array(list(itertools.product(*[[-s,s] for s in geom['size_m']])));v=v@np.array(geom['rotation_body_from_geom']).T+geom['position_body_m']
  else:raise ValueError(geom['kind'])
  pts.append(v@R.T+p)
 pts=np.concatenate(pts);out.append(pts);print(name, 'min',np.round(pts.min(0),5),'max',np.round(pts.max(0),5))
a=np.concatenate(out);print('whole min',a.min(0),'max',a.max(0))
