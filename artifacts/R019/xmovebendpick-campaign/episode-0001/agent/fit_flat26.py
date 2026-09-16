from geom import *
from scipy.optimize import least_squares
from fit_box import project
# Top corners manually selected in current26 RGB; no object state.
o=obs(26);uv=np.array([[[270,270],[319,264],[268,216],[308,212]],[[254,270],[304,264],[254,216],[296,212]]],float)
def cs(p):
 x,y,sx,sy,a,z=p;xy=np.array([[-sx/2,sy/2],[-sx/2,-sy/2],[sx/2,sy/2],[sx/2,-sy/2]])@np.array([[np.cos(a),np.sin(a)],[-np.sin(a),np.cos(a)]])+[x,y];return np.c_[xy,[z]*4]
def f(p):return np.array([project(im['calibration'],cs(p)) for im in o['images']]).ravel()-uv.ravel()
r=least_squares(f,[-.18,-.055,.22,.16,0,.51]);print('flat26',r.x,'rms',np.sqrt(np.mean(r.fun**2)));print('corners',cs(r.x));json.dump({'visual_cx_cy_sx_sy_yaw_top':r.x.tolist(),'rms_px':float(np.sqrt(np.mean(r.fun**2)))},open('flat_box_0026.json','w'),indent=2)
