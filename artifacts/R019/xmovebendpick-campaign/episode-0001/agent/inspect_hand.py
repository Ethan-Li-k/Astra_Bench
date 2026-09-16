from geom import *
o=obs(int(sys.argv[1]));m=json.load(open(o['finger_geometry']['hand_collision_model']['path']));bp=o['finger_geometry']['hand_collision_model']['body_poses_world']
for b,geoms in m['bodies'].items():
 if not b.startswith('left_'):continue
 vs=[]
 for g in geoms:
  if g['kind']=='convex_mesh':vs.append(rot(bp[b]['quaternion_wxyz']).apply(g['vertices_body_m'])+bp[b]['position_world_m'])
 if vs:
  v=np.concatenate(vs); print(b,np.round(v.min(0),4),np.round(v.max(0),4))
print('rpy',rot(o['four_point_world']['left_wrist_yaw_link']['quaternion_wxyz']).as_euler('xyz'))
