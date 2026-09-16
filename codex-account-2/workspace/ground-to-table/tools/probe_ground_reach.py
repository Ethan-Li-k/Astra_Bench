"""Robot-only reach feasibility at different pelvis-height lower bounds.

Scratch FK only: no physics episode, no successful demonstration, no actor input.
Local optimization cannot establish global impossibility.
"""
import json
from pathlib import Path
import numpy as np
import mujoco
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from ground_task import ROOT,create_backend

def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=ROOT/'artifacts/reach-boundary-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend();m=b.model;d=mujoco.MjData(m);d.qpos[:]=b.data.qpos
    qadr=b.adapter._policy_qpos_adr
    names=b.adapter.metadata['joint_names']
    limits=np.array([m.jnt_range[m.joint(n).id] for n in names])
    feet=b.adapter.body_ids[b.four[2:]]
    footpos=b.data.xpos[feet].copy()
    footrot=[Rotation.from_matrix(x.reshape(3,3)) for x in b.data.xmat[feet]]
    wrist=m.body('left_wrist_yaw_link').id
    target=np.mean(footpos,axis=0)+[.18,.16,.10-float(np.mean(footpos[:,2]))]
    q0=b.data.qpos[qadr].copy();results=[]
    def put(x):
        d.qpos[:2]=x[:2];d.qpos[2]=x[2];d.qpos[3:7]=[1,0,0,0]
        d.qpos[qadr]=x[3:];mujoco.mj_forward(m,d)
    def residual(x):
        put(x);parts=[(d.xpos[feet]-footpos).flatten()]
        for i,bid in enumerate(feet):
            parts.append(.2*(Rotation.from_matrix(d.xmat[bid].reshape(3,3))*footrot[i].inv()).as_rotvec())
        parts.append(d.xpos[wrist]-target)
        parts.append((x[3:]-q0)*1e-5)
        return np.concatenate(parts)
    for low in (.55,.40,.30):
        for seed in (0,1):
            lower=np.r_[-.15,-.10,low,limits[:,0]+1e-5]
            upper=np.r_[.15,.10,.80,limits[:,1]-1e-5]
            x=np.r_[0,0,max(low+.01,.56),q0]
            x[3+names.index('waist_pitch_joint')]=.45 if seed else 0
            x=np.clip(x,lower+1e-7,upper-1e-7)
            fit=least_squares(residual,x,bounds=(lower,upper),max_nfev=450,
                              ftol=1e-9,xtol=1e-9,gtol=1e-9)
            put(fit.x)
            result={'pelvis_lower_bound_m':low,'seed':seed,'solver_success':bool(fit.success),
                    'nfev':fit.nfev,'pelvis_m':d.qpos[:3].tolist(),
                    'wrist_goal_m':target.tolist(),'actual_wrist_m':d.xpos[wrist].tolist(),
                    'wrist_error_m':float(np.linalg.norm(d.xpos[wrist]-target)),
                    'max_foot_position_error_m':float(np.linalg.norm(d.xpos[feet]-footpos,axis=1).max()),
                    'max_foot_rotation_error_rad':max(float((Rotation.from_matrix(d.xmat[bid].reshape(3,3))*footrot[i].inv()).magnitude()) for i,bid in enumerate(feet)),
                    'joint_names':names,'joint_angles_rad':fit.x[3:].tolist(),
                    'physics_executed':False,'formal_success':False,'actor_input':False}
            results.append(result)
            (out/'results.json').write_text(json.dumps(results,indent=2))
            print(json.dumps({k:v for k,v in result.items() if k not in ('joint_names','joint_angles_rad')}),flush=True)
    (out/'scope.json').write_text(json.dumps({'question':'Can a wrist geometrically reach 10 cm above floor while feet remain planted and pelvis obeys original 55 cm stop?',
        'object_state_used':False,'pelvis_attitude':'upright','wrist_orientation':'free',
        'not_certified':'IK does not prove collision-free, dynamically stable, grasp-capable or achievable by the original tracker; failure is only local solver evidence.',
        'gpt_calls':0,'task_success_credit':0},indent=2))

if __name__=='__main__':main()
