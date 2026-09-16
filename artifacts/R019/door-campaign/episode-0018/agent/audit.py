import json,numpy as np,collections
from pathlib import Path
from control import ROOT,NAMES,obs
from scipy.spatial.transform import Rotation
statuses=collections.Counter();maxseg={'wrist':0.,'ankle':0.};maxchunk=maxseg.copy();nknots=[];total=0
for i in range(1,29):
 e=json.load(open(ROOT/f'execution_{i:04d}.json'));r=e['response'];ks=r['trajectory'];base=obs(i-1)['four_point_world'];prev=base
 statuses[e['receipts'][-1]['status']]+=1;nknots.append(len(ks));assert 2<=len(ks)<=5;assert sum(k['duration_s'] for k in ks)<=3+1e-8
 for k in ks:
  assert .5<=k['duration_s']<=3
  assert k['grippers']=={'left':0,'right':0};assert k['active']==ks[0]['active'];assert not k['active']['orientation']
  for n in NAMES:
   t=k['target'][n];typ='wrist' if 'wrist' in n else 'ankle';p=np.array(t['position_world_m']);b=np.array(base[n]['position_world_m']);q=np.array(t['quaternion_wxyz']);qb=np.array(base[n]['quaternion_wxyz'])
   assert np.isfinite(p).all() and np.isfinite(q).all();assert abs(np.linalg.norm(q)-1)<1e-8
   seg=np.linalg.norm(p-prev[n]['position_world_m']);chunk=np.linalg.norm(p-b);maxseg[typ]=max(maxseg[typ],float(seg));maxchunk[typ]=max(maxchunk[typ],float(chunk))
   assert seg<=({'wrist':.06,'ankle':.3}[typ])+1e-8;assert chunk<=({'wrist':.2,'ankle':.3}[typ])+1e-8
   assert np.allclose(q,qb,atol=1e-8)
   if n not in k['active']['position']:assert np.allclose(p,b,atol=1e-8)
  prev=k['target']
 rows=[json.loads(x) for x in (ROOT/f'robot_motion_{i:04d}.jsonl').read_text().splitlines()]
 for k in ['positions_world_m','quaternions_wxyz','joint_position_rad','commanded_joint_target_rad']:assert np.isfinite(np.array([x[k] for x in rows])).all()
a={'actions':28,'tracking_status_counts':dict(statuses),'simulated_action_seconds':obs(28)['sim_s']-obs(0)['sim_s'],'step_id':5287,'waypoint_range':[min(nknots),max(nknots)],'max_segment_translation_m':maxseg,'max_chunk_translation_m':maxchunk,'all_active_sets_constant':True,'all_grippers_open':True,'inactive_components_current_measured':True,'all_traces_finite':True,'terminal_receipt':str(ROOT.parent/'call_0028/tool_result.json'),'no_postterminal_action':True}
for n in NAMES[2:]:
 p=np.array(obs(28)['four_point_world'][n]['position_world_m']);p0=np.array(obs(0)['four_point_world'][n]['position_world_m']);a[n]={'final':p.tolist(),'reset_delta':(p-p0).tolist()}
Path('audit.json').write_text(json.dumps(a,indent=2));print(json.dumps(a,indent=2))
