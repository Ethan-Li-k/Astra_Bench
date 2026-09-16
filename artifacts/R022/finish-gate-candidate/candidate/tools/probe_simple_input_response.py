"""Compare ONNX outputs at identical robot/history state; execute no targets."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from rsi.simple_environment import create_closed_door_backend


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args=p.parse_args();args.output.mkdir(parents=True, exist_ok=False)
    b=create_closed_door_backend(pd_profile='checkpoint')
    try:
        a=b.adapter;history=a.policy_history.copy();actions=a.action_history.copy()
        cases=[('hold',(),2,0.)]
        for link in ('left_ankle_roll_link','right_ankle_roll_link','left_wrist_yaw_link'):
            cases.extend((f'{link}-z-{d}',(link,),2,d) for d in (.025,.08,.15))
        cases.append(('both-feet-x',('left_ankle_roll_link','right_ankle_roll_link'),0,.1))
        rows=[];baseline=None
        for label,links,axis,delta in cases:
            pos=np.tile(b.pos0,(34,1,1)).astype(np.float32)
            quat=np.tile(b.quat0,(34,1,1)).astype(np.float32)
            for link in links:
                pos[:,a.metadata['selected_body_names'].index(link),axis]+=delta
            a.policy_history[:]=history;a.action_history[:]=actions
            target=a.infer(b.data,SimpleNamespace(num_frames=34,body_pos_w=pos,body_quat_w=quat),0)
            if baseline is None:baseline=target.copy()
            difference=target-baseline
            rows.append({'case':label,'joint_target_difference_rad':dict(zip(
                a.metadata['joint_names'],map(float,difference))),
                'max_abs_difference_rad':float(np.abs(difference).max()),
                'left_leg_l2_rad':float(np.linalg.norm(difference[:6])),
                'right_leg_l2_rad':float(np.linalg.norm(difference[6:12]))})
        result={'gpt_calls':0,'executed_targets':0,'task_success_credit':False,
                'mode':a.mode.tolist(),'mode_mapping':a.mode_mapping.tolist(),'rows':rows}
        (args.output/'result.json').write_text(json.dumps(result,indent=2))
        for row in rows:print({k:v for k,v in row.items() if k!='joint_target_difference_rad'},flush=True)
    finally:b.close()


if __name__=='__main__':main()
