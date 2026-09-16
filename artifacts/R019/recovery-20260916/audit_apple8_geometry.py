"""Host-only saved-state geometric audit; no actor/action replay or new task credit."""
from pathlib import Path
import json,hashlib,math
import mujoco
import numpy as np
from scipy.spatial import ConvexHull
from rsi.simple_environment import create_native_task_backend
from rsi.simple_recording import restore_named_render_state
root=Path('/home/galbot/lizekai/RSI');ep=root/'artifacts/R019/apple-campaign/episode-0008'
out=root/'artifacts/R019/recovery-20260916/apple8-geometry';out.mkdir(exist_ok=False)
rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
backend=create_native_task_backend('simple/G1WholebodyPickAndPlaceAppleTeleop-v0',seed=8)
try:
 model,data=backend.model,backend.data;target=model.body('apple').id;container=model.body('bowl').id
 reward=0.;mismatches=[];qualified=[];samples=[];lift_contacts=[]
 initial=rows[0]['host_render_state']['qpos_by_joint']['apple_joint'][2]
 peak=max(range(len(rows)),key=lambda i:rows[i]['host_render_state']['qpos_by_joint']['apple_joint'][2])
 for i,row in enumerate(rows):
  state=row['host_render_state'];restore_named_render_state(model,data,state)
  contacts=[]
  for c in data.contact:
   a,b=[int(model.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
   if target in (a,b):contacts.append({'other_body':model.body(b if a==target else a).name,'distance_m':float(c.dist)})
  bowl=any(c['other_body']=='bowl' for c in contacts)
  hand=any('hand' in c['other_body'] for c in contacts)
  q=bowl and not hand;qualified.append(q)
  if i:
   expected=reward+.1 if q else 0.;reward=expected+.1 if q else 0.
   if abs(state['native_task_reward']-expected)>1e-7 or state['native_task_success']!=(reward>=.2):mismatches.append({'index':i,'recorded_reward':state['native_task_reward'],'geometric_expected':expected,'recorded_success':state['native_task_success'],'qualified':q})
  if i in (0,peak,len(rows)-1):
   vertices={}
   for label,bid in [('apple',target),('bowl',container)]:
    parts=[]
    for g in range(model.ngeom):
     if model.geom_bodyid[g]!=bid or not (model.geom_contype[g] or model.geom_conaffinity[g]):continue
     assert model.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH
     mesh=int(model.geom_dataid[g]);start=int(model.mesh_vertadr[mesh]);n=int(model.mesh_vertnum[mesh])
     parts.append(model.mesh_vert[start:start+n]@data.geom_xmat[g].reshape(3,3).T+data.geom_xpos[g])
    vertices[label]=np.concatenate(parts)
   hull=ConvexHull(vertices['bowl'][:,:2]);eq=hull.equations
   signed=float((eq[:,:2]@data.xipos[target,:2]+eq[:,2]).max())
   all_signed=float((vertices['apple'][:,:2]@eq[:,:2].T+eq[:,2]).max())
   samples.append({'index':i,'sim_s':row['sim_s'],'elapsed_sim_s':row['sim_s']-rows[0]['sim_s'],'bounds_world_m':{k:[v.min(0).tolist(),v.max(0).tolist()] for k,v in vertices.items()},'apple_com_world_m':data.xipos[target].tolist(),'apple_com_inside_bowl_footprint':signed<=0,'com_signed_margin_m':signed,'all_apple_xy_inside_bowl_footprint':all_signed<=0,'apple_xy_signed_margin_m':all_signed,'geometry_contacts_only':contacts})
  if state['qpos_by_joint']['apple_joint'][2]-initial>.02:
   cs=[c for c in state['external_robot_contacts_host_only'] if c['other_body']=='apple' and c['normal_force_n']>0]
   names=[c['robot_body'] for c in cs]
   if any('thumb' in n for n in names) and any(('index' in n or 'middle' in n) for n in names):lift_contacts.append(i)
 start=len(rows)-1
 while start>0 and qualified[start-1]:start-=1
 final=samples[-1]
 report={'actor_access':False,'diagnostic_only':True,'new_attempt_credit':False,'method':'Fresh native geometry backend; restore named saved qpos, mj_forward only. No old actions/tracker replay; initialization is diagnostic only. Original trace supplies force and temporal evidence.','additional_physics_after_backend_initialization':0,'recomputed_control_steps':len(rows)-1,'reward_mismatches':mismatches,'samples':samples,'max_apple_origin_rise_m':rows[peak]['host_render_state']['qpos_by_joint']['apple_joint'][2]-initial,'opposing_finger_loaded_samples_above_2cm':len(lift_contacts),'final_qualified_span_s':rows[-1]['sim_s']-rows[start]['sim_s'] if qualified[-1] else 0,'terminal_bowl_only_contact':bool(final['geometry_contacts_only']) and all(c['other_body']=='bowl' for c in final['geometry_contacts_only']),'trace_sha256':hashlib.sha256((ep/'video/robot_trace.jsonl').read_bytes()).hexdigest(),'limitations':'Convex footprint is not interior volume; combined with visual review and exclusive bowl support. Native stop during release prevents post-withdrawal hold. No counterfactual causal attribution of human feedback.'}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 assert not mismatches and final['all_apple_xy_inside_bowl_footprint'] and report['terminal_bowl_only_contact']
 assert lift_contacts and report['max_apple_origin_rise_m']>.05
finally:backend.close()
