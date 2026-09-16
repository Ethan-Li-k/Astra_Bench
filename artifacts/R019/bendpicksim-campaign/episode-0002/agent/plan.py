from geom import *
from itertools import product
import sys
spec=json.loads(sys.argv[1]);o=obs();side=spec.get('side','left');name=side+'_wrist_yaw_link';p0=np.array(o['four_point_world'][name]['position_world_m']);r0=R(o['four_point_world'][name]['quaternion_wxyz']);delta=np.array(spec.get('delta',[0,0,0]));rv=np.array(spec.get('rotvec',[0,0,0]));N=spec.get('n',1)

if 'goal_rpy' in spec:
 rv=Rot.from_matrix(Rot.from_euler('xyz',spec['goal_rpy']).as_matrix()@r0.T).as_rotvec();rv*=min(1,spec.get('angle',.27)/np.linalg.norm(rv))
if spec.get('fixed_grasp'):
 fixed=json.load(open(ROOT/'grasp_goal.json'));delta=np.array(fixed['position_world_m'])-p0;rv=Rot.from_matrix(R(fixed['quaternion_wxyz'])@r0.T).as_rotvec()
base=o['four_point_world'] if N>1 else o['four_point_reference_world'];target=json.loads(json.dumps(base));traj=[]
for f in np.linspace(1/N,1,N):
 t=json.loads(json.dumps(target));t[name]={'position_world_m':(p0+f*delta).tolist(),'quaternion_wxyz':quat(Rot.from_rotvec(f*rv).as_matrix()@r0)}
 other=('right' if side=='left' else 'left')+'_wrist_yaw_link';t[other]=o['four_point_world'][other]
 active={'position':[name,other],'orientation':[name] if spec.get('orientation_active',True) else []}
 traj.append({'active':active,'duration_s':spec.get('duration',1.5)/N,'target':t,'grippers':{**o['gripper_goal_closure'],side:spec.get('closure',o['gripper_goal_closure'][side])}})
p=json.load(open(ROOT/'box_fit.json'))['parameters'];br=Rot.from_euler('xyz',json.load(open(ROOT/'box_fit.json')).get('rotation_rpy',[0,0,p[6]])).as_matrix();half=np.array(p[3:6])/2+.004
verts=meshes(o,side);gaps=[];mins=[]
for f in np.linspace(0,1,21):
 rot=Rot.from_rotvec(f*rv).as_matrix();pts={b:(v-p0)@rot.T+p0+f*delta for b,v in verts.items()}
 for b,v in pts.items():
  vb=(v-p[:3])@br;lo=vb.min(0);hi=vb.max(0);gap=np.maximum(lo-half,-half-hi).max();gaps.append((gap,b,float(f)))
  if f==1:print(b,'world bounds',v.min(0).round(3),v.max(0).round(3),'box_axis_separation',round(gap,4))
print('MIN conservative box gap',min(gaps));print('target',traj[-1]['target'][name]);print('ankles', {k:v for k,v in o['four_point_world'].items() if 'ankle' in k})
a={'observation_path':str(sorted((EP/'observations').glob('*/observation.json'))[-1]),'output_dir':str(ROOT.parent/'rollout'/f"call_{int(spec['id']):04d}"),'response':{'mode':'four_point','request_id':f"e2_{spec['id']}",'reason':spec['reason'],'trajectory':traj}}
json.dump(a,open(ROOT/'action.json','w'),indent=2)
with open(ROOT/'NOTES.md','a') as f:f.write('\nPlan '+str(spec)+'\nGeometry conservative minimum: '+str(min(gaps))+'\n')
