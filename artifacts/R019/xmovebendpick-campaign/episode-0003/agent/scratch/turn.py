from control import *
from geom import meshes
import sys
n=int(sys.argv[1]);goal=np.array(json.loads(sys.argv[2]));angle=float(sys.argv[3]); _,o=obs();po=o['four_point_world'][NAMES[0]];r=rotation(po['quaternion_wxyz']);g=R.from_euler('xyz',goal);rv=(g*r.inv()).as_rotvec();theta=np.linalg.norm(rv);rv*=min(angle/theta,1);knots=[]
for f in [1/3,2/3,1]:
 q=(R.from_rotvec(rv*f)*r).as_quat()[[3,0,1,2]].tolist();knots.append({'q':{0:q},'t':1})
pts=meshes(o,'left');p=np.array(po['position_world_m']);print('SWEEP_BOUNDS')
for name,v in pts.items():
 vv=np.concatenate([R.from_rotvec(rv*f).apply(v-p)+p for f in np.linspace(0,1,15)]); print(name,np.round(vv.min(0),4),np.round(vv.max(0),4))
plan(n,knots,'Current box upright; left hand lateral and open. Change left attitude toward a shallower opposed pinch in free space while holding wrist and support poses. Review swept native palm/proximal/distal bounds, then inspect achieved orientation and drift before any medial approach. No closure.',orient=[0,1,2,3],active=([1,2,3] if len(sys.argv)>4 else None))
