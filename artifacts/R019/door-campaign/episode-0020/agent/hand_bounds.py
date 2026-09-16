import json,sys,itertools,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
n=int(sys.argv[1]);root=Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0020/rollout/episode');o=json.load(open(root/f'observations/{n:04}/observation.json'));h=o['finger_geometry']['hand_collision_model'];m=json.load(open(h['path']));
for side in ['left','right']:
 pts=[]
 for name,gs in m['bodies'].items():
  if not name.startswith(side):continue
  p=h['body_poses_world'][name];q=p['quaternion_wxyz'];R=Rotation.from_quat(q[1:]+q[:1]).as_matrix()
  for g in gs:
   if g['kind']=='convex_mesh':a=np.array(g['vertices_body_m'])
   elif g['kind']=='box':
    sz=g.get('size',g.get('size_m'));a=np.array(list(itertools.product([-1,1],repeat=3)))*np.array(sz);a=a@np.array(g['rotation_body_from_geom']).T+g['position_body_m']
   else:print('UNSUPPORTED',g['kind'],g.keys());continue
   pts.extend(a@R.T+np.array(p['position_world_m']))
 a=np.array(pts); print(side,'bounds',a.min(0).round(5).tolist(),a.max(0).round(5).tolist())
