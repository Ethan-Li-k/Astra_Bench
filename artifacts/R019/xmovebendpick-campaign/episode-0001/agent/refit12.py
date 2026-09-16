from geom import *
from scipy.optimize import least_squares
import fit_box_yaw as base
base.o=obs(12);base.uv=np.array([[[288,257],[343,256],[290,238.3],[340.3,238.3],[294.2,287.7],[338.7,287]],[[270.8,257],[326.7,256],[274.3,238.3],[324.2,238.3],[280.8,287.7],[325,287]]],float)
r=least_squares(base.f,[-.31,-.05,.06,.16,0,.5,.7]);print('new12',r.x,'rms',np.sqrt(np.mean(r.fun**2)));json.dump({'visual_cuboid_cx_cy_sx_sy_yaw_bottom_top':r.x.tolist(),'rms_px':float(np.sqrt(np.mean(r.fun**2)))},open('box_fit_yaw_0012.json','w'),indent=2)
