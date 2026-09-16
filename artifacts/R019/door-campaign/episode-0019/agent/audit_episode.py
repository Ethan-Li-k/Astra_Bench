import json,pathlib,numpy as np,collections
root=pathlib.Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0019/rollout/episode');checks=[];statuses=collections.Counter();maxseg={'wrist':0.,'ankle':0.};maxchunk=maxseg.copy();stats=[]
for n in range(1,19):
 e=json.load(open(root/f'execution_{n:04}.json'));a=e['response'];o=json.load(open(root/'observations'/f'{n-1:04}'/'observation.json'));t=a['trajectory'];anchor=o['four_point_world'];prev=anchor;assert 2<=len(t)<=5;assert sum(w['duration_s'] for w in t)<=3+1e-8
 for w in t:
  assert .5<=w['duration_s']<=3;assert w['active']==t[0]['active'];assert w['grippers']=={'left':0,'right':0};assert w['active']['orientation']==[]
  for k,v in w['target'].items():
   q=np.array(v['quaternion_wxyz']);assert abs(np.linalg.norm(q)-1)<1e-6;assert np.allclose(q,anchor[k]['quaternion_wxyz']);p=np.array(v['position_world_m']);s=np.linalg.norm(p-prev[k]['position_world_m']);d=np.linalg.norm(p-anchor[k]['position_world_m']);kind='wrist' if 'wrist' in k else 'ankle';maxseg[kind]=max(maxseg[kind],float(s));maxchunk[kind]=max(maxchunk[kind],float(d));assert s<={'wrist':.06,'ankle':.3}[kind]+1e-8;assert d<={'wrist':.2,'ankle':.3}[kind]+1e-8
   if k not in w['active']['position']:assert np.allclose(p,anchor[k]['position_world_m'])
  prev=w['target']
 r=e['receipts'][-1];statuses[r['status']]+=1;rows=[json.loads(l) for l in open(root/f'robot_motion_{n:04}.jsonl')];p=np.array([x['positions_world_m'] for x in rows]);j=np.array([x['joint_position_rad'] for x in rows]);c=np.array([x['commanded_joint_target_rad'] for x in rows]);assert np.isfinite(p).all() and np.isfinite(j).all() and np.isfinite(c).all();d=p-p[0];stats.append({'n':n,'status':r['status'],'samples':len(rows),'delta_mm':np.round(d[-1]*1000,3).tolist(),'peak_z_mm':np.round(d.max(0)[:,2]*1000,3).tolist(),'max_norm_mm':np.round(np.linalg.norm(d,axis=2).max(0)*1000,3).tolist()})
r={'actions':18,'statuses':dict(statuses),'max_segment_m':maxseg,'max_chunk_m':maxchunk,'all_passed':True,'steps':3277,'execution_sim_s':3277*.02,'stats':stats};json.dump(r,open('episode_audit.json','w'),indent=2);print(json.dumps({k:v for k,v in r.items() if k!='stats'},indent=2))
