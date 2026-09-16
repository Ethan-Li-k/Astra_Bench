from geom import *
from scipy.spatial import ConvexHull
from itertools import combinations
idx=int(sys.argv[1]);o=obs(idx);tr=json.load(open('plan.json'));p=o['four_point_world']['left_wrist_yaw_link'];r=rot(p['quaternion_wxyz']);m=json.load(open(o['finger_geometry']['hand_collision_model']['path']));bp=o['finger_geometry']['hand_collision_model']['body_poses_world'];bf=json.load(open('box_fit_yaw_0012.json'))['visual_cuboid_cx_cy_sx_sy_yaw_bottom_top'];cx,cy,sx,sy,yaw,z0,z1=bf;br=R.from_euler('z',yaw);bc=np.array([cx,cy,(z0+z1)/2]);hs=np.array([sx,sy,z1-z0])/2
vlocal={}
for b,gs in m['bodies'].items():
 if not b.startswith('left_'):continue
 for j,g in enumerate(gs):
  if g['kind']!='convex_mesh':continue
  v=rot(bp[b]['quaternion_wxyz']).apply(g['vertices_body_m'])+bp[b]['position_world_m'];vlocal[b+str(j)]=r.inv().apply(v-p['position_world_m'])
for k,t in enumerate(tr):
 pp=t['target']['left_wrist_yaw_link']; rr=rot(pp['quaternion_wxyz']);print('knot',k+1)
 for b,vl in vlocal.items():
  v=br.inv().apply(rr.apply(vl)+pp['position_world_m']-bc);gap=np.maximum(v.min(0)-hs,-hs-v.max(0));
  if max(gap)<.015: print(b,'box-axis separation',np.round(gap,4),'bounds',np.round(v.min(0),4),np.round(v.max(0),4))
