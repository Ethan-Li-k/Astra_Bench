import json,sys,numpy as np
from PIL import Image
from pathlib import Path
n,u,v=map(int,sys.argv[1:4]);root=Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0020/rollout/episode/observations')/f'{n:04}'
o=json.load(open(root/'observation.json'));im=[np.asarray(Image.open(a['path'])).astype(float) for a in o['images']]; a=im[0][v-4:v+5,u-9:u+10,:3];err=[]
for d in range(5,45):
 b=im[1][v-4:v+5,u-d-9:u-d+10,:3];err.append((round(float(abs(a-b).mean()),3),d))
best=sorted(err)[:5];d=best[0][1];ca=o['images'][0]['calibration'];cb=o['images'][1]['calibration'];K=ca['render_intrinsics'];R=np.array(ca['rotation_camera_to_world_row_major']).reshape(3,3);C=np.array(ca['position_world_m']);B=np.linalg.norm(C-np.array(cb['position_world_m']));z=K['fx']*B/d;world=C+R@np.array([(u+.5-K['cx'])/K['fx']*z,-(v+.5-K['cy'])/K['fy']*z,-z]);print({'pixel':[u,v],'best_MAE_disparity':best,'world_m':world.tolist(),'warning':'visual landmark estimate, pixel uncertainty, not angle or object truth'})
