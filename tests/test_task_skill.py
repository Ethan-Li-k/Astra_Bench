import unittest

from rsi.task_skill import TaskSkillEvidence, assess_task_skill


class TaskSkillTests(unittest.TestCase):
    def test_draft_until_training_and_independent_evaluation_pass(self):
        base = dict(
            task_id='grasp_red_cube',
            contract_sha256='a' * 64,
            execution_profile_sha256='b' * 64,
            actor_observation='rgb_plus_named_robot_state',
            action_space='umi4_se3_plus_bimanual_gripper',
            training_successes=3,
            training_trials=5,
            evaluation_successes=0,
            evaluation_trials=0,
            privileged_actor_inputs=(),
            unresolved_gates=(),
        )
        candidate = assess_task_skill(TaskSkillEvidence(**base))
        self.assertEqual(candidate['status'], 'CANDIDATE')
        self.assertFalse(candidate['reusable_for_new_task_evaluation'])

        frozen = assess_task_skill(TaskSkillEvidence(
            **(base | {'evaluation_successes': 4, 'evaluation_trials': 5})))
        self.assertEqual(frozen['status'], 'FROZEN')
        self.assertTrue(frozen['reusable_for_new_task_evaluation'])

    def test_privileged_input_or_unresolved_gate_keeps_skill_draft(self):
        common = dict(
            task_id='grasp_red_cube', contract_sha256='a' * 64,
            execution_profile_sha256='b' * 64,
            actor_observation='rgb_plus_named_robot_state',
            action_space='umi4_se3_plus_bimanual_gripper',
            training_successes=5, training_trials=5,
            evaluation_successes=5, evaluation_trials=5,
        )
        privileged = assess_task_skill(TaskSkillEvidence(
            **common, privileged_actor_inputs=('cube_pose',), unresolved_gates=()))
        self.assertEqual(privileged['status'], 'DRAFT')
        gated = assess_task_skill(TaskSkillEvidence(
            **common, privileged_actor_inputs=(), unresolved_gates=('wrist_rotation',)))
        self.assertEqual(gated['status'], 'DRAFT')


if __name__ == '__main__':
    unittest.main()
