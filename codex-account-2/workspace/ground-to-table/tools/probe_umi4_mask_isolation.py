"""Static original ONNX input-isolation test; no physical step or actor input."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
from ground_task import ROOT,GroundSim
from rsi.scalebfm import MODEL_SHA256


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=ROOT/'artifacts/umi4-mask-isolation-01';out.mkdir(exist_ok=False)
    b=GroundSim();a=b.adapter;d=b.data
    initial_time=float(d.time);initial_qpos=d.qpos.copy();initial_qvel=d.qvel.copy()
    policy_history=a.policy_history.copy();action_history=a.action_history.copy()
    pos=np.tile(b.pos0,(34,1,1)).astype(np.float32)
    quat=np.tile(b.quat0,(34,1,1)).astype(np.float32)
    captured={};original=a._run_policy
    def capture(task):
        captured.update(policy=a.policy_history.copy(),policy_task=task[None].copy(),
            action=a.action_history.copy(),mode=a.mode.copy(),mode_mapping=a.mode_mapping.copy())
        return original(task)
    a._run_policy=capture
    baseline=a.infer(d,SimpleNamespace(num_frames=34,body_pos_w=pos,body_quat_w=quat),0)
    a._run_policy=original;a.policy_history[:]=policy_history;a.action_history[:]=action_history
    robot_pos=d.xpos[a.body_ids].astype(np.float32)
    robot_quat=np.array([a._body_quat_wxyz(d,bid) for bid in a.body_ids],dtype=np.float32)
    def evaluate(p,q):
        task=a._build_policy_task(robot_pos[0],robot_quat[0],robot_pos,robot_quat,
            SimpleNamespace(num_frames=34,body_pos_w=p,body_quat_w=q),0)
        feed=dict(captured,policy_task=task[None])
        action=a.session.run(['actions'],feed)[0][0]
        return action*a._action_scale_p+a._default_qpos_p
    baseline_error=float(abs(evaluate(pos,quat)-baseline).max());assert baseline_error<1e-7
    names=a.metadata['selected_body_names'];joints=a.metadata['joint_names'];waist=[joints.index('waist_'+s+'_joint') for s in ('yaw','roll','pitch')]
    rows=[]
    for i,name in enumerate(names):
        active=bool(a.mode[0,i]);p=pos.copy();q=quat.copy()
        p[:,i]+=[.13,-.11,.17] if active else [1.,-2.,3.]
        old=Rotation.from_quat(q[0,i][[1,2,3,0]])
        new=(Rotation.from_rotvec([.2,-.2,.1] if active else [.5,-.7,.9])*old).as_quat()
        q[:,i]=new[[3,0,1,2]]
        target=evaluate(p,q)
        rows.append({'body':name,'active_UMI4':active,'max_joint_target_change_rad':float(abs(target-baseline).max()),
            'waist_target_yaw_roll_pitch_rad':target[waist].tolist()})
    assert np.array_equal(d.qpos,initial_qpos) and np.array_equal(d.qvel,initial_qvel) and d.time==initial_time
    assert np.array_equal(a.policy_history,policy_history) and np.array_equal(a.action_history,action_history)
    report={'backend_model':'Original model_38000 ONNX','model_sha256':MODEL_SHA256,
        'mode':'UMI-4','physics_steps':0,'actor_input':False,'gpt_calls':0,'task_success_credit':0,
        'scope':'Frozen initial robot/history input. Synthetic held pose perturbations are not executable trajectories,achieved poses or stability evidence.',
        'baseline_reconstruction_error_rad':baseline_error,'waist_baseline_yaw_roll_pitch_rad':baseline[waist].tolist(),
        'robot_state_and_histories_preserved':True,'rows':rows,
        'max_untracked_output_change_rad':max(r['max_joint_target_change_rad'] for r in rows if not r['active_UMI4']),
        'all_four_active_positive_controls_respond':all(r['max_joint_target_change_rad']>1e-6 for r in rows if r['active_UMI4']),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    assert report['max_untracked_output_change_rad']==0 and report['all_four_active_positive_controls_respond']


if __name__=='__main__':main()
