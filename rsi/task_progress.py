"""Learning-only causal progress gates. Never a leaderboard success evaluator.

The actor plans from RGB/proprioception. The simulator supervisor admits phases
and terminates unproductive learning; its privileged samples stay host-only.
This feedback variant must not be reported as unassisted RGB-only evaluation.
"""
import json
import math
from pathlib import Path

MOBILE_ENV = 'simple/G1WholebodyLocomotionPickBetweenTablesTeleop-v0'
MOBILE_PROGRESS = dict(id='mobile-progress-v3-reacquire', env_id=MOBILE_ENV,
    learning_only=True, expected_task_s=480., corrective_attempt_required=True,
    no_progress_s=180., stable_hold_s=1., loss_grace_s=.12,
    relative_slip_m=.03, minimum_lift_m=.02, progress_distance_m=.02,
    arrival_distance_m=.20, minimum_transport_m=.10, placement_hold_s=1.,
    feedback_tier='simulator_supervised_progress_learning', formal_credit=False)
MOBILE_COMPLETION = dict(id='mobile-ordered-retained-placement-v1', learning_only=True,
    native_reward_unchanged=True, unmodified_native_benchmark=False,
    independent_video_audit_required=True)


class MobileProgressEvaluator:
    completion_contract = MOBILE_COMPLETION

    def reset(self, backend):
        if backend._native_task_success:
            raise ValueError('Initial scene already meets native criterion')
        self._outcome = 'in_progress'
        self.native_seen = False
        self.guard = None

    def update(self, backend):
        self.native_seen |= bool(backend._native_task_success)
        self.guard = getattr(backend, 'mobile_progress_guard', None)
        if backend.reason:
            self._outcome = 'failure'
        elif (self.guard and self.guard.stage == 'complete' and
              backend._native_task_success and not self.guard.stop_reason):
            self._outcome = 'success'

    def outcome(self, backend):
        return self._outcome

    def host_audit_state(self):
        return dict(native_milestone_seen=self.native_seen,
            progress=self.guard.snapshot() if self.guard else None,
            independent_video_audit_required=True)


class MobileProgress:
    """Finite-state admission plus evidence-based progress, using simulation time."""
    def __init__(self, config):
        if config != MOBILE_PROGRESS:
            raise ValueError('Unreviewed progress thresholds; publish a new contract')
        self.config = dict(config)
        self.start = self.now = self.last_progress = None
        self.hold_since = self.gap_since = self.release_since = None
        self.relative = self.root_at_grasp = None
        self.best_distance = self.best_acquisition = math.inf
        self.distance_motion = False
        self.admission_error = None
        self.held = self.arrived = self.supported = self.transport_verified = False
        self.stage = 'acquire'
        self.stop_reason = None
        self.cancel_chunk = False
        self.events = []

    def event(self, name):
        self.events.append(dict(event=name, elapsed_sim_s=self.now-self.start))

    def stop(self, reason):
        if self.stop_reason is None:
            self.stop_reason = reason
            self.event(reason)
        self.cancel_chunk = True

    def update(self, s):
        now = float(s['time'])
        if not math.isfinite(now) or (self.now is not None and now < self.now):
            if self.now is None:self.start=self.now=self.last_progress=0.
            self.stop('progress_invalid_sample'); return
        self.now = now
        if self.start is None:
            self.start = self.last_progress = self.now
        if self.stop_reason or self.stage == 'complete':
            return
        cfg = self.config
        distance = float(s['acquisition_distance_m'])
        if not math.isfinite(distance) or distance < 0:
            self.stop('progress_invalid_sample'); return
        if self.stage == 'acquire':
            if math.isinf(self.best_acquisition):self.best_acquisition = distance
            elif self.distance_motion and distance <= self.best_acquisition-cfg['progress_distance_m']:
                self.best_acquisition = distance; self.last_progress = self.now
                self.event('new_original_target_approach')
        self.supported = bool(s['container_support'])
        retain = s['bilateral'] and s['unsupported'] and s['lifted']
        if retain:
            self.gap_since = None
            delta = (math.dist(s['relative'], self.relative) if self.relative else 0.)
            if self.hold_since is None or delta > cfg['relative_slip_m']:
                self.hold_since = self.now
                self.relative = list(s['relative'])
            stable = self.now-self.hold_since >= cfg['stable_hold_s']
            if not self.held and stable:
                self.held = True
                self.stage = 'hold'
                self.root_at_grasp = list(s['root_xy'])
                # Retain the best loaded distance across losses: replaying an
                # already reached prefix cannot refresh the progress clock.
                self.best_distance = min(self.best_distance, s['destination_distance_m'])
                # Repeated loss/regrasp cycles cannot repeatedly buy more time.
                if not any(e['event']=='stable_bimanual_hold' for e in self.events):
                    self.last_progress = self.now
                self.event('stable_bimanual_hold')
            elif self.held and delta > cfg['relative_slip_m']:
                self._lost()
        elif not (self.stage == 'place' and self.supported):
            self.hold_since = None
            if self.held:
                if self.gap_since is None:self.gap_since = self.now
                if self.now-self.gap_since > cfg['loss_grace_s']:self._lost()
        if self.held and self.stage in ('transport','place'):
            moved = math.dist(s['root_xy'], self.root_at_grasp)
            distance = s['destination_distance_m']
            if (moved >= cfg['minimum_transport_m'] and
                    distance <= self.best_distance-cfg['progress_distance_m']):
                self.last_progress = self.now
                self.best_distance = distance
                self.transport_verified = True
            if (self.transport_verified and distance <= cfg['arrival_distance_m']
                    and not self.arrived):
                self.arrived = True
                self.event('arrived_with_object')
                self.last_progress = self.now
        if self.stage == 'place' and self.arrived and self.supported and not s['hand_contact']:
            if self.release_since is None:self.release_since = self.now
            if self.now-self.release_since >= cfg['placement_hold_s']:
                self.held = False
                self.stage = 'complete'
                self.event('released_supported')
                return
        else:
            self.release_since = None
        if self.now-self.last_progress >= cfg['no_progress_s']:
            self.stop('progress_stall')

    def _lost(self):
        self.held = self.arrived = self.transport_verified = False
        self.hold_since = self.relative = None
        self.stage = 'acquire'
        self.cancel_chunk = True  # cancel the remainder of a loaded chunk now
        self.event('grasp_lost_return_to_acquire')

    def reject(self):
        # Validation rejected before execution. Keep the reset for a corrected request.
        self.admission_error = 'progress_order_violation'
        return False

    def admit(self, stage, *, moving_feet, reacquisition=False, distance_motion=False,
              open_grippers=True):
        self.cancel_chunk = False
        self.admission_error = None
        self.distance_motion = distance_motion
        if self.stop_reason:return False
        local = stage in ('approach','stationary_reach') and reacquisition and open_grippers
        violation = ((moving_feet and not self.held and not local)
            or (stage == 'loaded_travel' and not self.held)
            or (stage == 'lower' and not (self.held and self.arrived))
            or (stage in ('release','hands_clear_supported') and not
                (self.stage == 'place' and self.arrived and self.supported)))
        if violation:
            return self.reject()
        if self.held and (stage == 'loaded_travel' or moving_feet):
            self.stage = 'transport'
        elif stage == 'lower':
            self.stage = 'place'
        return True

    def snapshot(self):
        elapsed = 0. if self.start is None else self.now-self.start
        labels = [('acquire','获取物体'),('hold','双手稳定持物'),
                  ('transport','持物移动至对面'),('place','支持后放下并松手')]
        complete = self.stage == 'complete'
        done = {'acquire':self.held or complete, 'hold':self.held or complete,
                'transport':self.arrived or complete, 'place':complete}
        return dict(contract=self.config['id'], feedback_tier=self.config['feedback_tier'],
            formal_credit=False, elapsed_sim_s=elapsed, stage=self.stage,
            stop_reason=self.stop_reason, review_due=elapsed>=self.config['expected_task_s'],
            last_progress_sim_s=None if self.start is None else self.last_progress-self.start,
            no_progress_s=0. if self.start is None else self.now-self.last_progress,
            expected_task_s=self.config['expected_task_s'], stable_bimanual_hold=self.held,
            next_learning_focus=('stable_bimanual_grasp_and_small_body_motion'
                if self.stage in ('acquire','hold') else 'retained_transport_and_placement'),
            events=self.events[-12:],
            phases=[dict(id=k,label=label,status=('done' if done[k] else
                'stopped' if self.stop_reason and self.stage==k else
                'active' if self.stage==k else 'blocked')) for k,label in labels])


class MobileProgressSupervisor:
    """Host-only MuJoCo measurements; no poses/contacts/distances in actor packets."""
    def __init__(self, backend, output, config):
        self.backend = backend
        self.guard = MobileProgress(config)
        backend.mobile_progress_guard = self.guard
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        model, task = backend.model, backend.env.task
        self.target = int(model.body(str(task.target.asset.label)).id)
        self.container = int(model.body(str(task.container.asset.label)).id)
        def descendants(root):
            result = {root}
            for b in range(root+1, model.nbody):
                if int(model.body_parentid[b]) in result:result.add(b)
            return result
        self.targets = descendants(self.target)
        self.containers = descendants(self.container)
        self.wrists = [int(model.body(f'{s}_wrist_yaw_link').id) for s in ('left','right')]
        self.hands = [descendants(w) for w in self.wrists]
        self.robot = descendants(int(model.body('pelvis').id))
        self.root = int(model.body('pelvis').id)
        self.initial_z = float(backend.data.xpos[self.target,2])
        self.update(backend)

    def sample(self):
        import mujoco
        import numpy as np
        b = self.backend
        contacted = set()
        for i in range(b.data.ncon):
            c = b.data.contact[i]
            a, z = (int(b.model.geom_bodyid[g]) for g in (c.geom1,c.geom2))
            if (a in self.targets) == (z in self.targets):continue
            force = np.zeros(6)
            mujoco.mj_contactForce(b.model,b.data,i,force)
            if force[0] > .01:contacted.add(z if a in self.targets else a)
        obj = b.data.xpos[self.target]
        closure = b.gripper_command_at(b.data.time)
        relative = []
        for w in self.wrists:
            relative.extend((b.data.xmat[w].reshape(3,3).T @ (obj-b.data.xpos[w])).tolist())
        return dict(time=float(b.data.time), bilateral=all(bool(contacted & hand)
            and closure[side]>.1 for side,hand in zip(('left','right'),self.hands)),
            unsupported=not bool(contacted-set.union(*self.hands)),
            lifted=float(obj[2])-self.initial_z>=self.guard.config['minimum_lift_m'],
            relative=relative, root_xy=b.data.xpos[self.root,:2].tolist(),
            acquisition_distance_m=max(float(np.linalg.norm(obj-b.data.xpos[w])) for w in self.wrists),
            destination_distance_m=float(np.linalg.norm(obj[:2]-b.data.xpos[self.container,:2])),
            container_support=bool(contacted & self.containers) and not
                bool(contacted-self.robot-self.containers),
            hand_contact=bool(contacted & self.robot))

    def update(self, backend):
        s = self.sample()
        self.guard.update(s)
        with (self.output/'samples.jsonl').open('a') as stream:
            stream.write(json.dumps(s)+'\n')

    def admit(self, claim, response, observation):
        moving = commanded_foot_motion(response, observation)
        reaching = any(name in w['active']['position'] and math.dist(
            observation['four_point_world'][name]['position_world_m'],
            w['target'][name]['position_world_m']) >= self.guard.config['progress_distance_m']
            for w in response['trajectory'] for name in ('left_wrist_yaw_link','right_wrist_yaw_link'))
        return self.guard.admit(claim['currently_attempting'], moving_feet=moving,
            reacquisition=claim.get('reacquisition_target')=='original_task_object',
            distance_motion=reaching or moving,
            open_grippers=all(all(v==0 for v in w['grippers'].values()) for w in response['trajectory']))

    def publish(self, path):
        row = self.guard.snapshot()
        temp = Path(path).with_suffix('.tmp')
        temp.write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
        temp.replace(path)
        return row


def commanded_foot_motion(response, observation):
    """Detect named active foot translation/rotation, including small repeated turns."""
    for w in response['trajectory']:
        for name in ('left_ankle_roll_link','right_ankle_roll_link'):
            current=observation['four_point_world'][name]; target=w['target'][name]
            if name in w['active']['position'] and math.dist(current['position_world_m'],target['position_world_m'])>1e-6:
                return True
            if name in w['active']['orientation']:
                a,z=current['quaternion_wxyz'],target['quaternion_wxyz']
                norm=math.sqrt(sum(x*x for x in a)*sum(x*x for x in z))
                angle=2*math.acos(min(1.,abs(sum(x*y for x,y in zip(a,z)))/norm)) if norm else math.inf
                if angle>1e-6:return True
    return False
