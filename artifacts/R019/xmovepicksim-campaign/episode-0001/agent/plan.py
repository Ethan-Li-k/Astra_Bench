import json,sys,numpy as np
from scipy.spatial.transform import Rotation as R
p=json.load(open(sys.argv[1]));spec=json.loads(sys.argv[2]);N=spec.get('n',3);traj=[];base=p['four_point_world']
for i in range(1,N+1):
 t=json.loads(json.dumps(base))
 for name,d in spec.get('delta',{}).items(): t[name]['position_world_m']=(np.array(base[name]['position_world_m'])+np.array(d)*i/N).tolist()
 for name,rpy in spec.get('rpy',{}).items():
  a=R.from_quat(base[name]['quaternion_wxyz'],scalar_first=True); g=R.from_euler('xyz',rpy); rv=(g*a.inv()).as_rotvec(); ang=np.linalg.norm(rv); rv=rv*min(1,spec.get('rot',.285)/ang)*i/N; t[name]['quaternion_wxyz']=(R.from_rotvec(rv)*a).as_quat(scalar_first=True).tolist()
 traj.append(dict(target=t,active=dict(position=list(spec.get('delta',{})),orientation=list(spec.get('rpy',{}))),duration_s=spec.get('duration',2.4)/N,grippers=spec.get('grippers',{'left':0,'right':0})))
print(json.dumps(traj))
