import json,sys,copy,numpy as np
from pathlib import Path
root=Path('/home/galbot/lizekai/RSI/artifacts/R019/closedoor-campaign/episode-0001')
cfg=json.loads(sys.argv[1]);p=Path(cfg['observation_path']);o=json.load(open(p));names=list(o['four_point_world'])
active=cfg['active'];ori=cfg.get('orientation',[])
from scipy.spatial.transform import Rotation
trajectory=[]
for knot in cfg['knots']:
 t=copy.deepcopy(o['four_point_world'])
 for key,d in knot.get('deltas',{}).items():t[key]['position_world_m']=(np.array(t[key]['position_world_m'])+d).tolist()
 for key,rv in knot.get('rotations',{}).items():
  q=t[key]['quaternion_wxyz'];r=Rotation.from_rotvec(rv)*Rotation.from_quat(q,scalar_first=True);t[key]['quaternion_wxyz']=r.as_quat(scalar_first=True).tolist()
 trajectory.append({'active':{'position':active,'orientation':ori},'duration_s':knot.get('duration_s',.7),'grippers':{'left':0.,'right':0.},'target':t})
a={'observation_path':str(p),'output_dir':str(root/'rollout'/('call_%04d'%cfg['n'])),'response':{'mode':'four_point','request_id':'close1_%03d'%cfg['n'],'reason':cfg['reason'],'trajectory':trajectory}}
with open('pending_action.json','w') as f:json.dump(a,f,indent=2)
print(json.dumps(a))
