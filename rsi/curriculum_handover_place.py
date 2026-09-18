"""Pure host C2 gate; no actor exports, physics steps or native reward changes.

The existing C1 gate supplies opposed, unsupported ordered hand retention.
C2 supplies its own exact 0.5 s thresholds, placement sequence and final flag.
Only an owning host's final whole-action ACK may set command_complete=True.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from rsi.curriculum_handover import (
    ENV_ID, SPEC, SPEC_SHA256, HandoverC1Gate, Status,
)


def contract() -> dict[str, Any]:
    raw = SPEC.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SPEC_SHA256:
        raise ValueError('Published curriculum specification changed')
    source = json.loads(raw)
    task = next(t for t in source['tasks'] if t['env_id'] == ENV_ID)
    level = copy.deepcopy(next(l for l in task['levels'] if l['level'] == 'C2'))
    return dict(id=source['id'], spec_sha256=SPEC_SHA256, env_id=ENV_ID,
                level='C2', criteria=level,
                instruction=level['instruction_template'].format(target=task['target'], **level),
                goal_scope='full_task', official_evaluation=False)


class Stage(str, Enum):
    ACQUIRE_RIGHT = 'acquire_right'
    HOLD_RIGHT = 'hold_right'
    TRANSFER = 'transfer'
    HOLD_LEFT = 'hold_left'
    PLACE_BACK = 'place_back'
    RELEASE_ON_TABLE = 'release_on_table'
    RELEASE_GRACE = 'release_grace'
    SETTLE_ON_TABLE = 'settle_on_table'
    AWAIT_NATIVE_FINAL_FLAG = 'await_native_final_flag'
    AWAIT_FINAL_ACK = 'await_final_ack'
    COMPLETE = 'complete'
    UNAVAILABLE = 'unavailable'


@dataclass(frozen=True)
class HostProgress:
    status: Status
    stage: Stage
    reset_id: str
    time: float | None
    right_prerequisite: bool
    right_verified_at: float | None
    left_prerequisite: bool
    left_verified_at: float | None
    right_only_elapsed_s: float
    left_only_elapsed_s: float
    released_support_elapsed_s: float
    unsupported_release_elapsed_s: float
    original_table_contact: bool
    final_ack_action_id: str | None
    reason: str | None
    native_success_seen: bool
    raw_native_final_flag: bool | None
    curriculum_success: bool
    full_task_success: bool
    official_success: bool = False

    def host_dict(self) -> dict[str, Any]:
        return asdict(self)


class _C2Acquisition(HandoverC1Gate):
    """Reuse C1 mechanics, never its shorter durations or terminal decision."""
    def __init__(self, reset_id: str, c2_binding: Mapping[str, Any]):
        super().__init__(reset_id)
        self.binding = copy.deepcopy(c2_binding)
        self._level = copy.deepcopy(c2_binding['criteria'])


class HandoverC2Gate:
    REQUIRED = HandoverC1Gate.REQUIRED | frozenset((
        'robot_contact', 'other_support', 'target_position_m', 'target_quaternion_wxyz',
    ))

    def __init__(self, reset_id: str, binding: Mapping[str, Any] | None = None):
        expected = contract()
        if binding is not None and binding != expected:
            raise ValueError('Only the exact published Handover PlaceBack C2 is admitted')
        self.binding = copy.deepcopy(expected)
        self.level = self.binding['criteria']
        self._acquisition = _C2Acquisition(reset_id, self.binding)
        self.reset_id = reset_id
        self.last_time: float | None = None
        self.native_seen = False
        self.native_final: bool | None = None
        self.error: str | None = None
        self.table_contact = False
        self._clear_chain()

    def _clear_settle(self) -> None:
        self.release_since: float | None = None
        self.settle_position: list[float] | None = None
        self.settle_quaternion: list[float] | None = None

    def _clear_chain(self) -> None:
        self._acquisition._clear_chain()
        self._acquisition_progress = None
        self.left_verified_at: float | None = None
        self.gap_since: float | None = None
        self._clear_settle()

    def _result(self, stage: Stage, *, status: Status = Status.IN_PROGRESS,
                reason: str | None = None, ack: str | None = None) -> HostProgress:
        progress = self._acquisition_progress
        now = self.last_time
        elapsed = lambda start: now-start if start is not None and now is not None else 0.
        success = status == Status.CURRICULUM_SUCCESS
        return HostProgress(
            status=status, stage=stage, reset_id=self.reset_id, time=now,
            right_prerequisite=self._acquisition.right_verified_at is not None,
            right_verified_at=self._acquisition.right_verified_at,
            left_prerequisite=self.left_verified_at is not None,
            left_verified_at=self.left_verified_at,
            right_only_elapsed_s=progress.right_only_elapsed_s if progress else 0.,
            left_only_elapsed_s=progress.left_only_elapsed_s if progress else 0.,
            released_support_elapsed_s=elapsed(self.release_since),
            unsupported_release_elapsed_s=elapsed(self.gap_since),
            original_table_contact=self.table_contact,
            final_ack_action_id=ack, reason=reason,
            native_success_seen=self.native_seen, raw_native_final_flag=self.native_final,
            curriculum_success=success, full_task_success=success,
        )

    def _unavailable(self, reason: str) -> HostProgress:
        self.error = reason
        self._clear_chain()
        return self._result(Stage.UNAVAILABLE, status=Status.UNAVAILABLE, reason=reason)

    def _loss(self, reason: str) -> HostProgress:
        self._clear_chain()
        return self._result(Stage.ACQUIRE_RIGHT, reason=reason)

    def _validate(self, sample: Mapping[str, Any]) -> str | None:
        if not isinstance(sample, Mapping) or not self.REQUIRED <= sample.keys():
            return 'missing_host_signal'
        finite = HandoverC1Gate._finite
        if (not finite(sample['time']) or sample['time'] < 0
                or not finite(sample['bottom_clearance_m'])
                or any(type(sample[k]) is not bool for k in (
                    'nonhand_support', 'container_contact', 'robot_contact', 'other_support',
                    'standing_ok', 'native_success', 'command_complete'))
                or (sample['action_id'] is not None and (
                    not isinstance(sample['action_id'], str) or not sample['action_id'].strip()))
                or (sample['command_complete'] and not sample['action_id'])):
            return 'invalid_host_sample'
        sides = HandoverC1Gate._sides(sample['grasped_sides'])
        touch = HandoverC1Gate._sides(sample['touching_hands'])
        if sides is None or touch is None or not sides <= touch:
            return 'invalid_hand_contact_sample'
        for key, size in (('target_position_m', 3), ('target_quaternion_wxyz', 4)):
            values = sample[key]
            if (not isinstance(values, (list, tuple)) or len(values) != size
                    or not all(finite(v) for v in values)):
                return 'invalid_host_pose'
        norm = math.sqrt(sum(v*v for v in sample['target_quaternion_wxyz']))
        if abs(norm-1.) > .01:  # Same validity envelope as the existing sampler consumer.
            return 'invalid_host_quaternion'
        if sample['reset_id'] != self.reset_id:
            return 'reset_changed'
        if self.last_time is not None and sample['time'] < self.last_time:
            return 'clock_regressed'
        return None

    def update(self, sample: Mapping[str, Any]) -> HostProgress:
        if self.error is not None:
            return self._result(Stage.UNAVAILABLE, status=Status.UNAVAILABLE, reason=self.error)
        error = self._validate(sample)
        if error:
            return self._unavailable(error)
        now = self.last_time = float(sample['time'])
        self.native_final = sample['native_success']
        self.native_seen |= self.native_final
        self.table_contact = sample['container_contact']
        if not sample['standing_ok']:
            return self._loss('standing_lost')
        if sample['other_support']:
            return self._loss('wrong_external_support')
        if sample['nonhand_support'] and not self.table_contact:
            return self._loss('non_table_nonhand_support')

        # Before left retention, C1 mechanics enforce strict unsupported order.
        # Intermediate C1 success/ACK is ignored; C2 requires placement below.
        if self.left_verified_at is None:
            progress = self._acquisition.update(sample)
            self._acquisition_progress = progress
            if progress.status == Status.UNAVAILABLE:
                return self._unavailable(progress.reason or 'acquisition_unavailable')
            if not progress.left_only_retained:
                return self._result(Stage(progress.stage.value), reason=progress.reason)
            self.left_verified_at = now
            return self._result(Stage.PLACE_BACK)

        sides = set(sample['grasped_sides'])
        touch = set(sample['touching_hands'])
        # Expiry must be checked before accepting a late landing/regrasp.
        if (self.gap_since is not None
                and now-self.gap_since > self.level['unsupported_release_grace_s']+1e-9):
            return self._loss('unsupported_release_grace_expired')

        if self.table_contact:
            self.gap_since = None
            if touch or sides or sample['robot_contact']:
                self._clear_settle()
                return self._result(Stage.RELEASE_ON_TABLE, reason='release_all_robot_contact')
            pos = list(sample['target_position_m'])
            q = list(sample['target_quaternion_wxyz'])
            # Normalize valid numeric quaternions for sign-invariant angles.
            norm = math.sqrt(sum(v*v for v in q)); q = [v/norm for v in q]
            stable = (self.settle_position is not None
                and math.dist(pos, self.settle_position) <= self.level['settled_translation_m']
                and 2*math.acos(min(1., abs(sum(a*b for a,b in zip(q, self.settle_quaternion)))))
                    <= self.level['settled_rotation_rad'])
            if self.release_since is None or not stable:
                self.release_since = now
                self.settle_position, self.settle_quaternion = pos, q
            if now-self.release_since < self.level['released_support_s']-1e-9:
                return self._result(Stage.SETTLE_ON_TABLE)
            if not self.native_final:
                return self._result(Stage.AWAIT_NATIVE_FINAL_FLAG, reason='current_native_flag_required')
            if not sample['command_complete']:
                return self._result(Stage.AWAIT_FINAL_ACK)
            return self._result(Stage.COMPLETE, status=Status.CURRICULUM_SUCCESS,
                                ack=sample['action_id'])

        self._clear_settle()
        if sides:
            self.gap_since = None
            # After verified left retention, approaching the original table
            # necessarily crosses the acquisition clearance threshold.
            if 'left' in sides:
                return self._result(Stage.PLACE_BACK)
            if sample['bottom_clearance_m'] <= self.level['full_object_clearance_m']:
                return self._loss('whole_object_clearance_lost')
            # Returning the object to the right relinquishes left ownership;
            # the still-supported right prerequisite survives, left .5 s must recur.
            self.left_verified_at = None
            self._acquisition_progress = self._acquisition.update(sample)
            return self._result(Stage.TRANSFER, reason='left_ownership_relinquished')
        if self.gap_since is None:
            self.gap_since = now
        return self._result(Stage.RELEASE_GRACE, reason='unsupported_release_transition')
