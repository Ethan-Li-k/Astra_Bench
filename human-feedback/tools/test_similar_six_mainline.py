import json
import tempfile
import unittest
from pathlib import Path
from dashboard import Dashboard, SIX_TASKS, hash_json
from simple_breadth import project
from similar_six_mainline import OVERRIDE


class MainlineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir='/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/similar-six-mainline-20260917'))
        self.board = Dashboard(self.root)
        self.write(OVERRIDE, dict(id='similar-train-six-isaac-20260917',
            mode='similar_training_fixed_six_isaac', recorded_at='2026-09-17T13:20:00Z'))
        self.write('artifacts/harness-reset-20260917/plan.json', dict(
            id='simple-60x5-24h-20260917', started_at=1000, deadline_at=87400, target_tasks=60,
            minimum_complete_attempts_per_task=5, target_complete_attempts=300, initial_parallel_target=8))

    def write(self, name, doc):
        p = self.root/name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc))

    def snapshot(self):
        return project(self.board, self.board.snapshot(force=True))

    def test_latest_scope_replaces_old_300_goal_and_preserves_exact_six(self):
        s = self.snapshot(); c = s['simple_coverage']
        self.assertIsNone(c['goal'])
        self.assertIsNone(c['window_metrics'])
        self.assertEqual({r['env_id'] for r in c['mainline']['tests']}, set(SIX_TASKS.values()))
        self.assertTrue(c['mainline']['historical_success_reuse_only'])
        self.assertIn('已有成功任务不复试', s['tasks'][0]['scope_notice'])
        self.assertEqual(s['tasks'][0]['version'], hash_json({k:v for k,v in s['tasks'][0].items() if k!='version'}))

    def test_old_active_lane_is_closeout_not_new_training(self):
        env = SIX_TASKS['Handover']; ep = Path('artifacts/R019/handover-campaign/episode-0002')
        self.write(ep/'agent/task_specification.json', dict(env_id=env))
        self.write(ep/'video/scene_setup.json', dict(env_id=env,
            reset_provenance=dict(recorded_utc=1001, reset_id='old-plan')))
        self.write(ep/'rollout/episode/execution_0001.json', dict(receipts=[dict(command_id='ack', duration_s=1)]))
        self.write('artifacts/harness-reset-20260917/execution/status.json', dict(
            plan_id='simple-60x5-24h-20260917', started_at=1000, updated_at=1100,
            lanes=[dict(env_id=env, episode=str(self.root/ep), state='acting', actions=1)]))
        c = self.snapshot()['simple_coverage']
        self.assertEqual(len(c['environments']), 1)
        self.assertIn('旧计划收尾', c['environments'][0]['state_label'])
        self.assertIn('非新主线', c['environments'][0]['state_label'])
        self.assertEqual(c['formal_scheduling'], 'not_started')

    def test_closed_receipt_removes_only_matching_old_lane(self):
        env = SIX_TASKS['Handover']; ep = Path('artifacts/R019/handover-campaign/episode-0002')
        self.write(ep/'agent/task_specification.json', dict(env_id=env))
        self.write(ep/'video/scene_setup.json', dict(env_id=env,
            reset_provenance=dict(recorded_utc=1001, reset_id='old-plan')))
        lane = dict(env_id=env, episode=str(self.root/ep), state='acting', actions=1,
                    closed=True, unsettled_requests=[])
        self.write('artifacts/harness-reset-20260917/execution/status.json', dict(
            plan_id='simple-60x5-24h-20260917', started_at=1000, updated_at=1100, lanes=[lane]))
        self.write('artifacts/harness-reset-20260917/execution/strategy-stop/closed.json', dict(
            status='all_old_workers_closed', scheduler_stopped=True,
            all_current_requests_returned_complete=True, counts_as_task_failure=False, lanes=[lane]))
        s = self.snapshot(); c = s['simple_coverage']
        self.assertEqual(c['environments'], [])
        self.assertEqual(c['actual_parallel'], 0)
        self.assertTrue(s['tasks'][0]['history_subtasks'][0]['terminal'])
        self.assertIn('不计任务失败', s['tasks'][0]['history_subtasks'][0]['state_label'])

    def test_selected_training_rejects_historical_success_overlap(self):
        doc = dict(test_tasks=[dict(env_id=v) for v in SIX_TASKS.values()],
            historical_success_exclusions=[dict(env_id='simple/old-success')],
            training_candidates=[dict(env_id='simple/old-success', label='Old',
                already_succeeded=False, selected_for_minimum_stage=True)])
        self.write('artifacts/six-transfer-20260917/task-split.json', doc)
        self.assertEqual(self.snapshot()['simple_coverage']['mainline']['selected_training'], [])

    def test_new_training_uses_new_plan_episode_and_counts(self):
        env = 'simple/G1WholebodyTabletopGraspVariant1MP-v0'
        ep = Path('artifacts/six-transfer-20260917/execution/campaigns/G1WholebodyTabletopGraspVariant1MP-campaign/episode-0001')
        self.write('artifacts/six-transfer-20260917/plan.json', dict(id='new-mainline', initial_training_parallelism=2))
        self.write('artifacts/six-transfer-20260917/task-split.json', dict(
            test_tasks=[dict(env_id=v) for v in SIX_TASKS.values()], historical_success_exclusions=[],
            training_candidates=[dict(env_id=env, label='Grasp Variant1', already_succeeded=False,
                selected_for_minimum_stage=True, minimum_complete_attempts=5)]))
        self.write(ep/'agent/task_specification.json', dict(env_id=env))
        self.write(ep/'video/scene_setup.json', dict(env_id=env,
            reset_provenance=dict(recorded_utc=1001, reset_id='new-reset')))
        self.write(ep/'rollout/episode/execution_0001.json', dict(receipts=[dict(command_id='ack', duration_s=1)]))
        self.write('artifacts/six-transfer-20260917/execution/status.json', dict(
            plan_id='new-mainline', started_at=1000, updated_at=1100,
            lanes=[dict(env_id=env, episode=str(self.root/ep), real_process_alive=True, actions=1)],
            tasks=[dict(env_id=env, complete_attempts=0)], totals=dict(complete_attempts=0)))
        s=self.snapshot(); c=s['simple_coverage']
        self.assertTrue(c['new_mainline_execution'])
        self.assertEqual(c['live_workers'], 1)
        self.assertEqual(c['mainline']['training_counts']['complete_attempts'], 0)
        self.assertEqual(c['environments'][0]['reset_id'], 'new-reset')
        self.assertIn('新主线训练', c['environments'][0]['state_label'])
        self.assertEqual(s['tasks'][0]['version'],hash_json({k:v for k,v in s['tasks'][0].items() if k!='version'}))


if __name__ == '__main__':
    unittest.main()
