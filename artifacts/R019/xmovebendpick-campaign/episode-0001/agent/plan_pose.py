from geom import *
import copy
idx=int(sys.argv[1]);delta=np.array([float(v) for v in sys.argv[2:5]]);goal=np.array([float(v) for v in sys.argv[5:8]]);o=obs(idx);n='left_wrist_yaw_link';p=o['four_point_world'][n];r=rot(p['quaternion_wxyz']);rg=R.from_euler('xyz',goal);rv=(rg*r.inv()).as_rotvec();rv*=min(1,.285/np.linalg.norm(rv));traj=[]
for i in range(1,4):
 t=copy.deepcopy(o['four_point_world']);t[n]['position_world_m']=(np.array(p['position_world_m'])+delta*i/3).tolist();t[n]['quaternion_wxyz']=np.roll((R.from_rotvec(rv*i/3)*r).as_quat(),1).tolist();traj.append(dict(target=t,active=dict(position=list(t),orientation=list(t)),duration_s=1,grippers=dict(left=0,right=0)))
json.dump(traj,open('plan.json','w'));print('delta',delta,'rotation_vector',rv,'angle',np.linalg.norm(rv),'start_rpy',r.as_euler('xyz'),'goal',goal)
m=json.load(open(o['finger_geometry']['hand_collision_model']['path']));bp=o['finger_geometry']['hand_collision_model']['body_poses_world'];vs=[]
for b,geoms in m['bodies'].items():
 if not b.startswith('left_'):continue
 for g in geoms:
  if g['kind']!='convex_mesh':continue
  v=rot(bp[b]['quaternion_wxyz']).apply(g['vertices_body_m'])+bp[b]['position_world_m'];vs.append(r.inv().apply(v-np.array(p['position_world_m'])))
v=np.concatenate(vs)
for t in traj:
 pp=t['target'][n];w=rot(pp['quaternion_wxyz']).apply(v)+pp['position_world_m'];print('planned hand mesh bounds',np.round(w.min(0),4),np.round(w.max(0),4))
