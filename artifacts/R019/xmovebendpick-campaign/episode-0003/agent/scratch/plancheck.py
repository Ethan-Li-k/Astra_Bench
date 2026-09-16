from control import *
from geom import meshes
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
from scipy.spatial.transform import Slerp
_,o=obs();a=json.load(open(ROOT/'agent/plan.json'));b=json.load(open(ROOT/'agent/box.json'));bp=np.array(b['p']);br=R.from_euler('z',bp[5]);bounds=list(zip([-bp[3]/2-.006,-bp[4]/2-.006,.49],[bp[3]/2+.006,bp[4]/2+.006,bp[2]+.007]));base=o['four_point_world'][NAMES[0]];r0=rotation(base['quaternion_wxyz']);p0=np.array(base['position_world_m']);knots=[base]+[k['target'][NAMES[0]] for k in a['response']['trajectory']]
for name,world in meshes(o,'left').items():
 local=r0.inv().apply(world-p0);hits=[];mins=[]
 for j in range(len(knots)-1):
  x,y=knots[j:j+2];p=np.array(x['position_world_m']);d=np.array(y['position_world_m'])-p;sr=Slerp([0,1],R.concatenate([rotation(x['quaternion_wxyz']),rotation(y['quaternion_wxyz'])]))
  for f in np.linspace(0,1,7):
   vv=sr(f).apply(local)+p+f*d;mins.append(vv[:,2].min());v=br.inv().apply(vv-[bp[0],bp[1],0]);h=ConvexHull(v);s=linprog([0,0,0],A_ub=h.equations[:,:3],b_ub=-h.equations[:,3],bounds=bounds,method='highs')
   if s.success:hits.append([j,round(float(f),2)])
 print(name,'hits',hits,'minz',round(min(mins),4))
