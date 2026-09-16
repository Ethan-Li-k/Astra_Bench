from control import *
from scipy.optimize import least_squares
_,o=obs()
edges=[[[[315,269],[340,268],[352,267]],[[357,271],[359,280],[360,285]],[[315,292],[335,291],[357,289]],[[301,272],[301,280],[301,292]]], [[[297,269],[315,268],[338,268]],[[339,271],[340,276],[341,282],[341,288]],[[296,292],[320,290],[338,289]],[[282,292],[282,279],[283,272]]]]
def corners(p):
 x,y,z,dx,dy,yaw=p
 return np.array([[dx/2,dy/2,0],[dx/2,-dy/2,0],[-dx/2,-dy/2,0],[-dx/2,dy/2,0]])@R.from_euler('z',yaw).as_matrix().T+[x,y,z]
def fun(p):
 rr=[]
 for i in range(2):
  pix=project(o,i,corners(p))
  for j in range(4):
   a,b=pix[j],pix[(j+1)%4];v=b-a;v/=np.linalg.norm(v);normal=np.array([-v[1],v[0]]);rr.extend((np.array(edges[i][j])-a)@normal)
 return rr
f=least_squares(fun,[-.3,-.06,.65,.06,.16,0]);print('FIT',f.x,'rms',np.sqrt(np.mean(f.fun**2))); print('CORNERS',corners(f.x));print('REPRO',[project(o,i,corners(f.x)).round(2).tolist() for i in range(2)])
json.dump({'p':f.x.tolist(),'corners':corners(f.x).tolist(),'obs':o['observation_id']},open(ROOT/'agent/box.json','w'))
# pixel perturbation bootstrap
rng=np.random.default_rng(12);base=json.loads(json.dumps(edges));fits=[]
for k in range(80):
 edges=[[(np.array(e)+rng.normal(0,.45,np.array(e).shape)).tolist() for e in cam] for cam in base];t=least_squares(fun,f.x);fits.append(t.x)
print('UNC95',np.percentile(fits,[2.5,97.5],axis=0))
