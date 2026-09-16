"""H001: one fresh SIMPLE reset, original actions only, no actor or campaign."""
import os
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / 'artifacts/R019/apple-campaign/episode-0003'
HOST = OUT / 'host_audit'
ATTEMPT_NAME = sys.argv[1] if len(sys.argv)>1 else 'attempt-002'
assert ATTEMPT_NAME in ('attempt-002',)
ATTEMPT = OUT / ATTEMPT_NAME
AUDIT = HOST / ATTEMPT_NAME
for path in (ATTEMPT, AUDIT, OUT/'tmp', OUT/'cache'):
    path.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
sys.path.insert(0, str(HOST/'runtime'))
os.environ.update(TMPDIR=str(OUT/'tmp'), XDG_CACHE_HOME=str(OUT/'cache'),
                  MPLCONFIGDIR=str(OUT/'cache/matplotlib'), MUJOCO_GL='egl',
                  HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  PYTHONDONTWRITEBYTECODE='1')

# Guard Python file mutations. Native libraries also receive local cache/tmp paths.
read_paths = set()
def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).absolute()
        mode, flags = args[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and path != Path('/dev/null') and OUT not in path.resolve().parents:
            raise PermissionError('H001 sole write root violation: '+str(path))
        if not writing:
            if path.name in ('api.json', 'auth.json', 'credentials', 'credentials.json'):
                raise PermissionError('H001 credentials access forbidden')
            read_paths.add(str(path))
    if event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'):
        for value in args[:2] if event == 'os.rename' else args[:1]:
            if isinstance(value, (str, bytes)):
                path = Path(os.fsdecode(value)).resolve()
                if path != OUT and OUT not in path.parents:
                    raise PermissionError('H001 sole mutation root violation: '+str(path))
sys.addaudithook(guard)

import datetime
import hashlib
import json
import time
import traceback
import importlib.metadata
import numpy as np
import mujoco
from PIL import Image
from rsi.tool_host import LocoManipToolHost
from rsi.simple_live import SimpleLiveSim
from rsi.simple_recording import simple_video, named_render_state
from rsi.simple_hand_geometry import finger_geometry
from rsi.evaluator import SimpleNativeEvaluator
from rsi.scalebfm import MODEL, MODEL_SHA256, METADATA
import rsi.simple_environment as environment

environment.ROOT = ROOT  # Only path routing; assets are read-only.
THRESHOLDS = json.loads((OUT/'thresholds.json').read_text())
threshold_sha = hashlib.sha256((OUT/'thresholds.json').read_bytes()).hexdigest()
KEYS = (0, 1, 10, 30, 50, 57, 58, 59, 60, 61, 62, 63, 64, 65)
base_status = dict(reproduction_only=True, task_success_credit=False, backend='SIMPLE MuJoCo',
                   model='gpt-6-astra', effort='xhigh', account_route='existing_second_account_session',
                   gpt_actor_calls=0, paid_api_calls=0, human_feedback_used_in_baseline=False,
                   human_demonstration_used=False, threshold_sha256=threshold_sha)

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    def default(obj):
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, np.generic): return obj.item()
        if isinstance(obj, Path): return str(obj)
        raise TypeError(type(obj).__name__)
    path.write_text(json.dumps(value, indent=2, default=default))

def status(phase, **kw):
    row = dict(base_status, phase=phase, updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **kw)
    dump(OUT/'status.json', row)
    print(json.dumps(row), flush=True)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def angle(a, b):
    a=np.asarray(a); b=np.asarray(b)
    # atan2 is stable near identical quaternions; handle equivalent signs.
    a=a/np.linalg.norm(a); b=b/np.linalg.norm(b)
    if np.dot(a,b)<0: b=-b
    return float(4*np.arctan2(np.linalg.norm(a-b),np.linalg.norm(a+b)))

class Auditor:
    def __init__(self):
        self.original=(SOURCE/'video/robot_trace.jsonl').open()
        self.diff=(AUDIT/'trajectory_comparison.jsonl').open('w', buffering=1)
        self.physics=(AUDIT/'physics_history.jsonl').open('w', buffering=1)
        self.index=0; self.action=0; self.first=None; self.maxima={}; self.tick_count=0
        self.inputs=[]; self.pre_policy=[]; self.pre_action=[]; self.input_times=[]
        self.boundaries=[]; self.settle=[]

    def wrap_tracker(self, backend):
        original=backend.adapter._run_policy
        def tracked(task):
            self.inputs.append(task.copy())
            self.pre_policy.append(backend.adapter.policy_history.copy())
            self.pre_action.append(backend.adapter.action_history.copy())
            self.input_times.append(float(backend.data.time))
            return original(task)
        backend.adapter._run_policy=tracked

    def compare_tick(self, b):
        line=self.original.readline()
        if not line: raise RuntimeError('Original trace ended before replay')
        old=json.loads(line); new=named_render_state(b)
        old_q=old['host_render_state']['qpos_by_joint']; new_q=new['qpos_by_joint']
        if old_q.keys()!=new_q.keys(): raise RuntimeError('Named joint set differs')
        scalar=[]; free=[]; rotations=[]; by_name={}
        for name, q in new_q.items():
            delta=np.asarray(q)-np.asarray(old_q[name])
            if len(q)==7:
                p=float(np.linalg.norm(delta[:3])); r=angle(q[3:],old_q[name][3:]); free.append(p);rotations.append(r)
                by_name[name]={'position_m':p,'orientation_rad':r}
            else:
                d=float(np.max(np.abs(delta)));scalar.append(d);by_name[name]={'angle_rad':d}
        old_control=old['host_render_state']['control_chain']
        raw=b.adapter.action_history[0,-1]
        target=raw*b.adapter._action_scale_p+b.adapter._default_qpos_p+b.wrist_pi_tau/b.kp
        metrics={'sim_time_s':abs(float(b.data.time)-old['sim_s']),
            'four_point_position_m':float(np.linalg.norm(b.data.xpos[b.adapter.body_ids[b.four]]-np.asarray(old['measured_four_point_position_world_m']),axis=1).max()),
            'free_joint_position_m':max(free),'free_joint_orientation_rad':max(rotations),
            'joint_angle_rad':max(scalar),'normalized_action_max_abs':float(np.max(np.abs(raw-np.asarray(old_control['normalized_action29'])))),
            'commanded_joint_target_rad':float(np.max(np.abs(target-np.asarray(old_control['commanded_joint_target29_rad'])))),
            'wrist_pi_torque_nm':float(np.max(np.abs(b.wrist_pi_tau-np.asarray(old_control['wrist_pi_torque29_nm']))))}
        limits=THRESHOLDS['initial' if self.index==0 else 'trajectory']
        exceeded={k:{'value':v,'limit':limits[k]} for k,v in metrics.items() if k in limits and v>limits[k]}
        if b.status().get('command_id') != old['status'].get('command_id'):
            exceeded['command_id']={'new':b.status().get('command_id'),'old':old['status'].get('command_id')}
        if b.status()['status'] != old['status']['status']:
            exceeded['execution_status']={'new':b.status()['status'],'old':old['status']['status']}
        row={'sample_index':self.index,'action':self.action,'sim_s':float(b.data.time),'original_sim_s':old['sim_s'],
             'metrics':metrics,'exceeded':exceeded,'joint_differences_by_name':by_name}
        self.diff.write(json.dumps(row)+'\n')
        for key,value in metrics.items():self.maxima[key]=max(self.maxima.get(key,0),value)
        if exceeded and self.first is None:
            self.first=row;dump(AUDIT/'first_divergence.json',row)
            status('executing_diverged_compatibility_diagnostic', action=self.action,
                   same_condition_claim_allowed=False, earliest_divergence_sample=self.index)
        ends=list(b.model.jnt_dofadr[1:])+[b.model.nv]
        vel={b.model.joint(i).name:b.data.qvel[start:end].tolist() for i,(start,end) in enumerate(zip(b.model.jnt_dofadr,ends))}
        self.physics.write(json.dumps({'action':self.action,'sample_index':self.index,'sim_s':float(b.data.time),
            'qpos_by_joint':new_q,'qvel_by_joint':vel,'qacc_warmstart':b.data.qacc_warmstart.tolist(),
            'wrist_pi_e_int':b.wrist_pi.e_int.tolist(),'wrist_pi_tau':b.wrist_pi_tau.tolist(),
            'ctrl':b.data.ctrl.tolist(),'native_success':b._native_task_success,
            'native_reward':b._native_task_reward})+'\n')
        self.index+=1

    def checkpoint(self,b,step):
        flag=mujoco.mjtState.mjSTATE_INTEGRATION
        state=np.zeros(mujoco.mj_stateSize(b.model,flag));mujoco.mj_getState(b.model,b.data,state,flag)
        np.savez_compressed(AUDIT/f'checkpoints/action-{step:04d}.npz',integration_state=state,
            integration_flag=int(flag),policy_history=b.adapter.policy_history,action_history=b.adapter.action_history,
            wrist_pi_e_int=b.wrist_pi.e_int,wrist_pi_tau=b.wrist_pi_tau,
            reference_pos=b._reference_pose.positions,reference_quat=b._reference_pose.quaternions,
            start_pos=b._start_pose.positions,start_quat=b._start_pose.quaternions,
            goal_pos=b._goal_pose.positions,goal_quat=b._goal_pose.quaternions,
            qpos=b.data.qpos,qvel=b.data.qvel)
        dump(AUDIT/f'checkpoints/action-{step:04d}.json',{'step':step,'sim_s':float(b.data.time),
             'grips':b.grips,'grip_start':b.grip_start,'grip_t0':b.grip_t0,'grip_duration':b.grip_duration,
             'reference_t0':b.t0,'reference_duration':b.duration,'active':b.active,
             'status':b.status(),'state_scope':'MuJoCo integration + tracker/PI/reference; not a full serialized Python runtime',
             'task_attributes':{k:v for k,v in vars(b.env.task).items() if isinstance(v,(str,int,float,bool,type(None)))}})

    def finish(self):
        for f in (self.original,self.diff,self.physics):f.close()
        np.savez_compressed(AUDIT/'tracker_history.npz',sim_s=np.asarray(self.input_times),
            policy_task=np.asarray(self.inputs),policy_history_pre=np.asarray(self.pre_policy),
            action_history_pre=np.asarray(self.pre_action))
        dump(AUDIT/'trajectory_summary.json',{'samples':self.index,'tracker_calls_including_settle':len(self.inputs),
             'threshold_sha256':threshold_sha,'first_divergence':self.first,'maxima':self.maxima,
             'original_full_tracker_history_available':False,'boundaries':self.boundaries})

def main():
    status('initializing', actual_command='bash run_physics.sh', same_condition_claim_allowed=False)
    audit=Auditor();host=None;error=None;actions_done=0
    (AUDIT/'checkpoints').mkdir(exist_ok=True)
    actions=json.loads((OUT/'source_commands/actions.json').read_text())
    original_manifest=json.loads((SOURCE/'video/render_manifest.json').read_text())
    dump(AUDIT/'preflight.json',dict(base_status, env_id='simple/G1WholebodyPickAndPlaceAppleTeleop-v0',seed=3,
        interpreter=sys.executable,model_sha256=sha(MODEL),metadata_sha256=sha(METADATA),
        versions={name:importlib.metadata.version(name) for name in ['mujoco','numpy','onnxruntime','gymnasium']},
        runtime_source_sha256={str(p.relative_to(HOST/'runtime')):sha(p) for p in (HOST/'runtime').rglob('*.py')},
        original_versions_not_recorded=True, original_asset_hashes_not_recorded=True,
        initial_restore='fresh native reset seed=3 + checkpoint posture + 250 tracker ticks; never a frame teleport',
        physics_dt_s=.005,tracker_dt_s=.02,inference_wait='no GPT inference',
        action_timeout='original duration + 2s',physical_episode_budget_s=240,
        stop_after_action=65,wall_time_is_not_physics_time=True))
    assert sha(MODEL)==MODEL_SHA256
    original_init=SimpleLiveSim.__init__
    def instrument_init(self,*args,**kwargs):
        original_init(self,*args,**kwargs);audit.wrap_tracker(self)
        dump(AUDIT/'reset_pre_settle.json',{'named_state':named_render_state(self),'qvel':self.data.qvel,
            'ctrl':self.data.ctrl,'qfrc_applied':self.data.qfrc_applied,'xfrc_applied':self.data.xfrc_applied,
            'joint_names_policy_order':self.adapter.metadata['joint_names'],
            'joint_names_simple_body_order':self.bridge.body_names,'policy_to_body':self.bridge.body_from_policy,
            'hand_names_simple_order':self.bridge.hand_names,'kp':self.kp,'kd':self.kd,'limits':self.limits,
            'closed_finger_targets':dict(zip(self.fingers,self.closed)),
            'future_idx':getattr(self.adapter,'future_idx',None),
            'wrist_pi_parameters':{k:getattr(self.wrist_pi,k) for k in ['ki','kp','lam','e_max','r_max','W']}})
    SimpleLiveSim.__init__=instrument_init
    def factory():
        b=environment.create_native_task_backend('simple/G1WholebodyPickAndPlaceAppleTeleop-v0',seed=3,settle_ticks=250)
        current_config=b.env.task.state_dict()
        from simple.utils import NumpyArrayEncoder
        current_config=json.loads(json.dumps(current_config,cls=NumpyArrayEncoder))
        dump(AUDIT/'reset_comparison.json',{'environment_config_exactly_equal':current_config==original_manifest['environment_config'],
            'sonic_config_exactly_equal':json.loads(json.dumps(b.env.sonic_config,cls=NumpyArrayEncoder))==original_manifest['sonic_config'],
            'policy_joint_order_exactly_equal':b.adapter.metadata['joint_names']==original_manifest['control_chain_joint_names'],
            'current_environment_config':current_config,'original_environment_config':original_manifest['environment_config'],
            'original_init_state':original_manifest['initial_render_state'],'new_init_state':named_render_state(b),
            'original_complete_state_available':False,'new_reset_provenance':b.scene_setup.get('reset_provenance')})
        mujoco.mj_saveModel(b.model,str(AUDIT/'model.mjb'))
        dump(AUDIT/'model_export.json',{'format':'compiled MuJoCo MJB','xml_export':'not available for MjSpec-built model; attempt-001 error preserved'})
        return b
    def capture_factory(b):
        cap=simple_video(b,AUDIT/'video',label='H001 OLD ACTIONS | PHYSICS REPRODUCTION ONLY | ZERO TASK CREDIT')
        audit.compare_tick(b)  # Same t=5.005 initial sample as original recorder.
        native_record=cap.record_tick
        def record(outcome):
            native_record(outcome);audit.compare_tick(b)
        cap.record_tick=record
        return cap
    try:
        host=LocoManipToolHost(ATTEMPT/'rollout',factory,evaluator_factory=SimpleNativeEvaluator,
                              image_capture_factory=capture_factory)
        task=json.loads((OUT/'source_commands/loco_start.json').read_text())['task']
        packet=host.dispatch('loco_start',{'task':task,'output_dir':str(ATTEMPT/'rollout/episode')})
        if host.initialization_error:raise RuntimeError(str(host.initialization_error))
        def boundary(step,packet):
            b=host.backend
            observation=packet['observation'];observation['finger_geometry']=finger_geometry(b)
            dump(Path(packet['observation_path']),observation)
            old=json.loads((SOURCE/f'rollout/episode/observations/{step:04d}/observation.json').read_text())
            row={'action':step,'sim_s':float(b.data.time),'original_sim_s':old['sim_s'],
                 'new_native_outcome':packet['native_outcome'],'new_status':b.status()['status'],
                 'commanded_right_closure':b.gripper_command_at(b.data.time)['right'],
                 'new_wrist':observation['wrist_world_m'],'old_wrist':old['wrist_world_m'],
                 'named_state':named_render_state(b),'images':[]}
            if step in KEYS:
                audit.checkpoint(b,step)
                for camera in ('head_stereo_left','head_stereo_right'):
                    old_path=SOURCE/f'rollout/episode/observations/{step:04d}/{camera}.png'
                    new_path=Path(packet['observation_path']).parent/f'{camera}.png'
                    a=np.asarray(Image.open(old_path),dtype=np.int16);n=np.asarray(Image.open(new_path),dtype=np.int16)
                    diff=np.abs(a-n)
                    row['images'].append({'camera':camera,'source':str(old_path),'new':str(new_path),
                        'old_sha256':sha(old_path),'new_sha256':sha(new_path),
                        'mean_absolute_rgb_0_255':float(diff.mean()),
                        'fraction_pixels_channel_difference_gt_10':float((diff.max(axis=-1)>10).mean())})
            audit.boundaries.append(row);dump(AUDIT/'boundaries.json',audit.boundaries)
        boundary(0,packet)
        for action in actions:
            audit.action=action['action']
            packet=host.dispatch('scalebfm_act',{'observation_path':str(host.harness.latest_path),
                'response':action['response'],'output_dir':str(ATTEMPT/f'rollout/action-{audit.action:04d}')})
            actions_done=audit.action;boundary(actions_done,packet)
            dump(ATTEMPT/f'action-{actions_done:04d}-receipt.json',dict(base_status,action=actions_done,
                source_rpc=action['rpc'],source_request_sha256=action['request_sha256'],
                execution=packet['execution'],observation_path=packet['observation_path'],native_outcome=packet['native_outcome']))
            status('executing' if audit.first is None else 'executing_diverged_compatibility_diagnostic',
                   action=actions_done,sim_s=float(host.backend.data.time),same_condition_claim_allowed=False,
                   observed_prefix_within_thresholds=audit.first is None)
            if host.backend.reason:raise RuntimeError('Physical runtime stop: '+host.backend.reason)
            if host.backend.data.time-audit.boundaries[0]['sim_s']>240:raise RuntimeError('Physical budget exceeded')
        status('physics_complete_analysis_pending',actions_completed=actions_done,
            observed_prefix_within_thresholds=audit.first is None,same_condition_claim_allowed=False)
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}';traceback.print_exc()
        status('attempt_error_analysis_pending',actions_completed=actions_done,error=error)
    finally:
        if host:
            try:host.close()
            except Exception as exc:
                error=(error or '')+' close: '+repr(exc);traceback.print_exc()
        audit.finish()
        imports={}
        for name,module in list(sys.modules.items()):
            file=getattr(module,'__file__',None)
            if file and Path(file).is_file() and any(name==prefix or name.startswith(prefix+'.') for prefix in ('rsi','simple','locomanip','gear_sonic')):
                imports[name]={'path':file,'sha256':sha(file)}
        dump(AUDIT/'imported_sources.json',imports)
        asset_paths=[]
        for path in sorted(read_paths):
            p=Path(path)
            if p.is_file() and any(str(parent) in path for parent in (ROOT/'data/simple',Path('/home/galbot/Downloads/model_38000'),Path('/home/galbot/lizekai/APA/N_TRACK_ASSETS'))):
                asset_paths.append({'path':path,'sha256':sha(path),'bytes':p.stat().st_size})
        dump(AUDIT/'asset_reads.json',{'python_open_assets':asset_paths,'note':'C-library file reads may be absent; compiled model preserved; original asset hashes unavailable'})
        dump(ATTEMPT/'result.json',dict(base_status,actions_completed=actions_done,error=error,
            recorded_samples=audit.index,observed_prefix_within_thresholds=audit.first is None,
            first_divergence_file=str(AUDIT/'first_divergence.json') if audit.first else None,
            video=str(AUDIT/'video/episode.mp4'),same_condition_claim_allowed=False,
            original_complete_state_available=False))
    return 1 if error else 0

if __name__=='__main__':sys.exit(main())
