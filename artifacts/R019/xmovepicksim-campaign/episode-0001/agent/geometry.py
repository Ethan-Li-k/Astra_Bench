from analyze import *
from scipy.spatial import ConvexHull
from scipy.optimize import linprog

def bodies(o,side='left'):
 h=o['finger_geometry']['hand_collision_model']; m=json.load(open(h['path']));w=o['four_point_world'][side+'_wrist_yaw_link'];wr=R.from_quat(w['quaternion_wxyz'],scalar_first=True);wp=np.array(w['position_world_m']);out={}
 for n,geoms in m['bodies'].items():
  if not n.startswith(side):continue
  bp=h['body_poses_world'][n];br=R.from_quat(bp['quaternion_wxyz'],scalar_first=True)
  for i,g in enumerate(geoms):
   if g['kind']!='convex_mesh':continue
   v=br.apply(g['vertices_body_m'])+bp['position_world_m'];out[n+str(i)]=wr.inv().apply(v-wp)
 return out
if __name__=='__main__':
 o=obs(sys.argv[1]); w=o['four_point_world']['left_wrist_yaw_link']; pos=np.array(w['position_world_m']); rot=R.from_quat(w['quaternion_wxyz'],scalar_first=True);print('rpy',rot.as_euler('xyz').round(4)); vs=bodies(o);d=np.array(json.loads(sys.argv[2])) if len(sys.argv)>2 else np.zeros(3)
 box=np.array([[-.315,-.11,.765],[-.242,.062,.982]])
 for n,v in vs.items():
  v=rot.apply(v)+pos+d;h=ConvexHull(v); A=np.r_[h.equations[:,:3],np.eye(3),-np.eye(3)];b=np.r_[-h.equations[:,3],box[1],-box[0]];ok=linprog([0,0,0],A_ub=A,b_ub=b,bounds=[(None,None)]*3,method='highs').success
  print(n,'min',v.min(0).round(4),'max',v.max(0).round(4),'intersects conservative visual box',ok)
