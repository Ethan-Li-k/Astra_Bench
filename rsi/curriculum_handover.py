"""Unpublished, pure host-only Handover PlaceBack C1 gate.

No simulator, controller, actor, model, or shared runtime imports. Measurements
come from SimpleHandoverEvaluator.sample; the owning host adds reset_id,
standing_ok, action_id and command_complete. command_complete must mean the
FINAL WHOLE TOOL ACTION ACK, never an intermediate waypoint's tracker status.
All returned progress is privileged host/reviewer information.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from numbers import Real
from pathlib import Path
from typing import Any, Mapping


SPEC = Path('/home/galbot/lizekai/RSI/skills/curricula/curriculum-20260917-v1-0950b635108d0beb.json')
SPEC_SHA256 = '0950b635108d0beb42da631a90c7692177e34138f9e2f86ce1cee490f1e0a889'
ENV_ID = 'simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0'


def contract() -> dict[str, Any]:
    raw = SPEC.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SPEC_SHA256:
        raise ValueError('Published curriculum specification changed')
    source = json.loads(raw)
    task = next(t for t in source['tasks'] if t['env_id'] == ENV_ID)
    level = copy.deepcopy(next(l for l in task['levels'] if l['level'] == 'C1'))
    return dict(id=source['id'], spec_sha256=SPEC_SHA256, env_id=ENV_ID,
                level='C1', criteria=level,
                instruction=level['instruction_template'].format(target=task['target'], **level),
                goal_scope='curriculum_stage', official_evaluation=False)


class Status(str, Enum):
    IN_PROGRESS = 'in_progress'
    CURRICULUM_SUCCESS = 'curriculum_success'
    UNAVAILABLE = 'unavailable'


class Stage(str, Enum):
    ACQUIRE_RIGHT = 'acquire_right'
    HOLD_RIGHT = 'hold_right'
    TRANSFER = 'transfer'
    HOLD_LEFT = 'hold_left'
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
    right_only_elapsed_s: float
    left_only_elapsed_s: float
    left_only_retained: bool
    handover_contact: str
    final_ack_action_id: str | None
    reason: str | None
    native_success_seen: bool
    raw_native_final_flag: bool | None
    curriculum_success: bool
    full_task_success: bool = False
    official_success: bool = False

    def host_dict(self) -> dict[str, Any]:
        """Host evidence only; do not merge this into an actor observation."""
        return asdict(self)


class HandoverC1Gate:
    """A fresh gate per reset; no API for importing another episode's credit.

    A verified right-only interval survives a supported handover (one opposed
    grasp plus receiver/giver contact is enough; two opposed grasps also work).
    Neither bilateral contact nor an unqualified left-only interval can create
    the right prerequisite. Loss of all opposed grasps, support contact, loss of
    clearance or standing revokes the entire current chain immediately.
    """

    REQUIRED = frozenset((
        'time', 'reset_id', 'bottom_clearance_m', 'grasped_sides',
        'touching_hands', 'nonhand_support', 'container_contact',
        'standing_ok', 'native_success', 'action_id', 'command_complete',
    ))

    def __init__(self, reset_id: str, binding: Mapping[str, Any] | None = None):
        if not isinstance(reset_id, str) or not reset_id.strip():
            raise ValueError('A nonempty fresh host reset identity is required')
        expected = contract()
        if binding is not None and binding != expected:
            raise ValueError('Only the exact published Handover PlaceBack C1 is admitted')
        self.binding = copy.deepcopy(expected)
        self._level = copy.deepcopy(expected['criteria'])
        self.reset_id = reset_id
        self.last_time: float | None = None
        self.native_seen = False
        self.native_final: bool | None = None
        self.error: str | None = None
        self._clear_chain()

    def _clear_chain(self) -> None:
        self.right_since: float | None = None
        self.left_since: float | None = None
        self.right_verified_at: float | None = None

    @staticmethod
    def _finite(value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)

    @staticmethod
    def _sides(value: Any) -> set[str] | None:
        if not isinstance(value, (list, tuple, set, frozenset)):
            return None
        if any(not isinstance(x, str) or x not in ('left', 'right') for x in value):
            return None
        if len(set(value)) != len(value):
            return None
        return set(value)

    def _result(self, status: Status, stage: Stage, *, reason: str | None = None,
                contact: str = 'none', ack: str | None = None) -> HostProgress:
        now = self.last_time
        right_s = now-self.right_since if now is not None and self.right_since is not None else 0.
        left_s = now-self.left_since if now is not None and self.left_since is not None else 0.
        left_ok = self.right_verified_at is not None and left_s >= self._level['left_only_hold_s']-1e-9
        return HostProgress(
            status=status, stage=stage, reset_id=self.reset_id, time=now,
            right_prerequisite=self.right_verified_at is not None,
            right_verified_at=self.right_verified_at,
            right_only_elapsed_s=right_s, left_only_elapsed_s=left_s,
            left_only_retained=left_ok, handover_contact=contact,
            final_ack_action_id=ack, reason=reason,
            native_success_seen=self.native_seen, raw_native_final_flag=self.native_final,
            curriculum_success=status == Status.CURRICULUM_SUCCESS,
        )

    def _unavailable(self, reason: str) -> HostProgress:
        # A missing observation breaks proof of continuity. Do not recover by
        # silently joining observations on either side of an unknown interval.
        self.error = reason
        self._clear_chain()
        return self._result(Status.UNAVAILABLE, Stage.UNAVAILABLE, reason=reason)

    def update(self, sample: Mapping[str, Any]) -> HostProgress:
        if self.error is not None:
            return self._result(Status.UNAVAILABLE, Stage.UNAVAILABLE, reason=self.error)
        if not isinstance(sample, Mapping) or not self.REQUIRED <= sample.keys():
            return self._unavailable('missing_host_signal')
        if (not self._finite(sample['time']) or not self._finite(sample['bottom_clearance_m'])
                or sample['time'] < 0
                or any(type(sample[k]) is not bool for k in (
                    'nonhand_support', 'container_contact', 'standing_ok',
                    'native_success', 'command_complete'))
                or (sample['action_id'] is not None and (
                    not isinstance(sample['action_id'], str) or not sample['action_id'].strip()))
                or (sample['command_complete'] and not sample['action_id'])):
            return self._unavailable('invalid_host_sample')
        sides = self._sides(sample['grasped_sides'])
        touch = self._sides(sample['touching_hands'])
        if sides is None or touch is None or not sides <= touch:
            return self._unavailable('invalid_hand_contact_sample')
        if sample['reset_id'] != self.reset_id:
            return self._unavailable('reset_changed')
        now = float(sample['time'])
        if self.last_time is not None and now < self.last_time:
            return self._unavailable('clock_regressed')
        self.last_time = now
        self.native_final = sample['native_success']
        self.native_seen |= self.native_final

        loss = (
            'standing_lost' if not sample['standing_ok'] else
            'nonhand_support' if sample['nonhand_support'] or sample['container_contact'] else
            'whole_object_clearance_lost' if sample['bottom_clearance_m'] <= self._level['full_object_clearance_m'] else
            'opposed_grasp_lost' if not sides else None
        )
        if loss is not None:
            self._clear_chain()
            return self._result(Status.IN_PROGRESS, Stage.ACQUIRE_RIGHT, reason=loss)

        right_only = sides == touch == {'right'}
        left_only = sides == touch == {'left'}
        contact = 'right_only' if right_only else 'left_only' if left_only else 'handover_contact'
        if right_only:
            self.left_since = None
            if self.right_since is None:
                self.right_since = now
            if (self.right_verified_at is None
                    and now-self.right_since >= self._level['right_only_hold_s']-1e-9):
                self.right_verified_at = now
            stage = Stage.TRANSFER if self.right_verified_at is not None else Stage.HOLD_RIGHT
            return self._result(Status.IN_PROGRESS, stage, contact=contact)

        self.right_since = None  # Handover contact cannot accumulate right-only time.
        if self.right_verified_at is None:
            self.left_since = None
            return self._result(Status.IN_PROGRESS, Stage.ACQUIRE_RIGHT,
                                reason='right_prerequisite_missing', contact=contact)
        if not left_only:
            self.left_since = None  # Giver contact cancels left-only duration.
            return self._result(Status.IN_PROGRESS, Stage.TRANSFER, contact=contact)

        if self.left_since is None:
            self.left_since = now
        if now-self.left_since < self._level['left_only_hold_s']-1e-9:
            return self._result(Status.IN_PROGRESS, Stage.HOLD_LEFT, contact=contact)
        if not sample['command_complete']:
            return self._result(Status.IN_PROGRESS, Stage.AWAIT_FINAL_ACK, contact=contact)
        return self._result(Status.CURRICULUM_SUCCESS, Stage.COMPLETE,
                            contact=contact, ack=sample['action_id'])
