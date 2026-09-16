"""Admission state for a task-specific bundle built on the shared skill."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TaskSkillEvidence:
    task_id: str
    contract_sha256: str
    execution_profile_sha256: str
    actor_observation: str
    action_space: str
    training_successes: int
    training_trials: int
    evaluation_successes: int
    evaluation_trials: int
    privileged_actor_inputs: tuple[str, ...]
    unresolved_gates: tuple[str, ...]


def _is_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(
        char in '0123456789abcdef' for char in value)


def assess_task_skill(evidence, *, required_training_successes=3,
                      required_evaluation_trials=5,
                      required_evaluation_success_rate=.8):
    """Return a deterministic lifecycle verdict; never trains or promotes data."""
    reasons = []
    if not evidence.task_id or not _is_sha256(evidence.contract_sha256):
        reasons.append('identity_or_contract_missing')
    if not _is_sha256(evidence.execution_profile_sha256):
        reasons.append('execution_profile_missing')
    if evidence.actor_observation != 'rgb_plus_named_robot_state':
        reasons.append('actor_observation_contract_mismatch')
    if evidence.action_space != 'umi4_se3_plus_bimanual_gripper':
        reasons.append('action_space_contract_mismatch')
    if not (0 <= evidence.training_successes <= evidence.training_trials):
        reasons.append('invalid_training_counts')
    if not (0 <= evidence.evaluation_successes <= evidence.evaluation_trials):
        reasons.append('invalid_evaluation_counts')
    if evidence.privileged_actor_inputs:
        reasons.append('privileged_actor_input')
    if evidence.unresolved_gates:
        reasons.append('unresolved_gate')

    trained = evidence.training_successes >= required_training_successes
    evaluated = evidence.evaluation_trials >= required_evaluation_trials
    rate = (evidence.evaluation_successes / evidence.evaluation_trials
            if evidence.evaluation_trials else 0.)
    if reasons or not trained:
        status = 'DRAFT'
    elif evaluated and rate >= required_evaluation_success_rate:
        status = 'FROZEN'
    else:
        status = 'CANDIDATE'
    return {
        'schema': 'loco_manip.task_skill.v1',
        'status': status,
        'reusable_for_new_task_evaluation': status == 'FROZEN',
        'reasons': reasons,
        'evidence': asdict(evidence),
        'admission': {
            'required_training_successes': required_training_successes,
            'required_evaluation_trials': required_evaluation_trials,
            'required_evaluation_success_rate': required_evaluation_success_rate,
        },
    }
