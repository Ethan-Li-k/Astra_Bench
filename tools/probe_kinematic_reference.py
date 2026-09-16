"""Robot-only IK reference diagnostic across trained masks; never actor experience."""
import argparse
import hashlib
import json
from pathlib import Path
import traceback

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from rsi.four_point import FourPointPose
from rsi.reference_sequence import ReferenceSequence
from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import simple_video
from types import SimpleNamespace


def build_reference(b):
    model = b.model; scratch = mujoco.MjData(model)
    scratch.qpos[:] = b.data.qpos
    names = b.adapter.metadata['joint_names']
    leg_names = [n for n in names if any(part in n for part in ('hip_', 'knee_', 'ankle_'))]
    joints = [model.joint(n) for n in leg_names]
    qadr = np.array([j.qposadr[0] for j in joints])
    vadr = np.array([j.dofadr[0] for j in joints])
    limits = np.array([model.jnt_range[j.id] for j in joints])
    root_joint=model.joint('floating_base_joint')
    base_adr=root_joint.qposadr[0]
    # Lateral support transfer can require a lower pelvis to retain a planted
    # foot without hyperextending the opposite knee. Solve that robot-only DoF.
    qadr=np.r_[qadr,base_adr+2]
    vadr=np.r_[vadr,root_joint.dofadr[0]+2]
    limits=np.vstack([limits,[b.data.qpos[base_adr+2]-.08,b.data.qpos[base_adr+2]]])
    measured = FourPointPose(b.data.xpos[b.adapter.body_ids[b.four]],
                             b.data.xquat[b.adapter.body_ids[b.four]])
    knots = [measured.copy() for _ in range(5)]
    knots[2].positions[2] += [.06, 0, .06]
    knots[3].positions[2] += [.12, 0, 0]
    knots[4].positions[2] += [.12, 0, 0]
    foot_sequence = ReferenceSequence(np.arange(5)*.7, knots)
    offsets = [[0,0,0], [0,-.08,0], [.03,-.08,0], [.06,-.08,0], [.06,0,0]]
    pelvis = b.data.xpos[b.adapter.body_ids[0]].copy()
    quat = b.data.xquat[b.adapter.body_ids[0]].copy()
    pelvis_sequence = ReferenceSequence(np.arange(5)*.7, [
        FourPointPose(np.tile(pelvis+offset,(4,1)),np.tile(quat,(4,1))) for offset in offsets])
    body_ids = b.adapter.body_ids[b.four[2:]]
    times = np.arange(141)*.02
    positions, quaternions, errors, targets = [], [], [], []
    for t in times:
        desired = foot_sequence.pose_at(t)
        base = pelvis_sequence.pose_at(t)
        scratch.qpos[base_adr:base_adr+3] = base.positions[0]
        scratch.qpos[base_adr+3:base_adr+7] = base.quaternions[0]
        for iteration in range(80):
            mujoco.mj_forward(model, scratch)
            residual, jacobians = [], []
            for side, bid in enumerate(body_ids):
                pos_err = desired.positions[side+2]-scratch.xpos[bid]
                target_rot = Rotation.from_quat(desired.quaternions[side+2][[1,2,3,0]])
                current_rot = Rotation.from_matrix(scratch.xmat[bid].reshape(3,3))
                rot_err = (target_rot*current_rot.inv()).as_rotvec()
                jp, jr = np.zeros((3,model.nv)), np.zeros((3,model.nv))
                mujoco.mj_jacBody(model,scratch,jp,jr,int(bid))
                residual.extend([pos_err,rot_err*.2])
                jacobians.extend([jp[:,vadr],jr[:,vadr]*.2])
            error = np.concatenate(residual); J = np.concatenate(jacobians)
            if np.max(np.abs(error)) < 1e-6: break
            dq = np.linalg.solve(J.T@J+np.eye(len(qadr))*1e-6,J.T@error)
            dq *= min(1., .1/max(np.max(np.abs(dq)),1e-12))
            scratch.qpos[qadr] = np.clip(scratch.qpos[qadr]+dq, limits[:,0],limits[:,1])
        mujoco.mj_forward(model,scratch)
        errors.append(float(np.max(np.abs(error))))
        positions.append(scratch.xpos[b.adapter.body_ids].copy())
        quaternions.append(scratch.xquat[b.adapter.body_ids].copy())
        targets.append(scratch.qpos[b.adapter._policy_qpos_adr].copy())
    if max(errors) > .001:
        raise ValueError(f'IK reference invalid: max weighted residual {max(errors)}')
    return SimpleNamespace(num_frames=len(times),body_pos_w=np.array(positions,dtype=np.float32),
        body_quat_w=np.array(quaternions,dtype=np.float32),joint_targets=np.array(targets)), errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--direct-ik',action='store_true',help='Isolated actuation diagnostic bypassing model_38000; never a policy/task result')
    p.add_argument('--foot-residual',action='store_true',help='Diagnostic VR-5 plus bounded robot-only ankle pose correction, max 8Nm per leg joint')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    if args.direct_ik and args.foot_residual:p.error('Choose only one diagnostic override')
    results=[]
    modes=('direct-IK-PD',) if args.direct_ik else (('VR-5',) if args.foot_residual else ('UMI-4','VR-5','Full-14'))
    for mode in modes:
        folder=args.output/mode;folder.mkdir();b=video=None
        row={'mode':mode,'gpt_calls':0,'task_success_credit':False,'actor_access':False,
             'scope':'Robot geometry IK feasibility probe; no object state or demonstrated task motion'}
        try:
            b=create_closed_door_backend(seed=0,pd_profile='checkpoint',push_open=True)
            row['initial_state_sha256']=hashlib.sha256(b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest()
            motion,errors=build_reference(b)
            row['ik_max_weighted_residual']=max(errors)
            row['reference_sha256']=hashlib.sha256(motion.body_pos_w.tobytes()+motion.body_quat_w.tobytes()).hexdigest()
            row['bypass_network_for_actuation_diagnostic']=args.direct_ik
            row['foot_residual_torque_limit_nm']=8. if args.foot_residual else None
            np.savez(folder/'robot_reference.npz',body_pos_w=motion.body_pos_w,body_quat_w=motion.body_quat_w)
            if mode=='VR-5':b.adapter.mode[0,0]=1.
            if mode=='Full-14':b.adapter.mode[:]=1.
            b.adapter.mode_mapping=np.concatenate([
                *[np.repeat(b.adapter.mode[0],d) for d in (3,3,6,6)],np.ones(1,dtype=np.float32)
            ])[None].astype(np.float32)
            b.translation_limit_m_by_link={n:.3 for n in b.translation_limit_m_by_link}
            start=float(b.data.time)
            four=[FourPointPose(p[b.four],q[b.four]) for p,q in zip(motion.body_pos_w,motion.body_quat_w)]
            sequence=ReferenceSequence(start+np.arange(motion.num_frames)*.02,four)
            b.scene_setup['diagnostic_controller_override']=('direct IK, no network action inference' if args.direct_ik
                else ('VR-5 network plus ankle pose residual, max 8Nm per leg joint' if args.foot_residual else mode))
            video=simple_video(b,folder/'video',label=f'Robot IK/mask diagnostic {mode} | no task credit')
            residual_tau=np.zeros(29)
            last_target=np.zeros(29)
            original_trace=video.extra_trace
            def trace(backend):
                result=original_trace(backend)
                result['diagnostic_foot_residual_torque29_nm']=residual_tau.tolist()
                result['control_chain']['commanded_joint_target29_rad']=(last_target+b.wrist_pi_tau/b.kp).tolist()
                result['control_chain']['normalized_action_source']=('derived_IK_target' if args.direct_ik else 'network')
                return result
            video.extra_trace=trace
            obs=b.observe()
            b.move_four_points(obs['observation_id'],mode,four[-1].to_mapping(),2.8,
                              orientation_names=())
            old_infer=b.adapter.infer
            leg_idx=[i for i,n in enumerate(b.adapter.metadata['joint_names']) if any(s in n for s in ('hip_','knee_','ankle_'))]
            leg_vadr=b.adapter._policy_dof_adr[leg_idx]
            def infer(data, ignored, index):
                current=min(motion.num_frames-1,max(0,round((float(data.time)-start)/.02)))
                if args.direct_ik:
                    # Keep recording's normalized target field honest despite no inference.
                    a=b.adapter
                    a.action_history[0,-1]=(motion.joint_targets[current]-a._default_qpos_p)/a._action_scale_p
                    target=motion.joint_targets[current].copy()
                else:target=old_infer(data,motion,current)
                if args.foot_residual:
                    jacobians=[];residual=[]
                    for body_index in b.four[2:]:
                        bid=int(b.adapter.body_ids[body_index])
                        jp,jr=np.zeros((3,b.model.nv)),np.zeros((3,b.model.nv))
                        mujoco.mj_jacBody(b.model,data,jp,jr,bid)
                        goal_rot=Rotation.from_quat(motion.body_quat_w[current,body_index][[1,2,3,0]])
                        actual_rot=Rotation.from_matrix(data.xmat[bid].reshape(3,3))
                        residual.extend([motion.body_pos_w[current,body_index]-data.xpos[bid],
                                         .2*(goal_rot*actual_rot.inv()).as_rotvec()])
                        jacobians.extend([jp[:,leg_vadr],.2*jr[:,leg_vadr]])
                    J=np.concatenate(jacobians);error=np.concatenate(residual)
                    correction=np.linalg.solve(J.T@J+np.eye(len(leg_idx))*1e-4,J.T@error)
                    residual_tau[:]=0.
                    residual_tau[leg_idx]=np.clip(correction*b.kp[leg_idx],-8.,8.)
                    target=target+residual_tau/b.kp
                last_target[:]=target
                return target
            b.adapter.infer=infer;b.reference_pose_at=sequence.pose_at
            ankle_ids=b.adapter.body_ids[b.four[2:]]
            initial_z=b.data.xpos[ankle_ids,2].copy();peak=np.zeros(2)
            initial_pelvis=b.data.xpos[b.adapter.body_ids[0]].copy()
            feet=[]
            for bid in ankle_ids:
                descendants={int(bid)}
                for i in range(b.model.nbody):
                    if int(b.model.body_parentid[i]) in descendants:descendants.add(i)
                feet.append(set(np.flatnonzero(np.isin(b.model.geom_bodyid,list(descendants)))))
            plane=set(np.flatnonzero(b.model.geom_type==mujoco.mjtGeom.mjGEOM_PLANE))
            detached=[0,0];longest=[0,0]
            while b.active and not b.reason:
                b.tick();video.record_tick('diagnostic_only')
                peak=np.maximum(peak,b.data.xpos[ankle_ids,2]-initial_z)
                for side,geoms in enumerate(feet):
                    contact=any(((c.geom1 in geoms and c.geom2 in plane) or
                                 (c.geom2 in geoms and c.geom1 in plane)) and c.dist<=.0001 for c in b.data.contact)
                    detached[side]=0 if contact else detached[side]+1
                    longest[side]=max(longest[side],detached[side])
            row.update(sim_s=float(b.data.time)-start,stop_reason=b.reason,
                max_ankle_height_gain_m=peak.tolist(),max_no_plane_contact_s=(np.array(longest)*.02).tolist(),
                final_pelvis_delta_m=(b.data.xpos[b.adapter.body_ids[0]]-initial_pelvis).tolist(),
                final_ankle_delta_m=(b.data.xpos[ankle_ids]-four[0].positions[2:]).tolist())
        except Exception as exc:
            row['error']=f'{type(exc).__name__}: {exc}';traceback.print_exc()
        finally:
            if video:video.close()
            if b:b.close()
        (folder/'result.json').write_text(json.dumps(row,indent=2))
        results.append(row);(args.output/'summary.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(row),flush=True)


if __name__=='__main__':main()
