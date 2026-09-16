"""Named model_38000/DEX3 command compiler for SIMPLE's G1 action."""
from __future__ import annotations

import numpy as np


class SimpleActionBridge:
    """Compile one 50 Hz target without owning or advancing a SIMPLE env."""

    def __init__(self, policy_joint_names, simple_body_joint_names,
                 simple_hand_joint_names, *, action_factory=None):
        self.policy_names = tuple(policy_joint_names)
        self.body_names = tuple(simple_body_joint_names)
        self.hand_names = tuple(simple_hand_joint_names)
        for label, names in (('policy', self.policy_names),
                             ('body', self.body_names),
                             ('hand', self.hand_names)):
            if not names or len(names) != len(set(names)):
                raise ValueError(f'{label} joint names must be nonempty and unique')
        if set(self.policy_names) != set(self.body_names):
            raise ValueError('policy and SIMPLE body joint names must match exactly')
        if not all(name.startswith(('left_', 'right_')) for name in self.hand_names):
            raise ValueError('SIMPLE hand joint names must declare left/right side')
        self.body_from_policy = np.array(
            [self.policy_names.index(name) for name in self.body_names], dtype=int)
        self.left_names = tuple(name for name in self.hand_names
                                if name.startswith('left_'))
        self.right_names = tuple(name for name in self.hand_names
                                 if name.startswith('right_'))
        if not self.left_names or not self.right_names:
            raise ValueError('SIMPLE hand joint names require both sides')
        if action_factory is None:
            from simple.core.action import ActionCmd
            action_factory = ActionCmd
        self.action_factory = action_factory

    def compile(self, q29_policy_order, finger_targets_by_name):
        q = np.asarray(q29_policy_order, dtype=float)
        if q.shape != (len(self.policy_names),) or not np.isfinite(q).all():
            raise ValueError('q target must be finite and match policy joint names')
        if (not isinstance(finger_targets_by_name, dict)
                or set(finger_targets_by_name) != set(self.hand_names)):
            raise ValueError('finger targets must contain exactly the SIMPLE hand joint names')
        fingers = np.array([finger_targets_by_name[name] for name in self.hand_names],
                           dtype=float)
        if not np.isfinite(fingers).all():
            raise ValueError('finger targets must be finite')
        by_name = dict(zip(self.hand_names, fingers))
        return self.action_factory(
            'decoupled_wbc',
            target_q=q[self.body_from_policy],
            left_hand_q=np.array([by_name[name] for name in self.left_names]),
            right_hand_q=np.array([by_name[name] for name in self.right_names]),
        )
