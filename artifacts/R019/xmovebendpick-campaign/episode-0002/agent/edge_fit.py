import json,cv2,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
base='/home/galbot/lizekai/RSI/artifacts/R019/xmovebendpick-campaign/episode-0002/rollout/episode/observations'
old=json.load(open('box_fit.json'))['bounds']
def verts(v):
 x0,x1,y0,y1,z,yaw=v;c=np.array([(x0+x1)/2,(y0+y1)/2,0])
 return R.from_euler('z',yaw).apply(np.array([[x0,y1,z],[x0,y0,z],[x1,y1,z],[x1,y0,z]])-c)+c
def proj(v,im):
 c=im['calibration'];k=c['render_intrinsics'];p=(verts(v)-c['position_world_m'])@np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)
 return np.stack([k['cx']+k['fx']*p[:,0]/-p[:,2]-.5,k['cy']-k['fy']*p[:,1]/-p[:,2]-.5],1)
init=np.array(old[:4]+[old[5],old[6]])
allresults=[]
for th in [210,225,240,250]:
 pairs=[]
 for n in [0,6,10,16,25,30,33]:
  ob=json.load(open(f'{base}/{n:04d}/observation.json'))
  for im in ob['images']:
   gray=cv2.imread(im['path'],0);uv=proj(init,im);centre=uv.mean(0)
   mask=(gray>th).astype('uint8');roi=np.zeros_like(mask);uvc=uv.mean(0);polyroi=uvc+(uv-uvc)*1.08;cv2.fillConvexPoly(roi,polyroi[[0,1,3,2]].astype('int32'),1);mask*=roi;num,labels,stats,centroids=cv2.connectedComponentsWithStats(mask)
   valid=[i for i in range(1,num) if np.linalg.norm(centroids[i]-centre)<10]
   if not valid:continue
   label=min(valid,key=lambda i:np.linalg.norm(centroids[i]-centre));con=cv2.findContours((labels==label).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)[0][0]
   poly=cv2.approxPolyDP(cv2.convexHull(con),1.4,True).reshape(-1,2).astype(float)
   if len(poly)!=4:continue
   # Corresponding corners by nearest expected projection; reject merged/occluded contours.
   order=np.argmin(np.linalg.norm(uv[:,None,:]-poly[None,:,:],axis=2),axis=1)
   if len(set(order))<4:continue
   poly=poly[order]
   if np.max(np.linalg.norm(poly-uv,axis=1))>4:continue
   # Boundary pixel centres bound a filled white face; expand contour by half pixel.
   pc=poly.mean(0);poly=pc+(poly-pc)*(1+.5/np.linalg.norm(poly-pc,axis=1))[:,None]
   pairs.append((im,poly,n))
 if not pairs:
  print('none',th);continue
 fun=lambda v:np.concatenate([(proj(v,im)-px).ravel() for im,px,n in pairs])
 fit=least_squares(fun,init,loss='soft_l1',f_scale=.6)
 print('threshold',th,'view_count',len(pairs),'fit',fit.x.round(5),'rms',np.sqrt(np.mean(fit.fun**2)))
 allresults.append({'threshold':th,'views':len(pairs),'fit':fit.x.tolist(),'rms_px':float(np.sqrt(np.mean(fit.fun**2))),'observations':[n for im,p,n in pairs]})
json.dump(allresults,open('edge_fit_results.json','w'),indent=2)
