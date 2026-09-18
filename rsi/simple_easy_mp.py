"""Two exact preflighted native MP tasks, reusing original control and gates.

No model call or physics occurs on import. Keep all raw
completion samples host-only. Existing control, safety and hold gates are reused.
"""
from pathlib import Path
import hashlib
import json
import random
import numpy as np

from rsi.simple_grasp_mp import (
    CONTRACT as GRASP_CONTRACT, CONTROLLER, HOST, PREPARATION,
    RetainedGraspEvaluator, NativeActorCapture, load_module,
)
from rsi.simple_placement import SimplePlacementEvaluator, PLACEMENT_CONTRACT

GRASP = 'simple/G1WholebodyTabletopGraspVariant3MP-v0'
PLACE = 'simple/G1WholebodyPickNPlaceVariant1MP-v0'
TASKS = {
    GRASP: dict(uid='g1_wholebody_tabletop_grasp_variant3_mp',
        contract=dict(GRASP_CONTRACT, id='tabletop-variant3-retained-clear-lift-v1', scope=GRASP),
        instruction='Grasp the specified apple on the tabletop, lift it fully clear of support and retain it during a separately commanded stationary hold.'),
    PLACE: dict(uid='g1_wholebody_pick_n_place_variant1_mp',
        contract=dict(PLACEMENT_CONTRACT, id='pick-n-place-variant1-released-container-support-v1', scope=PLACE),
        instruction='Pick up the apple and place it on or in the nearby green dish. Confirm acquisition and an unsupported lift before transferring it; release after support and verify sustained placement without hand contact.'),
}


def definition(env_id):
    if env_id not in TASKS:
        raise ValueError('Unreviewed easy native MP identity')
    return TASKS[env_id]


class ScopedGraspEvaluator(RetainedGraspEvaluator):
    def __init__(self):
        super().__init__()
        self.env_id = GRASP
        self.task_uid = TASKS[GRASP]['uid']
        self.completion_contract = TASKS[GRASP]['contract']
        # The inherited pure gate reads original numeric constants. Exact parity
        # is intentional: this scene variant must not relax grasp requirements.
        assert all(self.completion_contract[k] == v for k, v in GRASP_CONTRACT.items()
                   if k not in ('id', 'scope'))

    def host_audit_state(self):
        return dict(super().host_audit_state(), contract=self.completion_contract['id'])


class ScopedPlacementEvaluator(SimplePlacementEvaluator):
    def reset(self, backend):
        # Exact-task form of the existing boxplace sampler initialization.
        task, model = backend.env.task, backend.model
        if task.uid != TASKS[PLACE]['uid']:
            raise ValueError('Wrong task for scoped placement evaluator')
        self.target = int(model.body(str(task.target.asset.label)).id)
        self.container = int(model.body(str(task.container.asset.label)).id)
        self.robot = {int(model.body('pelvis').id)}
        self.hands = {int(model.body(f'{s}_wrist_yaw_link').id) for s in ('left', 'right')}
        for body in range(1, model.nbody):
            for group in (self.robot, self.hands):
                if int(model.body_parentid[body]) in group:
                    group.add(body)
        self.initial_z = float(backend.data.xpos[self.target, 2])
        self._lift_since = self._release_since = self._gap_since = None
        self._acquired = False
        self._outcome = 'in_progress'
        self._last_sample = None
        backend.placement_evaluator = self

    def host_audit_state(self):
        return dict(super().host_audit_state(), contract=TASKS[PLACE]['contract']['id'])


def initialize(backend, output, seed, recorder, env_id):
    """Recorded 1s clearance + 2s standing, exactly as each short preflight."""
    from rsi.simulation_provenance import reset_provenance
    from rsi.simple_recording import external_robot_contacts, named_render_state
    b = backend
    task = definition(env_id)
    if (b.env.task.uid != task['uid'] or b.env.spec.id != env_id
            or b.env.task.dr_cfgs['target'].asset_id != 'graspnet1b:12'
            or b.robot.uid != 'g1_wholebody'
            or b.control_configuration['controller'] != CONTROLLER
            or b.env.spec.max_episode_steps is not None):
        raise ValueError('Exact easy MP reset/control mismatch')
    if env_id == PLACE and b.env.task.dr_cfgs['container'].asset_id != 'graspnet1b:46':
        raise ValueError('Exact placement container mismatch')
    b.scene_setup.update(env_id=env_id, seed=seed, completion_contract=task['contract'],
        reset_provenance=reset_provenance(b, seed), initial_state_modified=False,
        initialization='Recorded robot-only30mm clearance then2s standing; not task credit')
    b.state_hash = lambda: hashlib.sha256(b''.join(v.tobytes() for v in
        (b.data.qpos, b.data.qvel, b.data.ctrl))).hexdigest()
    video = None
    try:
        video = recorder(b, output/'video')
        b._reset_video = video
        (output/'initial-reset-host-only.json').write_text(json.dumps(named_render_state(b)))
        with (output/'initialization-host-only.jsonl').open('x') as stream:
            def record(phase):
                root = b.data.body('pelvis')
                w, x, y, z = root.xquat
                contacts = external_robot_contacts(b.model, b.data)
                row = dict(phase=phase, sim_s=float(b.data.time),
                    reset_id=b.scene_setup['reset_provenance']['reset_id'], root=root.xpos.tolist(),
                    yaw_rad=float(np.arctan2(2*(w*z+x*y), 1-2*(y*y+z*z))),
                    tilt_deg=float(np.degrees(np.arccos(np.clip(root.xmat.reshape(3,3)[2,2],-1,1)))),
                    height_above_floor_m=float(root.xpos[2]-b.ground), contacts_host_only=contacts)
                stream.write(json.dumps(row)+'\n')
                stream.flush()
                video.record_tick('initialization')
                if contacts or b.reason or row['tilt_deg'] > 25 or row['height_above_floor_m'] < .55:
                    raise RuntimeError('Easy MP initialization contact/stability gate')
                return row
            record('reset')
            prep = load_module('easy_native_clearance', PREPARATION)
            initial, goals, proposals = prep.prepare_targets(b)
            (output/'initialization-robot-only-proposals.json').write_text(json.dumps(proposals))
            for i in range(1, 51):
                prep.apply_ramp(b, initial, goals, i)
                b.tick()
                last = record('clearance')
            origin, yaw0 = np.asarray(last['root']), last['yaw_rad']
            for _ in range(100):
                b.tick()
                row = record('standing')
                if (np.linalg.norm(np.asarray(row['root'])-origin) > .05
                        or abs(np.arctan2(np.sin(row['yaw_rad']-yaw0),np.cos(row['yaw_rad']-yaw0))) > .1):
                    raise RuntimeError('Easy MP standing drift gate')
        (output/'video/scene_setup.json').write_text(json.dumps(b.scene_setup, indent=2))
        return b
    except BaseException:
        if video:
            video.close()
        raise


_host = load_module('easy_native_reused_host', HOST)
EASY_CANDIDATE = Path('/home/galbot/lizekai/RSI/artifacts/native-amo-wrist-control-v4/backend.py')


def create_backend(output, seed, env_id):
    definition(env_id)
    from rsi.simple_environment import configure_offline_assets, load_hssd_metadata
    from rsi.simple_sensors import install_pelvis_gyro
    from rsi.simple_object_names import install_unique_object_labels
    configure_offline_assets()
    from simple.scenes.hssd import HssdSceneManager
    HssdSceneManager.load = load_hssd_metadata
    import gymnasium as gym
    import simple.envs
    random.seed(seed)
    np.random.seed(seed)
    env = gym.make(env_id, sim_mode='mujoco', headless=True, render_hz=50, physics_dt=.002)
    try:
        install_pelvis_gyro(env)
        install_unique_object_labels(env)
        env.reset(seed=seed)
        b = load_module('easy_native_measured_control', EASY_CANDIDATE).NativeMPArms(env)
        b.scene_setup.update(native_reward_preserved=True,
            backend_sha256=hashlib.sha256(EASY_CANDIDATE.read_bytes()).hexdigest())
        initialize(b, Path(output), seed, _host.native_video, env_id)
        # Keep the exact validated initialization; enable only for subsequent requests.
        b.reanchor_enabled = b.coordinated_rate_enabled = True
        b.control_configuration['wrist_tracking'] = 'measured-start-coordinated-ray-v1'
        b.scene_setup['wrist_tracking'] = b.control_configuration['wrist_tracking']
        (Path(output)/'video/scene_setup.json').write_text(json.dumps(b.scene_setup, indent=2))
        return b
    except BaseException:
        env.close()
        raise


class EasyNativeLearningHost(_host.NativeLearningHost):
    def __init__(self, output, memory, episode_id, successes, *, seed=1, env_id):
        task = definition(env_id)['instruction'] + (
            ' Use only current RGB and named robot feedback. Native AMO owns legs/waist; '
            'only wrists and grippers are commandable. scalebfm_act is a compatibility '
            'tool name; no ScaleBFM or native expert planner runs.')
        _host.LearningHost.__init__(self, output, memory, episode_id, successes,
            task=task, backend_factory=lambda: create_backend(output, seed, env_id),
            evaluator_factory=ScopedGraspEvaluator if env_id == GRASP else ScopedPlacementEvaluator,
            image_capture_factory=lambda b: NativeActorCapture(b._reset_video, Path(output)/'rollout/episode'),
            geometry_provider=_host.HandGeometryProvider(Path(output)/'rollout/episode'),
            support_plane_z_m=None, max_episode_steps=None,
            execution_profile=_host.execution_profile('learning', None), require_selection=True)
        self.allow_voluntary_deferral = True
        self.corrective_attempt_required = True

    def tool_specs(self):
        specs=super().tool_specs()
        # The old native host described immediate three-action deferral.
        # New tasks use the central corrective-attempt contract instead.
        base=next(t for t in _host.LearningHost.tool_specs(self) if t['name']=='finish_attempt')
        for t in specs:
            if t['name']=='finish_attempt':t['description']=base['description']
        return specs
