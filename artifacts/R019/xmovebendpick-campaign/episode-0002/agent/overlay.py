import sys,json,numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw
ob=json.load(open(sys.argv[1]));v=json.load(open('box_fit.json'))['bounds'];x0,x1,y0,y1,z0,z1,yaw=v;c=np.array([(x0+x1)/2,(y0+y1)/2,0]);pts=Rotation.from_euler('z',yaw).apply(np.array([[x0,y1,z1],[x0,y0,z1],[x1,y1,z1],[x1,y0,z1],[x0,y1,z0],[x0,y0,z0]])-c)+c
for i,im in enumerate(ob['images']):
 cal=im['calibration'];k=cal['render_intrinsics'];p=(pts-cal['position_world_m'])@np.array(cal['rotation_camera_to_world_row_major']).reshape(3,3);uv=np.stack([k['cx']+k['fx']*p[:,0]/-p[:,2]-.5,k['cy']-k['fy']*p[:,1]/-p[:,2]-.5],1)
 img=Image.open(im['path']);d=ImageDraw.Draw(img)
 for u,w in uv:d.ellipse((u-1,w-1,u+1,w+1),outline='red')
 box=(int(uv[:,0].min())-55,int(uv[:,1].min())-25,int(uv[:,0].max())+15,int(uv[:,1].max())+15)
 img.crop(box).resize((800,500)).save('overlay%d.png'%i)
