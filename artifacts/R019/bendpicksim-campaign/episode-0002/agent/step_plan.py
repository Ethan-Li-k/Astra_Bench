from geom import *
from sat import gap_box
from copy import deepcopy
o=obs();base=o['four_point_world'];traj=[]
for i,(f,foot) in enumerate([(1/3,[0,0,.035]),(2/3,[.075,0,.055]),(1,[.075,0,0])]):
 t=deepcopy(base)
 for n in ['left_wrist_yaw_link','right_wrist_yaw_link']:
  d=np.array([.045,-.025,.03 if n.startswith('right') else 0])*f;t[n]['position_world_m']=(np.array(base[n]['position_world_m'])+d).tolist()
 t['left_ankle_roll_link']['position_world_m']=(np.array(base['left_ankle_roll_link']['position_world_m'])+foot).tolist()
 traj.append({'active':{'position':list(base),'orientation':list(base)},'duration_s':[.8,1.,1.][i],'grippers':{'left':0,'right':0},'target':t})
f=json.load(open(ROOT/'box_fit.json'));p=f['parameters'];br=Rot.from_euler('xyz',f['rotation_rpy']).as_matrix();half=np.array(p[3:6])/2+.004
for side in ['left','right']:
 mins=[]
 for frac in np.linspace(0,1,11):
  for b,v in meshes(o,side).items():
   v=v+frac*np.array([.045,-.025,.03 if side=='right' else 0]);vb=(v-p[:3])@br;g=np.maximum(vb.min(0)-half,-half-vb.max(0)).max();mins.append((g,b,frac,float(v[:,2].min())))
 print(side,'minimum conservative swept box gap',min(mins))
a={'observation_path':str(sorted((EP/'observations').glob('*/observation.json'))[-1]),'output_dir':str(ROOT.parent/'rollout/call_0046'),'response':{'mode':'four_point','request_id':'e2_046','reason':'Tracking stalled despite relaxed orientation. Test small coordinated stance approach: left foot up35mm then forward75mm/up55mm then down, right support held; both open wrists advance45mm with25mm rightward bias, right wrist rises30mm. Reviewed whole-hand clearance. Verify peak ankle translation/height, support tilt and view; references do not establish a gait.','trajectory':traj}}
json.dump(a,open(ROOT/'action.json','w'),indent=2)
print('targets',[(x['duration_s'],x['target']['left_ankle_roll_link']['position_world_m']) for x in traj])
with open(ROOT/'NOTES.md','a') as h:h.write('\n046 problem: pose-only reach stalled. Goal retained box lift unchanged. Error avoid: assuming ankle target is step. Changed test: small left-foot raised forward arc plus open wrist lateral bias; inspect trace and view.\n')
