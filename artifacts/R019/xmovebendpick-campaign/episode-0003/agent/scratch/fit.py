from control import *
from scipy.optimize import least_squares
_,o=obs()
uv=np.array([[[304,206],[352,204],[355,219],[305,222]],[[289,206],[338,204],[340,219],[290,222]]])
def corners(p):
 x,y,z,dx,dy,yaw=p
 off=np.array([[dx/2,dy/2,0],[dx/2,-dy/2,0],[-dx/2,-dy/2,0],[-dx/2,dy/2,0]])
 return off@R.from_euler('z',yaw).as_matrix().T+[x,y,z]
def res(p):return np.concatenate([(project(o,i,corners(p))-uv[i]).ravel() for i in range(2)])
f=least_squares(res,[-.30,-.06,.66,.06,.16,0]);print('FIT',f.x,'rmspx',np.sqrt(np.mean(f.fun**2)));print('corners',corners(f.x));print('repro',*[project(o,i,corners(f.x)) for i in range(2)])
json.dump({'p':f.x.tolist(),'corners':corners(f.x).tolist(),'obs':o['observation_id'],'rms_px':float(np.sqrt(np.mean(f.fun**2)))},open(ROOT/'agent/box.json','w'))
print('table near',tri(o,[210,254],[197,254]),tri(o,[413,249],[399,249]))
g=json.load(open(o['finger_geometry']['hand_collision_model']['path']));print('GEOMETRY SCHEMA',g.keys());print(str(g)[:3000])
