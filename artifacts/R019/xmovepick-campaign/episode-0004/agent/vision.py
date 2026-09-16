from control import *
def ray(im,uv):
 c=im['calibration'];k=c['render_intrinsics'];a=np.array([(uv[0]+.5-k['cx'])/k['fx'],-(uv[1]+.5-k['cy'])/k['fy'],-1.]);return np.array(c['position_world_m']),np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@a
def tri(o,l,r):
 a,u=ray(o['images'][0],l);b,v=ray(o['images'][1],r);t=np.linalg.lstsq(np.array([u,-v]).T,b-a,rcond=None)[0];p=a+t[0]*u;q=b+t[1]*v;return (p+q)/2,np.linalg.norm(p-q)
def project(im,p):
 c=im['calibration'];k=c['render_intrinsics'];p=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3).T@(np.array(p)-c['position_world_m']);return [k['cx']+k['fx']*p[0]/-p[2]-.5,k['cy']-k['fy']*p[1]/-p[2]-.5]
if __name__=='__main__':
 o=obs(int(sys.argv[1]));print('Robot wrist reprojection',[[project(im,v['position_world_m']) for v in o['four_point_world'].values()][:2] for im in o['images']])
 for pair in json.loads(sys.argv[2]):
  p,e=tri(o,*pair);w=o['four_point_world']['right_wrist_yaw_link'];local=R.from_quat(w['quaternion_wxyz'],scalar_first=True).inv().apply(p-w['position_world_m']);print('pixels',pair,'surface_world',p.tolist(),'ray_error',e,'wrist_local',local.tolist())
 for side in ['left','right']:
  w=o['four_point_world'][side+'_wrist_yaw_link'];rot=R.from_quat(w['quaternion_wxyz'],scalar_first=True)
  for f,g in o['finger_geometry'][side].items():
   import itertools
   corners=np.array(list(itertools.product(*zip(g['bounds_min_wrist_m'],g['bounds_max_wrist_m']))));world=rot.apply(corners)+w['position_world_m'];print(side,f,'world_bounds',world.min(0).tolist(),world.max(0).tolist())
