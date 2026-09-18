"""Pure host-only retained-lift curriculum evaluator; no actor data exports.

The owner must provide standing_ok from the existing fall monitor and complete
samples from the same reset. Native history is diagnostic; required terminal flags use the current sample.
"""
import math
from copy import deepcopy

class RetainedCurriculumGate:
    def __init__(self, level):
        if level['kind'] != 'retained_lift':
            raise ValueError('retained_lift level required')
        if level['hand'] == 'both hands together':
            raise ValueError('Mobile requires the separate bilateral retention sampler/guard')
        self.level=deepcopy(level)
        self.last_time=None;self.reset_id=None;self.native_seen=False
        self.acquire_action=None;self.side=None
        self.hold_action=None;self.since=None;self.position=None;self.rotation=None
        self.status='in_progress';self.reason=None

    def clear_retention(self):
        self.acquire_action=self.side=self.hold_action=self.since=None
        self.position=self.rotation=None

    def update(self, sample):
        self.status='in_progress';self.reason=None
        required=('time','reset_id','rise_m','bottom_clearance_m','target_position_m',
            'target_quaternion_wxyz','grasped_sides','touching_hands','nonhand_support',
            'standing_ok','action_id','command_complete')
        if any(k not in sample for k in required):
            self.clear_retention();self.status='unavailable';self.reason='missing_host_signal';return self.status
        if self.level['native_success_required'] and type(sample.get('native_success')) is not bool:
            self.clear_retention();self.status='unavailable';self.reason='missing_or_invalid_native_signal';return self.status
        now=sample['time'];position=sample['target_position_m'];rotation=sample['target_quaternion_wxyz']
        values=[now,sample['rise_m'],sample['bottom_clearance_m'],*position,*rotation]
        if len(position)!=3 or len(rotation)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in values) or abs(sum(x*x for x in rotation)-1)>.02:
            self.clear_retention();self.status='unavailable';self.reason='invalid_host_sample';return self.status
        if self.reset_id is None:self.reset_id=sample['reset_id']
        if sample['reset_id']!=self.reset_id or (self.last_time is not None and now<self.last_time):
            self.clear_retention();self.status='unavailable';self.reason='reset_or_clock_changed';return self.status
        self.last_time=now;cfg=self.level
        self.native_seen |= sample.get('native_success') is True
        sides=set(sample['grasped_sides']);touch=set(sample['touching_hands'])
        side=next(iter(sides)) if len(sides)==1 else None
        allowed=({'right'} if cfg['hand']=='right hand only' else {'left','right'})
        held=(side in allowed and touch==sides and sample['nonhand_support'] is False
            and sample['standing_ok'] is True
            and sample['rise_m']>=cfg['minimum_origin_rise_m']
            and sample['bottom_clearance_m']>cfg['full_object_clearance_m'])
        action=sample['action_id']
        if not held or not isinstance(action,str) or not action:
            self.clear_retention();return self.status
        if self.side!=side:
            self.clear_retention();self.side=side;self.acquire_action=action
        if cfg['separate_action_required'] and (action==self.acquire_action or sample.get('stationary_command') is not True):
            self.since=self.position=self.rotation=self.hold_action=None;return self.status
        stable=(self.position is not None and math.dist(position,self.position)<=cfg['hold_translation_m']
            and 2*math.acos(min(1.,abs(sum(a*b for a,b in zip(rotation,self.rotation)))))<=cfg['hold_rotation_rad'])
        if self.since is None or not stable or (cfg['separate_action_required'] and self.hold_action!=action):
            self.since=now;self.position=list(position);self.rotation=list(rotation);self.hold_action=action
        enough=now-self.since>=cfg['retained_hold_s']-1e-9
        native_ok=not cfg['native_success_required'] or sample.get('native_success') is True
        if enough and native_ok and sample['command_complete'] is True:
            self.status='curriculum_success'
        return self.status
