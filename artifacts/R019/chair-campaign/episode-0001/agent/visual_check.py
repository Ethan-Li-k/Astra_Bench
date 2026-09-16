import json,numpy as np
from PIL import Image
from scipy.ndimage import label
from pathlib import Path
root=Path('/home/galbot/lizekai/RSI/artifacts/R019/chair-campaign/episode-0001/rollout/episode/observations')
for idx in [0,8,22,33,34,38]:
 o=json.load(open(root/f'{idx:04d}'/'observation.json'));pts=[]
 for im in o['images']:
  a=np.asarray(Image.open(im['path']));m=(a[:,:,0]>185)&(a[:,:,1]>185)&(a[:,:,2]>185);m[:140]=False;m[235:]=False;m[:,:100]=False;m[:,520:]=False;l,n=label(m);areas=np.bincount(l.ravel());areas[0]=0;ys,xs=np.where(l==areas.argmax());x0,x1=xs.min(),xs.max();v0=np.mean(ys[xs<x0+3]);v1=np.mean(ys[xs>x1-3]);pts.append([(x0+1,v0),(x1-1,v1)]);
 def ray(im,uv):
  c=im['calibration'];k=c['render_intrinsics'];return np.array(c['position_world_m']),np.array(c['rotation_camera_to_world_row_major']).reshape(3,3)@[(uv[0]+.5-k['cx'])/k['fx'],-(uv[1]+.5-k['cy'])/k['fy'],-1]
 xyz=[]
 for j in [0,1]:
  A,u=ray(o['images'][0],pts[0][j]);B,v=ray(o['images'][1],pts[1][j]);s=np.linalg.lstsq(np.array([u,-v]).T,B-A,rcond=None)[0];P=A+s[0]*u;Q=B+s[1]*v;xyz.append(((P+Q)/2).round(3).tolist())
 print(idx,'edge pixels',pts,'world approx',xyz)
