"""Exact Variant1 native-AMO learning glue and host-only retained-grasp gate."""
from pathlib import Path
import hashlib, importlib.util, json
import numpy as np
from rsi.simple_handover import SimpleHandoverEvaluator

ROOT = Path('/home/galbot/lizekai/RSI')
ENV = 'simple/G1WholebodyTabletopGraspVariant1MP-v0'
UID = 'g1_wholebody_tabletop_grasp_variant1_mp'
CONTROLLER = 'native-mp-amo15-arm-ik-stationary-v1'
HOST = ROOT/'artifacts/native-amo-wrist-control-v5/host.py'
PREPARATION = ROOT/'artifacts/parallel-harness-20260917/next-easy/clearance_preparation.py'
CONTRACT = dict(id='tabletop-variant1-retained-clear-lift-v1', scope=ENV,
    native_reward_unchanged=True, native_trigger_alone_terminates=False,
    full_object_clearance_m=.001, final_origin_rise_m=.018, independent_hold_s=.5,
    hold_translation_m=.01, hold_rotation_rad=float(np.deg2rad(5)),
    separate_action_required=True, final_geometry_audit_required=True,
    unmodified_native_benchmark=False)
TASK = ('Grasp the specified apple on the native tabletop with one hand, lift the whole object clear '
        'of support and retain it during a separately commanded stationary hold. Use only current '
        'RGB and named robot feedback. Native AMO owns legs/waist; only wrists and grippers are '
        'commandable. scalebfm_act is a compatibility tool name; no ScaleBFM or native expert planner runs.')

def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def native_host():
    return load_module('variant1_native_learning_host',HOST).NativeLearningHost


class NativeActorCapture:
    """Attest the actual calibrated capture against the same live robot sample."""
    def __init__(self, video, episode):
        self.video=video;self.episode=str(Path(episode).resolve())
    def __call__(self, directory):
        b=self.video.backend;packet=b.observations[next(reversed(b.observations))]
        time=float(b.data.time)
        if packet['sim_s']!=time:raise ValueError('Capture observation is stale')
        images=self.video(directory)
        if float(b.data.time)!=time:raise ValueError('Physics advanced during capture')
        for image in images:
            if image['sim_exposure_s']!=time:raise ValueError('Camera exposure state differs')
            image['capture_binding']=dict(episode_id=self.episode,
                reset_id=b.scene_setup['reset_provenance']['reset_id'],
                state_id=packet['observation_id'],sim_s=time,camera=image['camera'])
        return images
    def record_tick(self, outcome):self.video.record_tick(outcome)
    def close(self):self.video.close()


class RetainedGraspEvaluator(SimpleHandoverEvaluator):
    """Reuse exact target mesh/contact sampler; never export its raw samples."""
    def __init__(self):
        self.env_id=ENV;self.task_uid=UID;self.completion_contract=CONTRACT

    def reset(self, backend):
        super().reset(backend)
        self.reset_history(self._reset_id)

    def reset_history(self, reset_id):
        """Same pure temporal state for online gate and offline host-trace audit."""
        self._reset_id=reset_id;self._outcome='in_progress';self._last_sample=None
        self._last_time=None;self._native_seen=False;self._native_first_sim_s=None;self._host_error=None
        self._acquire_action=None;self._acquire_side=None
        self._hold_action=None;self._hold_since=None
        self._hold_position=self._hold_quaternion=None

    def sample(self, backend):
        s=super().sample(backend)
        command=backend.status()
        identity=command.get('command_id')
        # Harness command suffix denotes a knot. Distinct knots are not distinct actions.
        action=identity.rsplit(':',1)[0] if isinstance(identity,str) and ':' in identity else identity
        s.update(action_id=action,
            stationary_command=(command.get('command_kind')=='gripper_only'
                and command.get('active_position_links')==[] and command.get('active_orientation_links')==[]),
            command_complete=command.get('status')=='gripper_duration_elapsed')
        return s

    def update_sample(self, s, reason=None):
        self._last_sample=dict(s)
        if reason or self._host_error:
            self._outcome='failure';return
        now=float(s['time']);pos=np.asarray(s['target_position_m'],dtype=float)
        quat=np.asarray(s['target_quaternion_wxyz'],dtype=float)
        if (pos.shape!=(3,) or quat.shape!=(4,) or not np.isfinite([now,s['rise_m'],s['bottom_clearance_m'],*pos,*quat]).all()
                or abs(np.linalg.norm(quat)-1)>.01 or (self._last_time is not None and now<self._last_time)):
            self._host_error='invalid_or_regressed_host_sample';self._outcome='failure';return
        self._last_time=now
        if s['native_success']:
            if not self._native_seen:self._native_first_sim_s=now
            self._native_seen=True
        sides=set(s['grasped_sides']);touch=set(s['touching_hands'])
        held=(len(sides)==1 and sides<= {'left','right'} and touch==sides
            and not s['nonhand_support'] and s['rise_m']>=CONTRACT['final_origin_rise_m']
            and s['bottom_clearance_m']>CONTRACT['full_object_clearance_m'])
        action=s.get('action_id');side=next(iter(sides)) if held else None
        if not held or not isinstance(action,str) or not action:
            self._acquire_action=self._acquire_side=None
            self._hold_action=self._hold_since=None;self._outcome='in_progress';return
        if self._acquire_side!=side:
            self._acquire_action=action;self._acquire_side=side
            self._hold_action=self._hold_since=None
        hold=(action!=self._acquire_action and s.get('stationary_command') is True)
        if not hold:
            self._hold_action=self._hold_since=None;self._outcome='in_progress';return
        stable=(self._hold_position is not None and np.linalg.norm(pos-self._hold_position)<=CONTRACT['hold_translation_m']
            and 2*np.arccos(np.clip(abs(float(quat@self._hold_quaternion)),0,1))<=CONTRACT['hold_rotation_rad'])
        if self._hold_action!=action or self._hold_since is None or not stable:
            self._hold_action=action;self._hold_since=now
            self._hold_position=pos.copy();self._hold_quaternion=quat.copy()
        # No sticky success before final action ACK; loss on a later sample revokes it.
        self._outcome=('success' if self._native_seen and now-self._hold_since>=CONTRACT['independent_hold_s']
            and s.get('command_complete') is True else 'in_progress')

    def host_audit_state(self):
        return dict(contract=CONTRACT['id'],sample=self._last_sample,
            native_milestone_seen=self._native_seen,native_first_sim_s=self._native_first_sim_s,
            acquire_action=self._acquire_action,acquire_side=self._acquire_side,
            hold_action=self._hold_action,hold_since=self._hold_since,
            outcome=self._outcome,error=self._host_error,reset_id=self._reset_id)


def initialize_variant(backend, output, seed, recorder):
    """Same preflight02 clearance/standing, recorded before any control tick; no probe."""
    from rsi.simulation_provenance import reset_provenance
    from rsi.simple_recording import external_robot_contacts,named_render_state
    b=backend;output=Path(output)
    if (b.env.task.uid!=UID or b.env.task.dr_cfgs['target'].asset_id!='graspnet1b:12'
            or b.robot.uid!='g1_wholebody' or b.control_configuration['controller']!=CONTROLLER
            or b.env.spec.max_episode_steps is not None):
        raise ValueError('Exact Variant1 native reset/control mismatch')
    b.scene_setup.update(env_id=ENV,seed=seed,completion_contract=CONTRACT,
        reset_provenance=reset_provenance(b,seed),initial_state_modified=False,
        initialization='Recorded robot-only30mm clearance then8s standing; not task credit')
    b.state_hash=lambda:hashlib.sha256(b''.join(v.tobytes() for v in (b.data.qpos,b.data.qvel,b.data.ctrl))).hexdigest()
    video=None
    try:
        video=recorder(b,output/'video');b._reset_video=video
        (output/'initial-reset-host-only.json').write_text(json.dumps(named_render_state(b)))
        with (output/'initialization-host-only.jsonl').open('x') as stream:
            def record(phase):
                root=b.data.body('pelvis');q=root.xquat;w,x,y,z=q
                contacts=external_robot_contacts(b.model,b.data)
                row=dict(phase=phase,sim_s=float(b.data.time),reset_id=b.scene_setup['reset_provenance']['reset_id'],
                    root=root.xpos.tolist(),yaw_rad=float(np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))),
                    tilt_deg=float(np.degrees(np.arccos(np.clip(root.xmat.reshape(3,3)[2,2],-1,1)))),
                    height_above_floor_m=float(root.xpos[2]-b.ground),contacts_host_only=contacts)
                stream.write(json.dumps(row)+'\n');stream.flush();video.record_tick('initialization')
                if contacts or b.reason or row['tilt_deg']>25 or row['height_above_floor_m']<.55:
                    raise RuntimeError('Variant1 initialization contact/stability gate')
                return row
            record('reset')
            prep=load_module('variant1_clearance_preparation',PREPARATION)
            initial,goals,proposals=prep.prepare_targets(b)
            (output/'initialization-robot-only-proposals.json').write_text(json.dumps(proposals))
            for i in range(1,51):prep.apply_ramp(b,initial,goals,i);b.tick();last=record('clearance')
            origin=np.asarray(last['root']);yaw0=last['yaw_rad']
            for _ in range(400):
                b.tick();row=record('standing')
                if (np.linalg.norm(np.asarray(row['root'])-origin)>.05
                        or abs(np.arctan2(np.sin(row['yaw_rad']-yaw0),np.cos(row['yaw_rad']-yaw0)))>.1):
                    raise RuntimeError('Variant1 standing drift gate')
        (output/'video/scene_setup.json').write_text(json.dumps(b.scene_setup,indent=2))
        return b
    except BaseException:
        if video:video.close()
        raise
