import json,sys,itertools,numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
from control import obs,ROOT

def rot(q):return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def bounds(i):
 o=obs(i);h=o['finger_geometry']['hand_collision_model']; m=json.load(open(h['path']))
 for side in ['left','right']:
  allpts=[]
  for n,gs in m['bodies'].items():
   if not n.startswith(side):continue
   bp=h['body_poses_world'][n]; R=rot(bp['quaternion_wxyz']);p=np.array(bp['position_world_m']);pts=[]
   for g in gs:
    if g['kind']=='convex_mesh':v=np.array(g['vertices_body_m'])
    elif g['kind']=='box':v=(np.array(list(itertools.product([-1,1],repeat=3)))*g['size_m'])@np.array(g['rotation_body_from_geom']).T+g['position_body_m']
    else:raise ValueError(g['kind'])
    pts.extend(v@R.T+p)
   pts=np.array(pts);allpts.extend(pts)
   print(n,pts.min(0).round(5).tolist(),pts.max(0).round(5).tolist())
  a=np.array(allpts);print('WHOLE',side,a.min(0).round(6).tolist(),a.max(0).round(6).tolist())
def stereo(i,u,v):
 o=obs(i);a=np.array(Image.open(o['images'][0]['path']).convert('RGB')).astype(float);b=np.array(Image.open(o['images'][1]['path']).convert('RGB')).astype(float);scores=[]
 for d in range(10,35):
  for dy in [-1,0,1]:
   p=a[v-4:v+5,u-12:u+13];q=b[v+dy-4:v+dy+5,u-d-12:u-d+13];scores.append((float(abs(p-q).mean()),d,dy))
 scores.sort();print('matches',scores[:8]);d,dy=scores[0][1:];
 def ray(c,u,v):
  k=c['render_intrinsics'];return np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@np.array([(u+.5-k['cx'])/k['fx'],-(v+.5-k['cy'])/k['fy'],-1])
 c1=o['images'][0]['calibration'];c2=o['images'][1]['calibration'];r1=ray(c1,u,v);r2=ray(c2,u-d,v+dy);p1=np.array(c1['position_world_m']);p2=np.array(c2['position_world_m']);ts=np.linalg.lstsq(np.stack([r1,-r2],1),p2-p1,rcond=None)[0];w1=p1+r1*ts[0];w2=p2+r2*ts[1];print('visible_feature_world',((w1+w2)/2).tolist(),'ray_gap',np.linalg.norm(w1-w2),'disparity',d,'dy',dy)
if __name__=='__main__':
 if sys.argv[1]=='bounds':bounds(int(sys.argv[2]))
 if sys.argv[1]=='stereo':stereo(*map(int,sys.argv[2:]))
