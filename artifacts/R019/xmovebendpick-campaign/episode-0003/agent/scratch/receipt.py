import json,sys
from pathlib import Path
from control import *
files=sorted((ROOT/'agent/rpc_calls').glob('*_result.json')); r=json.load(open(files[-1])); json.dump({'observation_path':r['observation_path']},open(P,'w'));o=r['observation']
print('OUTCOME', {k:r.get(k) for k in ['native_outcome','rollout_finished','stop_reason','step_id','remaining_steps']});print('STATE',round(o['sim_s'],3),o['robot_root'],pose_summary(o));print('closure',o['gripper_commanded_closure']);print('obs',r['observation_path']);
for e in r.get('execution',[]):
 print('EXEC', {k:v for k,v in e.items() if k in ['status','stop_reason','elapsed_s','tracking_error','motion_feedback_path','motion_trace_path']});print('EXEC_KEYS',list(e))
