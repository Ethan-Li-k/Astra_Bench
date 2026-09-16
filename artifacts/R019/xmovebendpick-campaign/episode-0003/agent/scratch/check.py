from control import *
from geom import meshes
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
import sys
_,o=obs();b=json.load(open(ROOT/'agent/box.json'));bp=np.array(b['p']);yaw=bp[5];br=R.from_euler('z',yaw);mins=np.array([-bp[3]/2-.006,-bp[4]/2-.006,.49]);maxs=np.array([bp[3]/2+.006,bp[4]/2+.006,bp[2]+.007]);d=np.array(json.loads(sys.argv[1]));
for n,v in meshes(o,'left').items():
 hits=[]
 for f in np.linspace(0,1,21):
  vv=br.inv().apply(v+d*f-np.array([bp[0],bp[1],0]));h=ConvexHull(vv);sol=linprog([0,0,0],A_ub=h.equations[:,:3],b_ub=-h.equations[:,3],bounds=list(zip(mins,maxs)),method='highs')
  if sol.success:hits.append(round(float(f),2))
 print(n,'intersect_expanded_box',hits,'end_bounds',np.round((v+d).min(0),4),np.round((v+d).max(0),4))
