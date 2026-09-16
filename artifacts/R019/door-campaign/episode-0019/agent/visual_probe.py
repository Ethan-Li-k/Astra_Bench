import json,sys,numpy as np
from PIL import Image
n=int(sys.argv[1]);u=int(sys.argv[2]);v=int(sys.argv[3]);root='/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0019/rollout/episode'
o=json.load(open(f'{root}/observations/{n:04}/observation.json'));a,b=[np.asarray(Image.open(x['path']).convert('RGB'),float) for x in o['images']]
patch=a[v-6:v+7,u-17:u+18];r=[]
for d in range(8,45):
 q=b[v-6:v+7,u-17-d:u+18-d]
 if q.shape==patch.shape:r.append((float(np.mean(abs(patch-q))),d))
r.sort();d=r[0][1];c=o['images'][0]['calibration'];K=c['render_intrinsics'];R=np.array(c['rotation_camera_to_world_row_major']).reshape(3,3);baseline=np.linalg.norm(np.array(c['position_world_m'])-o['images'][1]['calibration']['position_world_m']);z=K['fx']*baseline/d;p=np.array([(u+.5-K['cx'])*z/K['fx'],-(v+.5-K['cy'])*z/K['fy'],-z]);w=R@p+c['position_world_m']
print(json.dumps({'pixel':[u,v],'best_mae_disparities':r[:6],'approx_world':w.tolist(),'depth_optical':z,'scope':'visible chosen handle patch, integer-disparity uncertainty; no object/angle truth'}))
g=json.load(open(o['finger_geometry']['hand_collision_model']['path']));print('geometry topkeys',list(g));print(str(g)[:1600])
