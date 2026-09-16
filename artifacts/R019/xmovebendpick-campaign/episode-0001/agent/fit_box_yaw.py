exec(open('fit_box.py').read().split('r=least_squares')[0])
def corners(p):
 x,y,sx,sy,a,z0,z1=p
 pts=np.array([[-sx/2,sy/2],[-sx/2,-sy/2],[sx/2,sy/2],[sx/2,-sy/2],[-sx/2,sy/2],[-sx/2,-sy/2]])@np.array([[np.cos(a),np.sin(a)],[-np.sin(a),np.cos(a)]])+[x,y]
 return np.c_[pts,[z1,z1,z1,z1,z0,z0]]
r=least_squares(f,[-.32,-.05,.06,.16,0,.5,.65]);print(r.x,'rms',np.sqrt(np.mean(r.fun**2)));print(np.array([project(im['calibration'],corners(r.x)) for im in o['images']]));json.dump({'visual_cuboid_cx_cy_sx_sy_yaw_bottom_top':r.x.tolist(),'rms_px':float(np.sqrt(np.mean(r.fun**2)))},open('box_fit_yaw_0006.json','w'),indent=2)
