from geom import *
from scipy.optimize import least_squares
import fit_box_yaw as base
base.o=obs(11);base.uv=np.array([[[284,259],[340,256],[286,239],[337,238],[288,287],[337,283]],[[268,259],[323,256],[270,239],[322,238],[272,287],[320,283]]],float)
r=least_squares(base.f,[-.31,-.05,.06,.16,0,.5,.7]);print('new11',r.x,'rms',np.sqrt(np.mean(r.fun**2)));json.dump({'visual_cuboid_cx_cy_sx_sy_yaw_bottom_top':r.x.tolist(),'rms_px':float(np.sqrt(np.mean(r.fun**2)))},open('box_fit_yaw_0011.json','w'),indent=2)
