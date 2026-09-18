"""Learning-only handover admission. Privileged measurements never leave host logs."""
import json
import math
from pathlib import Path

from rsi.task_progress import MobileProgress, MobileProgressSupervisor, commanded_foot_motion
from rsi.simple_handover import HANDOVER_ENVS, HANDOVER_BACK_ENV

HANDOVER_PROGRESS = dict(id='handover-goal-progress-v2-reacquire', learning_only=True, corrective_attempt_required=True,
    no_progress_s=90., progress_distance_m=.01,
    feedback_tier='simulator_supervised_progress_learning', formal_credit=False)


class HandoverProgress(MobileProgress):
    """Reuse the existing event/stop boundary; no total time/action/turn cap."""
    def __init__(self, config):
        if config != HANDOVER_PROGRESS:
            raise ValueError('Unreviewed Handover progress contract')
        self.config=dict(config)
        self.start=self.now=self.last_progress=None
        self.stop_reason=None; self.cancel_chunk=False; self.events=[]
        self.phase='acquire'; self.highest=0; self.best={}
        self.right=self.left=self.supported=False
        self.distance_motion=False; self.admission_error=None

    def update(self, sample):
        now=float(sample['time']); distance=float(sample['goal_distance_m'])
        if (not math.isfinite(now) or not math.isfinite(distance) or distance < 0
                or (self.now is not None and now < self.now)):
            if self.now is None:self.start=self.now=self.last_progress=0.
            self.stop('progress_invalid_sample'); return
        self.now=now
        if self.start is None:self.start=self.last_progress=now
        if self.stop_reason:return
        self.right=bool(sample['right_retained']);self.left=bool(sample['left_retained'])
        self.supported=bool(sample['destination_support'])
        previous=self.phase
        self.phase=('place' if self.left or (self.highest>=2 and self.supported)
                    else 'transfer' if self.right else 'acquire')
        if previous!='acquire' and self.phase=='acquire':
            self.cancel_chunk=True;self.event('grasp_lost_return_to_acquire')
        rank={'acquire':0,'transfer':1,'place':2}[self.phase]
        if rank > self.highest:
            self.highest=rank;self.last_progress=now
            self.event('new_independent_retention_stage')
        # Best-ever net distance in each phase; replay/loss/regrasp cannot buy time.
        if self.phase not in self.best:self.best[self.phase]=distance
        elif (self.distance_motion and distance <= self.best[self.phase]-self.config['progress_distance_m']
                and (rank==0 or self.right or self.left)):
            self.best[self.phase]=distance;self.last_progress=now
            self.event('new_goal_approach')
        if now-self.last_progress >= self.config['no_progress_s']:
            self.stop('progress_stall')

    def admit(self, stage, *, distance_motion=False, knots=1, open_grippers=True, hand_contact=False,
              moving_feet=False, reacquisition=False):
        self.cancel_chunk=False;self.distance_motion=distance_motion;self.admission_error=None
        if self.stop_reason:return False
        transfer=stage in ('present','receiver_enclosure','load_transfer','giver_clear')
        placement=stage in ('loaded_travel','lower','release','hands_clear_supported')
        local=stage in ('approach','stationary_reach') and reacquisition and open_grippers
        violation=((moving_feet and not (self.right or self.left) and not local)
            or (transfer and not (self.right or self.left))
            or (placement and not (self.left or (self.highest>=2 and self.supported)))
            or (knots>1 and (stage not in ('approach','stationary_reach')
                or not open_grippers or hand_contact)))
        if violation:
            return self.reject()
        return True

    def snapshot(self):
        # Permission/stall feedback is supervision, never an alleged RGB fact.
        return dict(contract=self.config['id'],feedback_tier=self.config['feedback_tier'],
            formal_credit=False,stop_reason=self.stop_reason,
            feedback_semantics='Host action permission/stall decision; not visual evidence. '
                'Use public RGB and robot receipts for claims; raw task measurements are private.')


class HandoverProgressSupervisor(MobileProgressSupervisor):
    """Use the already installed completion sampler, reset and safe tool boundary."""
    def __init__(self, backend, output, config):
        self.backend=backend;self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.guard=HandoverProgress(config)
        self.evaluator=backend.placement_evaluator
        if self.evaluator.env_id not in HANDOVER_ENVS:
            raise ValueError('Handover progress requires its exact completion evaluator')
        self.reset_id=backend.scene_setup['reset_provenance']['reset_id']
        self.target=self.evaluator.target
        self.wrists={s:int(backend.model.body(s+'_wrist_yaw_link').id) for s in ('left','right')}
        self.destination=(backend.data.xpos[self.target].copy() if self.evaluator.env_id==HANDOVER_BACK_ENV
            else backend.data.xpos[self.evaluator.container].copy() if self.evaluator.container>=0 else None)
        self.multi=False;self.touching=False
        self.update(backend)

    def update(self, backend):
        if (backend is not self.backend or backend.scene_setup['reset_provenance']['reset_id']!=self.reset_id):
            self.guard.stop('progress_reset_mismatch');return
        # Pure completion update is idempotent at one sim timestamp; no actions/rewards.
        e=self.evaluator;e.update(backend);s=e._last_sample
        if backend.reason or e.outcome(backend) in ('success','failure'):
            return  # Completion/safety owns the terminal; never mask it as a stall.
        sides=set(s['grasped_sides'])
        right=bool(e._right and 'right' in sides)
        left=bool(e._left and 'left' in sides)
        phase=('place' if left or (self.guard.highest>=2 and s['container_contact'])
               else 'transfer' if right else 'acquire')
        obj=backend.data.xpos[self.target]
        if phase=='place':
            distance=math.dist(obj,self.destination) if self.destination is not None else 0.
        else:
            distance=math.dist(obj,backend.data.xpos[self.wrists['right' if phase=='acquire' else 'left']])
        sample=dict(time=float(s['time']),phase=phase,goal_distance_m=distance,
            right_retained=right,left_retained=left,destination_support=bool(s['container_contact']))
        self.guard.update(sample)
        self.touching=bool(s['touching_hands'])
        if self.multi and self.touching:self.guard.cancel_chunk=True
        with (self.output/'samples.jsonl').open('a') as stream:
            stream.write(json.dumps(sample)+'\n')

    def admit(self, claim, response, observation):
        trajectory=response['trajectory'];self.multi=len(trajectory)>1
        side='right' if self.guard.phase=='acquire' else 'left'
        name=side+'_wrist_yaw_link';current=observation['four_point_world'][name]['position_world_m']
        moving=any(name in w['active']['position'] and math.dist(
            current,w['target'][name]['position_world_m'])>=self.guard.config['progress_distance_m']
            for w in trajectory)
        feet=commanded_foot_motion(response,observation)
        return self.guard.admit(claim['currently_attempting'],distance_motion=moving or feet,
            moving_feet=feet,reacquisition=claim.get('reacquisition_target')=='original_task_object',
            knots=len(trajectory),open_grippers=all(all(v==0 for v in w['grippers'].values())
            for w in trajectory),hand_contact=self.touching)
