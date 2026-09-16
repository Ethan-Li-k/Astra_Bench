"""Compare named PD profiles on contact-free 25 mm perturbations, no GPT."""
import argparse
import copy
import json
from pathlib import Path
import random
import traceback
import hashlib
import mujoco
import numpy as np
from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import simple_video


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--feet', action='store_true', help='Independent 60/80 mm foot-only diagnostics')
    p.add_argument('--zero-body-friction', action='store_true', help='Isolated dynamics counterfactual only')
    p.add_argument('--grasp-scene', action='store_true', help='Compare prior robot asset with the same 5 ms physics step')
    p.add_argument('--duration', type=float, default=2., help='Single-factor waypoint timing diagnostic')
    p.add_argument('--case', help='Run one exact existing case key instead of the full set')
    p.add_argument('--foot-heights', type=float, nargs='+', default=(.06,.08),
                   help='Isolated amplitude probe only; formal actor limits are unchanged')
    p.add_argument('--side', choices=('left','right','both'), default='both')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);rows=[]
    cases=[('left_wrist_yaw_link',0,.025),('left_wrist_yaw_link',2,.025),
           ('right_wrist_yaw_link',0,.025),('left_ankle_roll_link',2,.025)]
    if args.feet:
        if any(not 0 < h <= .3 for h in args.foot_heights): p.error('Foot diagnostic height must be in (0, .3]')
        sides=('left','right') if args.side=='both' else (args.side,)
        cases=[(f'{side}_ankle_roll_link',2,delta) for side in sides for delta in args.foot_heights]
    for profile in (('checkpoint',) if args.feet else ('native','checkpoint')):
        for name,axis,delta in cases:
            key=f'{profile}-{name}-{axis}-{delta}'
            if args.case and args.case != key:continue
            folder=args.output/key;folder.mkdir()
            backend=video=None;row={'case':key,'duration_s':args.duration,'gpt_calls':0,'task_success_credit':False}
            try:
                random.seed(0);np.random.seed(0)
                if args.grasp_scene:
                    from rsi.live import LiveSim
                    backend=LiveSim(wrist_pi=True,physics_dt=.005)
                    for _ in range(250):backend.tick()
                else:
                    backend=create_closed_door_backend(seed=0,pd_profile=profile,
                        settle_ticks=0 if args.zero_body_friction else 250)
                if args.zero_body_friction:
                    adr=backend.adapter._policy_dof_adr
                    row['original_body_frictionloss']=backend.model.dof_frictionloss[adr].tolist()
                    backend.model.dof_frictionloss[adr]=0.
                    backend.scene_setup['counterfactual_body_frictionloss']=0.
                    for _ in range(250):backend.tick()
                row['initial_state_sha256']=hashlib.sha256(backend.data.qpos.tobytes()+backend.data.qvel.tobytes()).hexdigest()
                if args.feet:
                    backend.translation_limit_m_by_link[name]=max(.08, delta)
                label=f'ScaleBFM tracking probe | {profile} PD | no GPT'
                if args.grasp_scene:
                    from rsi.episode_video import EpisodeVideo
                    video=EpisodeVideo(backend,folder/'video',label=label)
                else:
                    video=simple_video(backend,folder/'video',label=label)
                obs=backend.observe();target=copy.deepcopy(obs['four_point_reference_world'])
                target[name]=copy.deepcopy(obs['four_point_world'][name]);target[name]['position_world_m'][axis]+=delta
                start=np.array(obs['four_point_world'][name]['position_world_m'])
                body_id=backend.model.body(name).id
                descendants={body_id}
                for i in range(backend.model.nbody):
                    if int(backend.model.body_parentid[i]) in descendants: descendants.add(i)
                geoms=set(np.flatnonzero(np.isin(backend.model.geom_bodyid,list(descendants))))
                planes=set(np.flatnonzero(backend.model.geom_type==mujoco.mjtGeom.mjGEOM_PLANE))
                peak_z=0.;detached=longest=0
                backend.move_four_points(obs['observation_id'],key,target,args.duration,
                    position_names=(name,),orientation_names=(name,))
                while backend.active and not backend.reason:
                    backend.tick();video.record_tick('diagnostic_only')
                    peak_z=max(peak_z,float(backend.data.xpos[body_id,2]-start[2]))
                    contact=any(((c.geom1 in geoms and c.geom2 in planes) or
                                 (c.geom2 in geoms and c.geom1 in planes)) and c.dist<=.0001
                                for c in backend.data.contact)
                    detached=0 if contact else detached+1;longest=max(longest,detached)
                end=np.array(backend.observe()['four_point_world'][name]['position_world_m'])
                row.update(status=backend.status(),stop_reason=backend.reason,
                    requested_delta_m=(np.eye(3)[axis]*delta).tolist(),actual_delta_m=(end-start).tolist(),
                    max_height_gain_m=peak_z,max_no_plane_contact_s=longest*.02,
                    translation_limits_m=backend.translation_limit_m_by_link,
                    policy_joint_names=backend.adapter.metadata['joint_names'],
                    kp=backend.kp.tolist(),kd=backend.kd.tolist(),
                    task_configuration=({'scene':'prior grasp asset; 5 ms physics'} if args.grasp_scene
                                        else backend.env.task.state_dict()))
            except Exception as exc:
                row['error']=f'{type(exc).__name__}: {exc}';traceback.print_exc()
            finally:
                if video:video.close()
                if backend and hasattr(backend, 'close'):backend.close()
            from simple.utils import NumpyArrayEncoder
            (folder/'result.json').write_text(json.dumps(row,indent=2,cls=NumpyArrayEncoder))
            brief={k:v for k,v in row.items() if k not in ('task_configuration','kp','kd','policy_joint_names')}
            rows.append(brief);(args.output/'summary.json').write_text(json.dumps(rows,indent=2))
            print(json.dumps(brief),flush=True)


if __name__=='__main__':main()
