import json,sys,numpy as np
from scipy.spatial.transform import Rotation as R
from pathlib import Path
ROOT=Path('/home/galbot/lizekai/RSI/artifacts/R019/xmovebendpick-campaign/episode-0001/rollout/episode')
def obs(i):return json.load(open(ROOT/f'observations/{i:04d}/observation.json'))
def rot(q):return R.from_quat(np.roll(q,-1))
def ray(c,uv):
 k=c['render_intrinsics'];p=np.array([(uv[0]+.5-k['cx'])/k['fx'],-(uv[1]+.5-k['cy'])/k['fy'],-1]);return np.array(c['position_world_m']),np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@p
def stereo(o,a,b):
 c,d=ray(o['images'][0]['calibration'],a);e,f=ray(o['images'][1]['calibration'],b);t=np.linalg.lstsq(np.array([d,-f]).T,e-c,rcond=None)[0];p=c+t[0]*d;q=e+t[1]*f;return (p+q)/2,np.linalg.norm(p-q)
if __name__=='__main__':
 o=obs(int(sys.argv[1]));
 for n,p in o['four_point_world'].items():print(n,np.round(p['position_world_m'],4),np.round(rot(p['quaternion_wxyz']).as_euler('xyz'),4))
 for a,b in [((310,238),(293,238)),((363,241),(347,241)),((313,222),(297,222)),((363,226),(347,226)),((210,275),(194,275))]: print(a,b,stereo(o,a,b))
