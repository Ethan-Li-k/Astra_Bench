from geom import *
from scipy.optimize import least_squares
# Current visible cuboid corners, both views. Pixel estimates, not object state.
o=obs(6)
uv=np.array([[[310,239],[364,242],[313,222],[363,225],[311,269],[356,273]],[[293,239],[347,242],[296,222],[347,225],[294,269],[340,273]]],float)
def corners(p):
 x0,x1,y0,y1,z0,z1=p
 return np.array([[x0,y1,z1],[x0,y0,z1],[x1,y1,z1],[x1,y0,z1],[x0,y1,z0],[x0,y0,z0]])
def project(c,pts):
 v=(pts-np.array(c['position_world_m']))@np.array(c['rotation_camera_to_world_row_major']).reshape(3,3);k=c['render_intrinsics'];return np.c_[k['cx']+k['fx']*v[:,0]/-v[:,2]-.5,k['cy']-k['fy']*v[:,1]/-v[:,2]-.5]
def f(p):return np.array([project(im['calibration'],corners(p)) for im in o['images']]).ravel()-uv.ravel()
r=least_squares(f,[-.33,-.26,-.13,.03,.5,.65]);print(r.x, 'RMS px',np.sqrt(np.mean(r.fun**2)));print(np.array([project(im['calibration'],corners(r.x)) for im in o['images']]));json.dump({'visual_estimate_bounds':r.x.tolist(),'rms_px':float(np.sqrt(np.mean(r.fun**2))),'observation':6,'pixels':uv.tolist()},open('box_fit_0006.json','w'),indent=2)
p=json.load(open('/home/galbot/lizekai/RSI/artifacts/R019/bendpick-campaign/episode-0006/rollout/episode/observations/0054/observation.json'))
print('PRIOR candidate left',p['four_point_world']['left_wrist_yaw_link']);print('PRIOR right',p['four_point_world']['right_wrist_yaw_link'])
