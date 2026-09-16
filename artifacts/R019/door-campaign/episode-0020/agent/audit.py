import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
root=Path('/home/galbot/lizekai/RSI/artifacts/R019/door-campaign/episode-0020/rollout');ep=root/'episode';names=['left_wrist_yaw_link','right_wrist_yaw_link','left_ankle_roll_link','right_ankle_roll_link'];fails=[];mxw=mxc=mxa=0;counts={};steps=0
for n in range(1,40):
 e=json.load(open(ep/f'execution_{n:04}.json'));tr=e['response']['trajectory'];o=json.load(open(ep/f'observations/{n-1:04}/observation.json'));base=o['four_point_world'];prev=base;act=tr[0]['active'];grip=tr[0]['grippers'];assert 2<=len(tr)<=5 and sum(t['duration_s'] for t in tr)<=3.000001
 for t in tr:
  assert .5<=t['duration_s']<=3 and t['active']==act and t['grippers']==grip and grip=={'left':0,'right':0}
  for k in names:
   p=np.array(t['target'][k]['position_world_m']);q=np.array(t['target'][k]['quaternion_wxyz']);bp=np.array(base[k]['position_world_m']);bq=np.array(base[k]['quaternion_wxyz']);pp=np.array(prev[k]['position_world_m']);pq=np.array(prev[k]['quaternion_wxyz']);a=np.linalg.norm(p-pp);b=np.linalg.norm(p-bp);assert abs(np.linalg.norm(q)-1)<1e-6
   if 'wrist' in k:mxw=max(mxw,a);mxc=max(mxc,b);assert a<=.060001 and b<=.200001
   else:mxa=max(mxa,a,b);assert a<=.300001 and b<=.300001
   assert 2*np.arccos(np.clip(abs(q@pq),0,1))<=.100001 and 2*np.arccos(np.clip(abs(q@bq),0,1))<=.300001
   if k not in act['position']:assert np.max(abs(p-bp))<1e-8
   if k not in act['orientation']:assert abs(abs(q@bq)-1)<1e-7
  prev=t['target']
 trace=[json.loads(l) for l in open(ep/f'robot_motion_{n:04}.jsonl')]
 for t in trace:
  for k in ['positions_world_m','quaternions_wxyz','joint_position_rad','commanded_joint_target_rad']:assert np.isfinite(t[k]).all()
 steps+=len(trace)-1
 end=json.load(open(ep/f'observations/{n:04}/observation.json'));s=end['command_status']['status'];counts[s]=counts.get(s,0)+1
r={'actions':39,'action_steps':steps,'simulated_action_s':steps*.02,'status_counts':counts,'max_wrist_segment_m':mxw,'max_wrist_chunk_m':mxc,'max_ankle_segment_or_chunk_m':mxa,'all_bounds_inactive_grippers_quaternions_trace_checks':'passed','terminal_receipt':str(root/'call_0039/tool_result.json')};print(json.dumps(r,indent=2));json.dump(r,open('audit.json','w'),indent=2)
old=Path('SKILL.md').read_text();new=old[:old.index('## Current task entry')]+'''## Current task entry

Choose the hand from current lateral alignment; do not mirror arm response. Revalidate low-arm approach, support drift and whole-hand clearance. After saturation or drift, withdraw/lower open hands, then reassess foot stagger and wrist lateral alignment before reapproaching. Wrist shifts and ankle rise do not prove unloading. Separate lateral residual from forward saturation. A lower push may stall despite partial opening; an above-handle push is a candidate after support recovery and clearance checks. Continue until host termination.
''';Path('SKILL.candidate.md').write_text(new)
size={'words':len(new.split())+266,'characters':len(new)+1982,'non_whitespace':len(''.join(new.split()))+1715};print('COMBINED_CAP_CHECK',size);assert size['words']<=831 and size['characters']<=6250 and size['non_whitespace']<=5357
