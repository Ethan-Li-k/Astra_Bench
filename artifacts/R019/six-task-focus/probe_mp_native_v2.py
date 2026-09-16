"""Zero-policy native MP reset audit. No actor, AMO action, planner or task credit."""
from pathlib import Path
import hashlib,json,traceback,datetime
import numpy as np
import mujoco
from rsi.simple_environment import configure_offline_assets,load_hssd_metadata
from rsi.simple_sensors import install_pelvis_gyro
from rsi.simple_object_names import install_unique_object_labels
from rsi.scalebfm import METADATA
OUT=Path('artifacts/R019/six-task-focus/mp-native-probe-v2')
OUT.mkdir(parents=True,exist_ok=False)
configure_offline_assets()
from simple.scenes.hssd import HssdSceneManager
HssdSceneManager.load=load_hssd_metadata
import gymnasium as gym
import simple.envs
import simple.robots.g1_wholebody as legacy
class ForbiddenAMO:
    creations=0
    def __init__(self,*args,**kwargs):type(self).creations+=1
    def __getattr__(self,name):raise RuntimeError('Legacy AMO access forbidden: '+name)
legacy.AMO_Policy=ForbiddenAMO
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_access':False,'hypothesis':'Native MP task can reset without legacy policy and exposes a name-complete physical robot for an explicit ScaleBFM adapter.','criteria':'Both native resets, named joint/actuator mappings, mixed actuator coefficients, root/ground frame, camera and target force semantics recorded; no old policy access. Reset alone is not adapter validation.','physics_actions':0,'model_calls':0,'success_credit':0,'entries':[]}
for suffix in ('BendPickMP','TabletopGraspMP'):
    env=None;row={'env_id':'simple/G1Wholebody'+suffix+'-v0'}
    try:
        env=gym.make(row['env_id'],sim_mode='mujoco',headless=True,render_hz=50,physics_dt=.002)
        install_pelvis_gyro(env);install_unique_object_labels(env)
        env.reset(seed=1)
        run=env.unwrapped;engine=run.mujoco;m,d=engine.mjModel,engine.mjData
        names=json.loads(METADATA.read_text())['joint_names']
        row.update(status='native_reset_complete',native_reset_sim_s=float(d.time),robot_uid=engine.task.robot.uid,robot_asset=engine.task.robot.mjcf_path,physics_dt=float(m.opt.timestep),gravity=m.opt.gravity.tolist(),ground_z=float(m.geom_pos[m.geom('ground').id,2]),root_body_world=d.body('pelvis').xpos.tolist(),free_roots=[m.joint(i).name for i in range(m.njnt) if m.jnt_type[i]==mujoco.mjtJoint.mjJNT_FREE],cameras=[m.camera(i).name for i in range(m.ncam)],task_instance_shared=engine.task is run.task)
        row['body_joints']=[{'name':n,'qposadr':int(m.joint(n).qposadr[0]),'dofadr':int(m.joint(n).dofadr[0]),'actuator_id':int(m.actuator(n).id),'gainprm':m.actuator_gainprm[m.actuator(n).id].tolist(),'biasprm':m.actuator_biasprm[m.actuator(n).id].tolist(),'ctrllimited':bool(m.actuator_ctrllimited[m.actuator(n).id]),'ctrlrange':m.actuator_ctrlrange[m.actuator(n).id].tolist()} for n in names]
        row['objects_host_only']={k:{'position':v.xpos.tolist(),'applied_force':v.xfrc_applied.tolist()} for k,v in engine.mj_objects.items()}
        row['qpos_sha256']=hashlib.sha256(d.qpos.tobytes()).hexdigest()
        np.savez(OUT/(suffix+'-reset.npz'),qpos=d.qpos,qvel=d.qvel,ctrl=d.ctrl,xfrc_applied=d.xfrc_applied)
        (OUT/(suffix+'-compiled.xml')).write_text(engine.mjSpec.to_xml())
        row['actuator_semantics']={'position_servos':[r['name'] for r in row['body_joints'] if r['biasprm'][1]!=0],'torque_motors':[r['name'] for r in row['body_joints'] if r['biasprm'][1]==0]}
        row['existing_adapter_blockers']=['native root joint is pelvis, not floating_base_joint','ground below world zero: native root world height triggers current absolute safety cutoff','14 arm position actuators cannot accept torque as ctrl','native2ms step requires10 substeps per50Hz tracker command','legacy AMO must remain disabled; no privileged planner actions']
    except Exception as exc:
        row.update(status='failed',error=repr(exc),traceback=traceback.format_exc())
    finally:
        if env is not None:
            try:env.close()
            except Exception as exc:row['close_error']=repr(exc)
    report['entries'].append(row)
report['blocked_legacy_policy_constructions']=ForbiddenAMO.creations
(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='entries'}))
for row in report['entries']:print(json.dumps({k:v for k,v in row.items() if k not in ('body_joints','objects_host_only')}))
