import json,sys,numpy as np
from pathlib import Path
n=int(sys.argv[1]);root=Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0020/rollout/episode')
a=[json.loads(l) for l in open(root/f'robot_motion_{n:04}.jsonl')];p=np.array([x['positions_world_m'] for x in a]);q=np.array([x['quaternions_wxyz'] for x in a]);j=np.array([x['joint_position_rad'] for x in a]);c=np.array([x['commanded_joint_target_rad'] for x in a]);d=p-p[0];names=['LW','RW','LA','RA'];out={'action':n,'duration':a[-1]['sim_s']-a[0]['sim_s'],'joints_finite':bool(np.isfinite(j).all() and np.isfinite(c).all()),'joint_range':[float(j.min()),float(j.max())],'command_range':[float(c.min()),float(c.max())]}
for i,k in enumerate(names):out[k]={'end_m':p[-1,i].round(5).tolist(),'delta_mm':(d[-1,i]*1000).round(2).tolist(),'peak_norm_mm':round(float(np.linalg.norm(d[:,i],axis=1).max()*1000),2),'peak_rise_mm':round(float(d[:,i,2].max()*1000),2),'last1s_displacement_mm':round(float(np.linalg.norm(p[-1,i]-p[max(0,len(p)-51),i])*1000),2),'rotation_rad':round(float(2*np.arccos(np.clip(abs(q[-1,i]@q[0,i]),0,1))),3)}
print(json.dumps(out));
with open('motion_summaries.jsonl','a') as f:f.write(json.dumps(out)+'\n')
