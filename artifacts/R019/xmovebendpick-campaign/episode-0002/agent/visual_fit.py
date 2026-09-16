import json,sys,itertools
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
from PIL import Image,ImageDraw
ob=json.load(open(sys.argv[1]))
def project(points,im):
 c=im['calibration'];k=c['render_intrinsics'];r=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)
 p=(np.array(points)-c['position_world_m'])@r
 return np.stack([k['cx']+k['fx']*p[:,0]/-p[:,2]-.5,k['cy']-k['fy']*p[:,1]/-p[:,2]-.5],1)
def vertices(v):
 x0,x1,y0,y1,z0,z1,yaw=v
 pts=np.array([[x0,y1,z1],[x0,y0,z1],[x1,y1,z1],[x1,y0,z1],[x0,y1,z0],[x0,y0,z0]])
 c=np.array([(x0+x1)/2,(y0+y1)/2,0]);return Rotation.from_euler("z",yaw).apply(pts-c)+c
if len(sys.argv)>2:
 px=np.array(json.load(open(sys.argv[2])))
 fun=lambda v: np.concatenate([(project(vertices(v),im)-p).ravel() for im,p in zip(ob['images'],px)])
 fit=least_squares(fun,[-.32,-.25,-.13,.025,.48,.70,0]);v=fit.x
 print('RGB-fitted axis-aligned cuboid',v.round(5).tolist(),'RMSpx',np.sqrt(np.mean(fit.fun**2)))
 json.dump({'bounds':v.tolist(),'rms_px':float(np.sqrt(np.mean(fit.fun**2))),'pixels':px.tolist(),'observation':sys.argv[1]},open('box_fit.json','w'),indent=2)
 for i,im in enumerate(ob['images']):
  img=Image.open(im['path']);d=ImageDraw.Draw(img)
  for u,w in project(vertices(v),im):d.ellipse((u-2,w-2,u+2,w+2),outline='red')
  img.resize((1280,720)).save('fit%d.png'%i)
model=json.load(open(ob['finger_geometry']['hand_collision_model']['path']))
for name,pose in ob['finger_geometry']['hand_collision_model']['body_poses_world'].items():
 if not name.startswith('left'):continue
 pts=[]
 for g in model['bodies'][name]:
  if g['kind']=='convex_mesh':pts.extend(g['vertices_body_m'])
 if not pts:continue
 q=pose['quaternion_wxyz'];r=Rotation.from_quat(q[1:]+q[:1]);w=r.apply(pts)+pose['position_world_m']
 print(name,'world bounds',w.min(0).round(4),w.max(0).round(4))
for name,p in ob['four_point_world'].items():
 q=p['quaternion_wxyz'];print(name,'rpy',Rotation.from_quat(q[1:]+q[:1]).as_euler('xyz').round(4))
