import json,sys,copy
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT='/home/galbot/lizekai/RSI/artifacts/R019/xmovepick-campaign/episode-0004'
names={'L':'left_wrist_yaw_link','R':'right_wrist_yaw_link','A':'left_ankle_roll_link','B':'right_ankle_roll_link'}
def obs(i):
    return json.load(open(f'{ROOT}/rollout/episode/observations/{i:04d}/observation.json'))
def summary(o):
    return {'sim_s':o['sim_s'],'root':o['robot_root'],'poses':{k:{'p':v['position_world_m'],'rpy':R.from_quat(v['quaternion_wxyz'],scalar_first=True).as_euler('xyz').tolist()} for k,v in o['four_point_world'].items()},'closure':o['gripper_commanded_closure'],'status':{k:v for k,v in o['command_status'].items() if k in ['status','reason','position_error_m','orientation_error_rad','robot_root_summary','elapsed_s']}}
def plan(i,spec):
    o=obs(i); traj=[]
    for knot in spec['knots']:
        t=copy.deepcopy(o['four_point_world'])
        for a,d in knot.get('delta',{}).items(): t[names[a]]['position_world_m']=(np.array(t[names[a]]['position_world_m'])+d).tolist()
        for a,p in knot.get('pos',{}).items(): t[names[a]]['position_world_m']=p
        for a,v in knot.get('rot',{}).items(): t[names[a]]['quaternion_wxyz']=(R.from_rotvec(v)*R.from_quat(t[names[a]]['quaternion_wxyz'],scalar_first=True)).as_quat(scalar_first=True).tolist()
        for a,v in knot.get('localrot',{}).items(): t[names[a]]['quaternion_wxyz']=(R.from_quat(t[names[a]]['quaternion_wxyz'],scalar_first=True)*R.from_rotvec(v)).as_quat(scalar_first=True).tolist()
        traj.append({'duration_s':knot.get('duration',1),'target':t,'active':{c:[names[a] for a in spec[c]] for c in ['position','orientation']},'grippers':spec.get('grippers',o['gripper_goal_closure'])})
    r={'mode':'four_point','request_id':f'ep4_a{i+1:03d}','reason':spec['reason'],'trajectory':traj}
    args={'observation_path':f'{ROOT}/rollout/episode/observations/{i:04d}/observation.json','output_dir':f'{ROOT}/rollout/call_{i+1:04d}','response':r}
    json.dump(args,open(f'{ROOT}/agent/action_{i+1:04d}.json','w'),indent=2)
    with open(f'{ROOT}/agent/NOTES.md','a') as f: f.write(f'\nAction {i+1}: '+spec['reason']+'\n')
    return args
if __name__=='__main__':
    i=int(sys.argv[2])
    print(json.dumps(summary(obs(i)) if sys.argv[1]=='summary' else plan(i,json.load(sys.stdin))))
