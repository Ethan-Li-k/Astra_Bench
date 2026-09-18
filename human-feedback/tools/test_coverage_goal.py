"""The page must not manufacture coverage or route a feedback submission to a model."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import Dashboard, hash_json
from coverage_goal import read_plan, read_execution
from simple_breadth import project
from feedback_board import FeedbackBoard

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'human-feedback/dashboard-upgrade/coverage-24h-20260917'
ENV = 'simple/G1WholebodyHandoverTeleop-v0'


class GoalTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=OUT))
        self.board = Dashboard(self.root)
        self.plan = dict(id='simple-60x5-24h-20260917', started_at=1000, deadline_at=87400,
            target_tasks=60, minimum_complete_attempts_per_task=5, target_complete_attempts=300,
            initial_parallel_target=4, preferred_route='api', model='gpt-6-astra', effort='xhigh')
        self.write('artifacts/harness-reset-20260917/plan.json', self.plan)
        self.write('ref/tasks/simple-easy-coverage.json', dict(active=True, max_new_attempts_per_task=2,
            priority=[dict(env_id=ENV, state='ready', label='交接', reuse='成功经验')]))

    def write(self, path, doc):
        p = self.root/path
        p.parent.mkdir(parents=True, exist_ok=True)
        pending = p.with_name(p.name+'.pending')
        pending.write_text(json.dumps(doc))
        pending.replace(p)  # Match the supervisor's atomic publication contract.
        return p

    def episode(self, number, at, terminal=False):
        p = Path('artifacts/R019/handover-campaign')/f'episode-{number:04}'
        self.write(p/'agent/task_specification.json', dict(env_id=ENV))
        self.write(p/'video/scene_setup.json', dict(env_id=ENV,
            reset_provenance=dict(recorded_utc=at, method='fresh_environment_reset', reset_id=str(number))))
        self.write(p/'rollout/episode/execution_0001.json', dict(receipts=[dict(duration_s=1)]))
        if terminal:
            self.write(p/'result.json', dict(episode_id=p.name, actions=1, success=True,
                native_outcome='success', skill_updated=True, codex_turns=1))
            self.write(p/'turn_001.json', dict(status='completed'))
            self.write(p/'success_review.json', dict(audited_task_success=True, independent_reset_verified=True))
        return p

    def snapshot(self):
        return project(self.board, self.board.snapshot(force=True))

    def test_plan_only_never_claims_zero_or_target_parallel_as_actual(self):
        c = self.snapshot()['simple_coverage']
        self.assertIsNone(c['window_metrics'])
        self.assertIsNone(c['actual_parallel'])
        self.assertEqual(c['goal']['target_complete_attempts'], 300)

    def test_invalid_goal_is_not_accepted(self):
        self.plan['target_complete_attempts'] = 299
        self.write('artifacts/harness-reset-20260917/plan.json', self.plan)
        self.assertIsNone(read_plan(self.board))

    def test_history_success_does_not_retire_new_attempt(self):
        self.episode(1, 500, terminal=True)
        self.episode(2, 1001)
        s = self.snapshot(); c = s['simple_coverage']
        self.assertEqual(c['completed_tasks'], 1)
        self.assertEqual(c['environments'][0]['episode'], 'episode-0002')
        self.assertFalse(c['environments'][0]['retired'])
        self.assertEqual(c['environments'][0]['goal'], 5)
        self.assertNotIn('成功后不再重试', s['tasks'][0]['summary'])
        self.assertIsNone(c['window_metrics'])

    def test_old_inflight_not_counted_as_new_window(self):
        self.episode(1, 900)
        row = self.snapshot()['simple_coverage']['environments'][0]
        self.assertFalse(row['window_eligible_reset'])
        self.assertTrue(row['historical'])

    def test_interrupted_unknown_request_moves_to_history_without_failure_credit(self):
        base = self.episode(2, 1001)
        self.write(base/'rollout/episode/execution_0005.json',
            dict(receipts=[dict(command_id='last-confirmed', duration_s=1)]))
        self.write(base/'infrastructure-stop.json', dict(
            state='infrastructure_interrupted_unknown_request', episode=str(self.root/base),
            complete_attempt=False, physical_failure=False, automatic_replay=False, unsettled_request=15))
        s = self.snapshot()
        self.assertEqual(s['simple_coverage']['environments'], [])
        row = s['tasks'][0]['history_subtasks'][0]
        self.assertEqual(row['actions'], 5)
        self.assertTrue(row['terminal'])
        self.assertFalse(row['complete_attempt'])
        self.assertIsNone(row['result_success'])
        self.assertIn('请求结果未知', row['state_label'])
        self.assertEqual(s['simple_coverage']['active_environments'], 0)

    def test_pre_dispatch_stop_must_match_reset(self):
        base = self.episode(2, 1001)
        receipt = dict(complete_attempt=False, no_request_sent=True, actions=0, reset_id='wrong')
        self.write(base/'infrastructure-stop.json', receipt)
        self.assertEqual(len(self.snapshot()['simple_coverage']['environments']), 1)
        receipt['reset_id'] = '2'
        self.write(base/'infrastructure-stop.json', receipt)
        self.assertEqual(self.snapshot()['simple_coverage']['environments'], [])

    def test_new_package_feedback_hash_and_api_handoff(self):
        self.episode(1, 1001)
        task = self.snapshot()['tasks'][0]
        self.assertEqual(task['version'], hash_json({k:v for k,v in task.items() if k!='version'}))
        self.write('ref/tasks/account-policy.json', dict(api_enabled=True, preferred_route='api',
            main_account_allowed=True, auxiliary_accounts_allowed=False))
        b = FeedbackBoard(self.board, self.root/'feedback')
        b.publish_packages([task])
        with patch('feedback_board.subprocess.Popen') as launch, patch('feedback_board.subprocess.run') as run:
            answer = b.submit(dict(request_id='synthetic-api-goal-feedback', task_id='simple', case_id=None,
                source_version=task['version'], text='SYNTHETIC 用户建议', choice='', user_timestamp='2026-09-17T00:00:00Z', correction_of=None))
            launch.assert_not_called(); run.assert_not_called()
        self.assertEqual(answer['status']['handoff'], 'authorized_owner_inbox')
        self.assertEqual(answer['status']['priority'], 'highest')
        self.assertFalse(answer['status']['delivery_uncertain'])
        self.assertIsNone(answer['status']['actual_loaded'])

    def status_fixture(self):
        ids = [f'simple/FixtureTask{i}-v0' for i in range(60)]
        self.write('artifacts/harness-reset-20260917/task-inventory/exact60.json',
                   dict(tasks=[dict(env_id=i) for i in ids]))
        status = dict(updated_at=1100, plan_id=self.plan['id'], started_at=1000,
            lanes=[dict(env_id=ids[0], state='ready', pid=100, route='api')],
            tasks=[dict(env_id=ids[0], complete_attempts=5, successes=1)],
            totals=dict(complete_attempts=5, attempted_tasks=1, tasks_at_least_five=1))
        return status

    def test_supervisor_totals_are_projected_but_ready_lane_is_not_running(self):
        status = self.status_fixture()
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        s = read_execution(self.board, self.plan)
        self.assertEqual(s['window_metrics']['complete_attempts'], 5)
        self.assertIsNone(s['actual_parallel'])
        self.assertFalse(s['reported_lanes'][0]['reported_running'])

    def test_process_counts_do_not_call_paused_worker_acting(self):
        status = self.status_fixture()
        status['parallel_target'] = 4
        status['lanes'] = [dict(env_id=f'simple/FixtureTask{i}-v0', real_process_alive=True,
            service_paused=(i == 0), actions=(0 if i == 0 else 1), pid=100+i) for i in range(4)]
        status['totals'].update(active_lanes=4, acting_lanes=3, service_paused_lanes=1)
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        s = read_execution(self.board, self.plan)
        self.assertEqual(s['actual_parallel'], 3)
        self.assertEqual(s['live_workers'], 4)
        self.assertEqual(s['paused_workers'], 1)
        status['totals']['acting_lanes'] = 4
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        self.assertIsNone(read_execution(self.board, self.plan)['actual_parallel'])

    def test_duplicate_ids_and_wrong_window_do_not_gain_credit(self):
        status = self.status_fixture()
        status['tasks'] *= 2
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        self.assertIsNone(read_execution(self.board, self.plan)['window_metrics'])
        status['tasks'] = status['tasks'][:1]
        status['started_at'] = 900
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        self.assertIsNone(read_execution(self.board, self.plan)['window_metrics'])

    def test_inconsistent_aggregate_does_not_gain_credit(self):
        status = self.status_fixture()
        status['totals']['complete_attempts'] = 10
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        self.assertIsNone(read_execution(self.board, self.plan)['window_metrics'])

    def test_missing_explicit_window_binding_does_not_gain_credit(self):
        status = self.status_fixture()
        del status['plan_id']
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        self.assertIsNone(read_execution(self.board, self.plan)['window_metrics'])

    def test_same_attempt_total_but_wrong_coverage_does_not_gain_credit(self):
        status = self.status_fixture()
        status['totals'].update(attempted_tasks=2, tasks_at_least_five=0)
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        self.assertIsNone(read_execution(self.board, self.plan)['window_metrics'])

    def test_rejected_launch_is_displayed_as_blocked_not_active(self):
        status = self.status_fixture()
        status.update(stage='automatic_review_blocked', actual_parallel=0, tasks=[], lanes=[],
            totals=dict(complete_attempts=0, attempted_tasks=0, tasks_at_least_five=0))
        self.write('artifacts/harness-reset-20260917/execution/status.json', status)
        s = self.snapshot()
        self.assertEqual(s['simple_coverage']['actual_parallel'], 0)
        self.assertIn('自动审批拒绝', s['tasks'][0]['problem'])
        self.assertEqual(s['tasks'][0]['state'], 'infraerror')

    def test_new_supervisor_campaign_is_visible_without_counting_as_complete(self):
        uid = 'g1_wholebody_handover_teleop'
        self.write('artifacts/harness-reset-20260917/task-inventory/exact60.json',
            dict(tasks=[dict(env_id=ENV, task_uid=uid)]))
        base = Path('artifacts/harness-reset-20260917/execution/campaigns')/(uid+'-campaign')/'episode-0001'
        self.write(base/'agent/task_specification.json', dict(env_id=ENV))
        self.write(base/'video/scene_setup.json', dict(env_id=ENV,
            reset_provenance=dict(recorded_utc=1001, reset_id='fresh')))
        self.write(base/'rollout/episode/execution_0001.json',
            dict(receipts=[dict(command_id='ack-1', duration_s=1)]))
        c = self.snapshot()['simple_coverage']
        row = c['environments'][0]
        self.assertEqual(row['environment_id'], str(base))
        self.assertEqual(row['actions'], 1)
        self.assertEqual(row['id'], 'goal-g1-wholebody-handover-teleop')
        self.assertIsNone(c['window_metrics'])
        self.write('artifacts/harness-reset-20260917/execution/status.json', dict(
            plan_id=self.plan['id'], started_at=1000, updated_at=1100,
            lanes=[dict(env_id=ENV, episode=str(self.root/base), state='api_service_paused', actions=1)]))
        row = self.snapshot()['simple_coverage']['environments'][0]
        self.assertEqual(row['state'], 'infraerror')
        self.assertIn('原场景保留', row['state_label'])
        self.write(base/'video/scene_setup.json', dict(env_id='simple/Wrong-v0'))
        self.assertEqual(self.snapshot()['simple_coverage']['environments'], [])


if __name__ == '__main__':
    unittest.main()
