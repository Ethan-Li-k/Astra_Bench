import json, sys, itertools
import numpy as np
from scipy.spatial.transform import Rotation

o=json.load(open(sys.argv[1]))
print('observation',o['observation_id'],'sim_s',round(o['sim_s'],3))
for n,p in o['four_point_world'].items():
 print(n,np.round(p['position_world_m'],4).tolist(),np.round(p['quaternion_wxyz'],4).tolist())
for side in ['right']:
 p=o['four_point_world'][side+'_wrist_yaw_link'];q=p['quaternion_wxyz'];r=Rotation.from_quat(q[1:]+q[:1]).as_matrix()
 for name,g in o['finger_geometry'][side].items():
  pts=np.array(list(itertools.product(*zip(g['bounds_min_wrist_m'],g['bounds_max_wrist_m']))))@r.T+p['position_world_m']
  print(side,name,'world AABB',np.round(pts.min(0),4).tolist(),np.round(pts.max(0),4).tolist())
print('closure',o['gripper_commanded_closure'])
s=o['command_status'];print('tracking',{k:s.get(k) for k in ['status','actual_error_m','actual_rotation_error_rad']})
