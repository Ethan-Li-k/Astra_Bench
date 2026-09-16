import json,sys,numpy as np
from scipy.spatial.transform import Rotation as R

def obs(p): return json.load(open(p))
def ray(o,i,p):
 c=o['images'][i]['calibration']; k=c['render_intrinsics']; d=np.array([(p[0]+.5-k['cx'])/k['fx'],-(p[1]+.5-k['cy'])/k['fy'],-1]); d=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@d; return np.array(c['position_world_m']),d/np.linalg.norm(d)
def stereo(o,l,r):
 a,u=ray(o,0,l); b,v=ray(o,1,r); t=np.linalg.lstsq(np.array([u,-v]).T,b-a,rcond=None)[0]; p=a+t[0]*u;q=b+t[1]*v;return (p+q)/2,np.linalg.norm(p-q)
if __name__=='__main__':
 o=obs(sys.argv[1]);print('sim',o['sim_s'])
 for n,p in o['four_point_world'].items():print(n, np.round(p['position_world_m'],5).tolist(),'rpy',R.from_quat(p['quaternion_wxyz'],scalar_first=True).as_euler('xyz').round(4).tolist())
 if len(sys.argv)>2:
  for pair in json.loads(sys.argv[2]): print('stereo',pair,stereo(o,*pair))
