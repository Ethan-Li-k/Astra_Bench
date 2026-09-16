from geom import *
from scipy.spatial.transform import Slerp
import sys
cur=obs();side='left';n=side+'_wrist_yaw_link';w=cur['four_point_world'][n];wr=R(w['quaternion_wxyz']);wp=np.array(w['position_world_m'])+np.array(json.loads(sys.argv[1]) if len(sys.argv)>1 else [0,0,0]);p=json.load(open(ROOT/'box_fit.json'))['parameters'];br=Rot.from_euler('xyz',json.load(open(ROOT/'box_fit.json')).get('rotation_rpy',[0,0,p[6]])).as_matrix();half=np.array(p[3:6])/2
for ix in [28,29,30,33]:
 path=Path('/home/galbot/lizekai/RSI/artifacts/R019/xmovepicksim-campaign/episode-0001/rollout/episode/observations')/f'{ix:04d}/observation.json';src=json.load(open(path));sw=src['four_point_world'][n];sr=R(sw['quaternion_wxyz']);sp=np.array(sw['position_world_m']);print('source',ix,'closure',src['gripper_commanded_closure'],'finger angles',np.round(src['finger_position_rad'][:7],3))
 for b,v in meshes(src,side).items():
  world=(v-sp)@sr@wr.T+wp;vb=(world-p[:3])@br;gap=np.maximum(vb.min(0)-half,-half-vb.max(0)).max()
  print(b,'xyz',world.min(0).round(3),world.max(0).round(3),'gap',round(gap,4))
