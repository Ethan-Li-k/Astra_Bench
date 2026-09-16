from control import *
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
def vertices(o,hand='left'):
 poses=o['finger_geometry']['hand_collision_model']['body_poses_world'];g=json.load(open(o['finger_geometry']['hand_collision_model']['path']))['bodies'];wp=o['four_point_world'][hand+'_wrist_yaw_link'];wr=rot(wp['quaternion_wxyz']);bp=np.array(wp['position_world_m']);out=[]
 for name,shapes in g.items():
  if not name.startswith(hand):continue
  body=poses[name];br=rot(body['quaternion_wxyz']);b=np.array(body['position_world_m'])
  for s in shapes:
   if s['kind']=='convex_mesh':v=np.array(s['vertices_body_m'])
   else: continue
   out.append((name,wr.inv().apply(br.apply(v)+b-bp)))
 return out
def check(o,p,q,box=((-0.300,-0.240),(-.105,.067),(.755,.973))):
 rr=rot(q)
 for name,local in vertices(o):
  v=rr.apply(local)+p
  if name.endswith('_1_link') or name.endswith('thumb_2_link'):print(name, 'range', v.min(0).round(4),v.max(0).round(4))
  hull=ConvexHull(v);h=hull.equations
  res=linprog([0.,0.,0.],A_ub=h[:,:3],b_ub=-h[:,3],bounds=box,method='highs')
  if res.success:print('INTERSECT',name,np.round(res.x,4))
def triangulate(o,uvs):
 rays=[];cs=[]
 for im,uv in zip(o['images'],uvs):
  c=im['calibration'];k=c['render_intrinsics'];d=np.array([(uv[0]+.5-k['cx'])/k['fx'],-(uv[1]+.5-k['cy'])/k['fy'],-1]);d=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@d;rays.append(d/np.linalg.norm(d));cs.append(np.array(c['position_world_m']))
 t=np.linalg.lstsq(np.array([rays[0],-rays[1]]).T,cs[1]-cs[0],rcond=None)[0];pts=[cs[i]+t[i]*rays[i] for i in range(2)];return np.mean(pts,axis=0),np.linalg.norm(pts[0]-pts[1])
def project(o,xyz,side=0):
 c=o['images'][side]['calibration'];k=c['render_intrinsics'];v=(np.array(xyz)-c['position_world_m'])@np.array(c['rotation_camera_to_world_row_major']).reshape(3,3);return np.stack([k['fx']*v[...,0]/-v[...,2]+k['cx']-.5,k['cy']-k['fy']*v[...,1]/-v[...,2]-.5],-1)
