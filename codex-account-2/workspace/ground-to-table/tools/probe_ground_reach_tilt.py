"""Independent robot-only FK diagnostic; never physics or actor experience.

Test the formerly constrained upright-root assumption, retaining the formal
55cm root floor and 25degree tilt ceiling. A local solver is not a reach proof.
"""
import json
from pathlib import Path
import numpy as np
import mujoco
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from ground_task import ROOT, create_backend


def main():
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    out=ROOT/'artifacts/reach-tilt-boundary-01';out.mkdir(parents=True,exist_ok=False)
    b=create_backend();m=b.model;d=mujoco.MjData(m);d.qpos[:]=b.data.qpos
    names=b.adapter.metadata['joint_names'];qadr=b.adapter._policy_qpos_adr
    limits=np.array([m.jnt_range[m.joint(n).id] for n in names])
    feet=b.adapter.body_ids[b.four[2:]];footpos=b.data.xpos[feet].copy()
    footrot=[Rotation.from_matrix(x.reshape(3,3)) for x in b.data.xmat[feet]]
    wrist=m.body('left_wrist_yaw_link').id;q0=b.data.qpos[qadr].copy()
    target=np.mean(footpos,axis=0)+[.18,.16,.10-float(np.mean(footpos[:,2]))]
    def put(x):
        d.qpos[:3]=x[:3];q=Rotation.from_rotvec([0.,x[3],0.]).as_quat()
        d.qpos[3:7]=q[[3,0,1,2]];d.qpos[qadr]=x[4:];mujoco.mj_forward(m,d)
    def residual(x):
        put(x);parts=[(d.xpos[feet]-footpos).flatten(),d.xpos[wrist]-target]
        for i,bid in enumerate(feet):
            parts.append(.2*(Rotation.from_matrix(d.xmat[bid].reshape(3,3))*footrot[i].inv()).as_rotvec())
        parts.append((x[4:]-q0)*1e-5)
        return np.concatenate(parts)
    results=[]
    for tilt in (1e-5,np.deg2rad(24.9)):
        for seed in (0,1):
            lower=np.r_[-.15,-.10,.55,-tilt,limits[:,0]+1e-5]
            upper=np.r_[.15,.10,.80,tilt,limits[:,1]-1e-5]
            x=np.r_[0.,0.,.56,tilt*.8 if seed else 0.,q0]
            x[4+names.index('waist_pitch_joint')]=.45 if seed else 0.
            fit=least_squares(residual,np.clip(x,lower+1e-7,upper-1e-7),bounds=(lower,upper),
                max_nfev=450,ftol=1e-9,xtol=1e-9,gtol=1e-9)
            put(fit.x)
            result={'pelvis_tilt_limit_deg':float(np.rad2deg(tilt)),'seed':seed,
                'solver_success':bool(fit.success),'nfev':fit.nfev,
                'pelvis_m':d.qpos[:3].tolist(),'pelvis_pitch_deg':float(np.rad2deg(fit.x[3])),
                'wrist_goal_m':target.tolist(),'actual_wrist_m':d.xpos[wrist].tolist(),
                'wrist_error_m':float(np.linalg.norm(d.xpos[wrist]-target)),
                'max_foot_position_error_m':float(np.linalg.norm(d.xpos[feet]-footpos,axis=1).max()),
                'max_foot_rotation_error_rad':max(float((Rotation.from_matrix(d.xmat[bid].reshape(3,3))*footrot[i].inv()).magnitude()) for i,bid in enumerate(feet)),
                'joint_names':names,'joint_angles_rad':fit.x[4:].tolist(),
                'physics_executed':False,'formal_success':False,'actor_input':False}
            results.append(result);(out/'results.json').write_text(json.dumps(results,indent=2))
            print(json.dumps({k:v for k,v in result.items() if k not in ('joint_names','joint_angles_rad')}),flush=True)
    (out/'scope.json').write_text(json.dumps({'question':'Does allowing the original legal pelvis pitch materially change the upright-only local reach residual?',
        'object_state_used':False,'pelvis_height_min_m':.55,'wrist_orientation':'free',
        'not_certified':'Local IK only; no global impossibility, collision-free grasp, balance or original-policy feasibility claim.',
        'gpt_calls':0,'task_success_credit':0},indent=2))

if __name__=='__main__':main()
