"""Diagnostic only: preserve native MP geometry; test explicit ScaleBFM control adapter."""
from pathlib import Path
import json,random,traceback,datetime
import numpy as np
import mujoco
from PIL import Image
from rsi.simple_environment import configure_offline_assets,load_hssd_metadata
from rsi.simple_sensors import install_pelvis_gyro
from rsi.simple_object_names import install_unique_object_labels
from rsi.scalebfm import METADATA
from rsi.live import LiveSim
from rsi.episode_video import EpisodeVideo
OUT=Path('artifacts/R019/six-task-focus/mp-scalebfm-probe-01');OUT.mkdir(parents=True,exist_ok=False)
report={'actor_access':False,'classification':'adapter_diagnostic','hypothesis':'Original MP geometry can run model_38000 through named checkpoint PD after a rigid world-origin translation and explicit arm actuator conversion.','distinguishing_criteria':['Translation preserves every body/camera relative position and rotation, mass/inertia, native scene/table placement, and RGB projection.','Control uses four-point model_38000 only; old AMO raises on access.','Stationary5s and25mm robot-only wrist perturbation retain standing, finite states, exact20ms tracker increments; diagnostic success is not task credit.'],'model_calls':0,'task_success_credit':0,'env_id':'simple/G1WholebodyBendPickMP-v0','seed':1,'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
env=video=None
try:
    configure_offline_assets()
    from simple.scenes.hssd import HssdSceneManager
    HssdSceneManager.load=load_hssd_metadata
    import gymnasium as gym
    import simple.envs
    import simple.robots.g1_wholebody as legacy
    class ForbiddenAMO:
        def __init__(self,*args,**kwargs):pass
        def __getattr__(self,name):raise RuntimeError('Legacy policy forbidden: '+name)
    legacy.AMO_Policy=ForbiddenAMO
    random.seed(1);np.random.seed(1)
    env=gym.make(report['env_id'],sim_mode='mujoco',headless=True,render_hz=50,physics_dt=.002)
    install_pelvis_gyro(env);install_unique_object_labels(env);env.reset(seed=1)
    e=env.unwrapped.mujoco;m0,d0=e.mjModel,e.mjData
    offset=-float(m0.geom_pos[m0.geom('ground').id,2]);translation=np.array([0.,0.,offset])
    spec=mujoco.MjSpec();spec.option=e.mjSpec.option
    spec.attach(e.mjSpec.copy(),frame=spec.worldbody.add_frame(pos=translation))
    model=spec.compile();data=mujoco.MjData(model)
    assert [model.joint(i).name for i in range(model.njnt)]==[m0.joint(i).name for i in range(m0.njnt)]
    data.qpos[:]=d0.qpos;data.qvel[:]=d0.qvel;data.ctrl[:]=d0.ctrl;data.xfrc_applied[:]=d0.xfrc_applied
    for j in range(model.njnt):
        if model.jnt_type[j]==mujoco.mjtJoint.mjJNT_FREE:data.qpos[model.jnt_qposadr[j]:model.jnt_qposadr[j]+3]+=translation
    data.time=d0.time;mujoco.mj_forward(model,data);mujoco.mj_forward(m0,d0)
    checks={'body_translation_max_error_m':float(np.max(np.abs(data.xpos[1:]-d0.xpos[1:]-translation))),
        'camera_translation_max_error_m':float(np.max(np.abs(data.cam_xpos-d0.cam_xpos-translation))),
        'body_rotation_max_error':float(np.max(np.abs(data.xmat-d0.xmat))),
        'camera_rotation_max_error':float(np.max(np.abs(data.cam_xmat-d0.cam_xmat))),
        'body_mass_max_difference':float(np.max(np.abs(model.body_mass-m0.body_mass))),
        'body_inertia_max_difference':float(np.max(np.abs(model.body_inertia-m0.body_inertia)))}
    assert max(checks.values())<1e-10,checks
    before=mujoco.Renderer(m0,height=360,width=640);after=mujoco.Renderer(model,height=360,width=640)
    before.update_scene(d0,camera='head_stereo_left');after.update_scene(data,camera='head_stereo_left')
    rgb0=before.render();rgb1=after.render();Image.fromarray(rgb0).save(OUT/'native.png');Image.fromarray(rgb1).save(OUT/'translated.png')
    checks['render_mean_absolute_difference']=float(np.abs(rgb0.astype(float)-rgb1).mean());checks['render_max_difference']=int(np.abs(rgb0.astype(int)-rgb1).max());before.close();after.close()
    report.update(translation_z_m=offset,geometry_equivalence=checks)
    metadata=json.loads(METADATA.read_text());converted=[]
    for name in metadata['joint_names']:
        a=model.actuator(name).id;j=model.joint(name)
        if model.actuator_biasprm[a,1]!=0:converted.append(name)
        assert model.actuator_gear[a,0]==1
        model.actuator_gainprm[a]=0;model.actuator_gainprm[a,0]=1
        model.actuator_biasprm[a]=0;model.actuator_biastype[a]=mujoco.mjtBias.mjBIAS_NONE
        model.actuator_ctrllimited[a]=1;model.actuator_ctrlrange[a]=model.jnt_actfrcrange[j.id]
    report['arm_position_servos_explicitly_converted']=converted
    for name,value in zip(metadata['joint_names'],metadata['default_dof_pos']):data.qpos[model.joint(name).qposadr[0]]=value
    root=model.joint('pelvis');assert root.qposadr[0]==0
    data.qpos[2]=.755;data.qvel[:]=0;data.ctrl[:]=0;mujoco.mj_forward(model,data)
    sim=LiveSim(model=model,data=data,physics_dt=.002,wrist_pi=True,workspace_radius_m=2.)
    camera=mujoco.MjvCamera();mujoco.mjv_defaultFreeCamera(model,camera);camera.lookat[:]=data.body('pelvis').xpos;camera.distance=3.;camera.azimuth=120;camera.elevation=-20
    video=EpisodeVideo(sim,OUT/'video',label='MP ScaleBFM adapter diagnostic | no actor/task credit',cameras=('head_stereo_left','head_stereo_right'),video_cameras=(camera,'head_stereo_left'),height=360)
    times=[];heights=[];tilts=[]
    def tick():
        t=data.time;sim.tick();times.append(float(data.time-t));heights.append(float(data.qpos[2]));tilts.append(float(np.degrees(np.arccos(np.clip(data.xmat[sim.adapter.body_ids[0]].reshape(3,3)[2,2],-1,1)))));video.record_tick('diagnostic')
    for _ in range(250):
        tick()
        if sim.reason:break
    report['standing5s']={'ticks':len(times),'reason':sim.reason,'min_height_m':min(heights),'max_tilt_deg':max(tilts),'mean_dt':float(np.mean(times))}
    if not sim.reason:
        start=sim.data.xpos[sim.adapter.body_ids[sim.wrist]].copy()
        obs=sim.observe();target=sim.reference_pose_at(data.time).copy();target.positions[sim.right_four]=start+np.array([.025,0,0]);sim.move_four_point(obs['observation_id'],'diagnostic-wrist25mm',target.to_mapping(),duration=1.,position_names=('right_wrist_yaw_link',),orientation_names=())
        for _ in range(150):
            tick()
            if sim.reason:break
        report['wrist25mm']={'measured_delta_m':(sim.data.xpos[sim.adapter.body_ids[sim.wrist]]-start).tolist(),'reason':sim.reason}
    report.update(status='diagnostic_complete',simulation_s=float(data.time),min_height_m=min(heights),max_tilt_deg=max(tilts),dt_max_error=float(np.max(np.abs(np.array(times)-.02))))
except Exception as exc:report.update(status='diagnostic_error',error=repr(exc),traceback=traceback.format_exc())
finally:
    if video is not None:
        try:video.close()
        except Exception as exc:report['video_close_error']=repr(exc)
    if env is not None:
        try:env.close()
        except Exception as exc:report['env_close_error']=repr(exc)
(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
