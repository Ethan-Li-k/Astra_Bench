from control import *
from PIL import Image
from scipy.optimize import least_squares
_,o=obs();edges=[]
for i in range(2):
 a=np.array(Image.open(o['images'][i]['path'])).mean(2);e=[[],[],[],[]];th=247
 for u in (range(307,334) if i==0 else range(288,315)):
  yy=np.where(a[266:306,u]>th)[0]+266;t,b=yy.min(),yy.max();e[0].append([u,t-1+(th-a[t-1,u])/(a[t,u]-a[t-1,u])]);e[2].append([u,b+(a[b,u]-th)/(a[b,u]-a[b+1,u])])
 for v in range(278,289):
  xx=np.where(a[v,300 if i==0 else 280:360 if i==0 else 340]>th)[0]+(300 if i==0 else 280);r=xx.max();e[1].append([r+(a[v,r]-th)/(a[v,r]-a[v,r+1]),v])
 edges.append(e)
def corners(p):
 x,y,z,dx,yaw=p;dy=.159573
 return np.array([[dx/2,dy/2,0],[dx/2,-dy/2,0],[-dx/2,-dy/2,0],[-dx/2,dy/2,0]])@R.from_euler('z',yaw).as_matrix().T+[x,y,z]
def fun(p):
 out=[]
 for i in range(2):
  uv=project(o,i,corners(p))
  for j in [0,1,2]:
   aa,bb=uv[j],uv[(j+1)%4];v=bb-aa;v/=np.linalg.norm(v);out.extend((np.array(edges[i][j])-aa)@np.array([-v[1],v[0]]))
 return out
f=least_squares(fun,[-.3,-.062,.663,.0607,.0274]);print('partial FIT',f.x,'RMS',np.sqrt(np.mean(np.array(fun(f.x))**2)));print('repro',[project(o,i,corners(f.x)).round(2).tolist() for i in range(2)])
p=[*f.x[:4],.159573,f.x[4]];json.dump({'p':p,'obs':o['observation_id'],'method':'current visible top/front/right edges, width from unoccluded018 fit; left edge occluded'},open(ROOT/'agent/box.json','w'))
