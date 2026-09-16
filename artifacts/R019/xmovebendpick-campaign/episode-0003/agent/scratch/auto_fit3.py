from control import *
from PIL import Image
from scipy.ndimage import label
from scipy.optimize import least_squares
import sys
_,o=obs();centres=json.loads(sys.argv[1])
def corners(p):
 x,y,z,dx,dy,yaw=p
 return np.array([[dx/2,dy/2,0],[dx/2,-dy/2,0],[-dx/2,-dy/2,0],[-dx/2,dy/2,0]])@R.from_euler('z',yaw).as_matrix().T+[x,y,z]
def extract(th):
 edges=[]
 for i in range(2):
  a=np.array(Image.open(o['images'][i]['path'])).mean(2);labs,_=label(a>th);u0,v0=centres[i];mask=labs==labs[v0,u0];v,u=np.where(mask);xmin,xmax=u.min(),u.max();ymin,ymax=v.min(),v.max();e=[[],[],[],[]]
  for x in range(int(xmin+.18*(xmax-xmin)),int(xmax-.18*(xmax-xmin))+1):
   ys=np.where(mask[:,x])[0];t,b=ys.min(),ys.max()
   e[0].append([x,t-1+(th-a[t-1,x])/(a[t,x]-a[t-1,x])]);e[2].append([x,b+(a[b,x]-th)/(a[b,x]-a[b+1,x])])
  for y in range(int(ymin+.28*(ymax-ymin)),int(ymax-.25*(ymax-ymin))+1):
   xs=np.where(mask[y])[0];l,r=xs.min(),xs.max()
   e[3].append([l-1+(th-a[y,l-1])/(a[y,l]-a[y,l-1]),y]);e[1].append([r+(a[y,r]-th)/(a[y,r]-a[y,r+1]),y])
  edges.append(e)
 return edges
fits=[]
for th in [242,247,250,253]:
 edges=extract(th)
 def fun(p):
  out=[]
  for i in range(2):
   uv=project(o,i,corners(p))
   for j in [0,1,2]:
    a,b=uv[j],uv[(j+1)%4];v=b-a;v/=np.linalg.norm(v);out.extend((np.array(edges[i][j])-a)@np.array([-v[1],v[0]]))
  return out
 f=least_squares(fun,[-.3,-.06,.666,.06,.16,0],loss='soft_l1',f_scale=.3);fits.append(f.x);print('TH',th,'FIT',f.x.round(6),'RMS',np.sqrt(np.mean(np.array(fun(f.x))**2)))
 if th==247:best=f.x
print('RANGE',np.min(fits,axis=0),np.max(fits,axis=0));print('REPRO',[project(o,i,corners(best)).round(2).tolist() for i in range(2)])
json.dump({'p':best.tolist(),'corners':corners(best).tolist(),'obs':o['observation_id'],'threshold_range':[np.min(fits,axis=0).tolist(),np.max(fits,axis=0).tolist()]},open(ROOT/'agent/box.json','w'))
