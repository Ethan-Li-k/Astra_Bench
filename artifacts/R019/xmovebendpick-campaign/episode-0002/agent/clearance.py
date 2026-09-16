import json,sys,itertools
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
ob=json.load(open(sys.argv[1]));delta=np.array(json.loads(sys.argv[2]));extra=float(sys.argv[3]) if len(sys.argv)>3 else .003
model=json.load(open(ob['finger_geometry']['hand_collision_model']['path']));poses=ob['finger_geometry']['hand_collision_model']['body_poses_world']
wp=np.array(ob['four_point_world']['left_wrist_yaw_link']['position_world_m']);wq=ob['four_point_world']['left_wrist_yaw_link']['quaternion_wxyz'];wr=R.from_quat(wq[1:]+wq[:1]);rv=(R.from_euler('xyz',json.loads(sys.argv[4]))*wr.inv()).as_rotvec() if len(sys.argv)>4 else np.zeros(3)
v=json.load(open('box_fit.json'))['bounds'];x0,x1,y0,y1,z0,z1,yaw=v
centre=np.array([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]);half=np.array([(x1-x0)/2,(y1-y0)/2,(z1-z0)/2])+extra
rot=R.from_euler('z',yaw).as_matrix();A=np.concatenate([rot.T,-rot.T]);b=np.concatenate([half+rot.T@centre,half-rot.T@centre])
for name,p in poses.items():
 if not name.startswith('left'):continue
 q=p['quaternion_wxyz'];r=R.from_quat(q[1:]+q[:1]);pts=[]
 for g in model['bodies'][name]:
  if g['kind']=='convex_mesh':loc=np.array(g['vertices_body_m'])
  else:
   size=np.array(g['size_m']);kind=g['kind']
   if kind=='box':loc=np.array(list(itertools.product(*[[-a,a] for a in size])))
   else:
    if kind=='sphere':ext=[size[0]]*3
    elif kind=='capsule':ext=[size[0],size[0],size[0]+size[1]]
    elif kind=='cylinder':ext=[size[0],size[0],size[1]]
    else:ext=size
    loc=np.array(list(itertools.product(*[[-a,a] for a in ext])))
   loc=loc@np.array(g['rotation_body_from_geom']).T+g['position_body_m']
  pts.append(r.apply(loc)+p['position_world_m'])
 for t in [0,.25,.5,.75,1]:
  for loc in pts:
   w=R.from_rotvec(t*rv).apply(loc-wp)+wp+t*delta;eq=ConvexHull(w).equations
   sol=linprog(np.zeros(3),A_ub=np.concatenate([A,eq[:,:3]]),b_ub=np.concatenate([b,-eq[:,3]]),bounds=[(None,None)]*3,method='highs')
   if sol.success:print('intersection',name,'t',t,'margin',extra)
 w=R.from_rotvec(rv).apply(np.concatenate(pts)-wp)+wp+delta
 print(name,'end',w.min(0).round(4),w.max(0).round(4))
