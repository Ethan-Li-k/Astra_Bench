"""Read-only dashboard fixtures; never launch a model or physical environment."""
import json
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dashboard import Dashboard
from simple_breadth import project
from rsi.simple_coverage import snapshot as canonical_snapshot
from tools.audit_simple_campaigns import episode_status

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'artifacts/R019/simple-parallel-coverage-20260917/web'
ENV1 = 'simple/G1WholebodyHandoverSimToRealTeleop-v0'
ENV2 = 'simple/G1WholebodyHandoverPlaceBackSimToRealTeleop-v0'


class BreadthTests(unittest.TestCase):
    def setUp(self):
        # Keep fixtures for review, all inside RSI.
        self.root = Path(tempfile.mkdtemp(prefix='fixture-breadth-', dir=OUT))
        self.board = Dashboard(self.root)
        self.policy = dict(active=True, max_new_attempts_per_task=2,
                           priority=[dict(env_id=ENV1, state='ready', label='交接', reuse='历史经验')])
        self.write('ref/tasks/simple-easy-coverage.json', self.policy)

    def write(self, path, data):
        path = self.root/path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return path

    def episode(self, campaign='handover-sim-campaign', env=ENV1, number=1, actions=2):
        path = Path('artifacts/R019')/campaign/f'episode-{number:04d}'
        self.write(path/'agent/task_specification.json', dict(env_id=env, hidden_sentinel='do not publish'))
        self.write(path/'video/scene_setup.json', dict(env_id=env, reset_provenance=dict(
            reset_id=f'{campaign}-{number}', method='fresh_environment_reset')))
        if actions:
            self.write(path/f'rollout/episode/execution_{actions:04d}.json', dict(
                receipts=[dict(command_id='fixture-action', duration_s=1)], hidden_sentinel='do not publish'))
        return path

    def terminal(self, path, reviewed=None):
        self.write(path/'result.json', dict(episode_id=path.name, actions=28, success=True,
            native_outcome='success', skill_updated=True, codex_turns=1))
        self.write(path/'turn_001.json', dict(status='completed'))
        if reviewed is not None:
            self.write(path/'success_review.json', dict(audited_task_success=reviewed, independent_reset_verified=True))

    def snapshot(self):
        return project(self.board, self.board.snapshot(force=True))

    def test_projected_package_accepts_proactive_feedback_without_failure_cluster(self):
        from dashboard import hash_json
        from feedback_board import FeedbackBoard
        self.episode()
        task=self.snapshot()['tasks'][0]
        self.assertEqual(task['version'],hash_json({k:v for k,v in task.items() if k!='version'}))
        b=FeedbackBoard(self.board,self.root/'feedback',fixture=True);b.publish_packages([task])
        self.assertEqual(b.cases()['eligible_count'],0)
        r=b.submit(dict(request_id='coverage_feedback_fixture',task_id='simple',case_id=None,source_version=task['version'],text='synthetic fixture',choice='',user_timestamp='2026-09-17T00:00:00Z',correction_of=None))
        self.assertEqual(r['evidence_binding']['state'],'verified');self.assertTrue(r['status']['saved'])

    def test_first_episode_discovered_without_campaign_aggregate(self):
        path = self.episode()
        self.write(path/'public-progress.json', dict(episode_id=path.name, state='inference_waiting_no_deadline'))
        s = self.snapshot(); row = s['simple_coverage']['environments'][0]
        self.assertEqual((row['episode'], row['actions'], row['state']), ('episode-0001', 2, 'modelwaiting'))
        self.assertEqual(self.board.simple_catalog['handover-sim'][1], 'handover-sim-campaign')
        self.assertNotIn('hidden_sentinel', json.dumps(s))
        # A new episode wins over an old aggregate and old episode, with no refresh of that aggregate.
        self.write('artifacts/R019/campaign_audit.json', dict(campaigns=[]))
        self.episode(number=2, actions=3)
        self.assertEqual(self.snapshot()['simple_coverage']['environments'][0]['episode'], 'episode-0002')

    def test_terminal_overrides_later_stale_progress_and_needs_audit(self):
        path = self.episode(actions=28); self.terminal(path)
        self.write(path/'public-progress.json', dict(episode_id=path.name, state='action_executing', success=True))
        s = self.snapshot(); c = s['simple_coverage']; row = c['environments'][0]
        self.assertEqual(row['state'], 'review'); self.assertEqual(row['actions'], 28)
        self.assertEqual((c['completed_tasks'], c['pending_audit'], c['active_environments']), (0, 1, 0))
        self.assertEqual(row['last_action_at'], (self.root/path/'rollout/episode/execution_0028.json').stat().st_mtime)
        self.terminal(path, reviewed=False)
        self.assertEqual(self.snapshot()['simple_coverage']['environments'][0]['state'], 'audit-rejected')

    def test_audited_success_retires_exact_task_only(self):
        path = self.episode(); self.terminal(path, reviewed=True)
        self.policy['priority'].append(dict(env_id=ENV2, state='ready', label='放回', reuse='经验'))
        self.write('ref/tasks/simple-easy-coverage.json', self.policy)
        s = self.snapshot(); c = s['simple_coverage']
        self.assertEqual(c['completed_tasks'], 1); self.assertEqual(c['audited_successes'], 1)
        self.assertEqual([r['env_id'] for r in c['next']], [ENV2])
        self.assertTrue(c['environments'][0]['retired'])
        self.assertNotIn(ENV1, [r['native_env_id'] for r in s['tasks'][0]['subtasks']])
        self.assertIn('handover-sim', [r['id'] for r in s['tasks'][0]['history_subtasks']])
        self.assertEqual(c['completed'][0]['detail_id'], 'handover-sim')

    def test_second_parallel_admission_appears_without_owner_mapping(self):
        path = self.episode()
        self.write(path/'public-progress.json', dict(episode_id=path.name, state='inference_waiting'))
        self.assertEqual(len(self.snapshot()['simple_coverage']['environments']), 1)
        self.policy['priority'].append(dict(env_id=ENV2, state='ready', label='放回', reuse='经验'))
        self.write('ref/tasks/simple-easy-coverage.json', self.policy)
        other = self.episode('placeback-campaign', ENV2)
        self.write(other/'public-progress.json', dict(episode_id=other.name, state='action_executing'))
        c = self.snapshot()['simple_coverage']
        self.assertEqual(c['active_environments'], 2)
        self.assertEqual({r['state'] for r in c['environments']}, {'physicsrunning', 'modelwaiting'})
        self.assertEqual(len({r['environment_id'] for r in c['environments']}), 2)

    def test_management_preflight_and_weak_events_never_count(self):
        self.write('artifacts/R019/simple-parallel-coverage-20260917/supervisor-status.json', dict(state='complete', success=True))
        self.write('artifacts/easy-coverage-20260917/preflight/handover-sim/result.json', dict(status='passed', task_success_credit=False))
        self.assertEqual(self.snapshot()['simple_coverage']['environments'], [])
        path = self.episode(actions=0)
        self.write(path/'public-progress.json', dict(episode_id=path.name, state='complete', success=True))
        c = self.snapshot()['simple_coverage']
        self.assertEqual(c['completed_tasks'], 0); self.assertIsNone(c['environments'][0]['last_action_at'])
        self.terminal(path, reviewed=True)
        self.write(path/'turn_001.json', dict(status='failed'))
        self.assertEqual(self.snapshot()['simple_coverage']['completed_tasks'], 0)

    def test_unadmitted_mismatched_archive_and_symlink_excluded(self):
        path = self.episode(); self.terminal(path, reviewed=True)
        self.write(path/'video/scene_setup.json', dict(env_id=ENV2))
        self.assertEqual(self.snapshot()['simple_coverage']['environments'], [])
        real = self.root/'artifacts/R019/handover-sim-campaign'
        real.rename(self.root/'archive')
        real.symlink_to(self.root/'archive', target_is_directory=True)
        c = self.snapshot()['simple_coverage']
        self.assertEqual(c['environments'], []); self.assertEqual(c['completed_tasks'], 0)
        self.episode('unadmitted-campaign', ENV2)
        self.assertEqual(self.snapshot()['simple_coverage']['environments'], [])

    def test_file_symlinks_and_ambiguous_binding_rejected(self):
        path = self.episode()
        target = self.write('other.json', dict(env_id=ENV1))
        spec = self.root/path/'agent/task_specification.json'
        spec.rename(spec.with_suffix('.before')); spec.symlink_to(target)
        self.assertEqual(self.snapshot()['simple_coverage']['environments'], [])

    def test_open_video_not_probed_and_closed_video_signature_retained(self):
        path = self.episode()
        video = self.root/path/'video/episode.mp4'; video.write_bytes(b'not finalized')
        with patch('dashboard.subprocess.run') as probe:
            self.assertEqual(self.snapshot()['simple_coverage']['environments'][0]['videos'], [])
            probe.assert_not_called()
        self.terminal(path)
        with patch('dashboard.subprocess.run') as probe:
            probe.return_value.stdout = json.dumps(dict(streams=[dict(width=16, height=16)], format=dict(duration=1)))
            row = self.snapshot()['simple_coverage']['environments'][0]
            route = row['videos'][0]['url']; self.assertIsNotNone(self.board.media_file(route))
            video.write_bytes(b'changed recording')
            self.assertIsNone(self.board.media_file(route))

    def reset_bound_audit(self):
        """HandoverSim producer schema: full reset receipt, no redundant flag."""
        path = self.episode(actions=28)
        reset = dict(method='fresh_environment_reset', reset_id='fixture-independent-reset', seed=1,
            recorded_utc='2026-09-17T05:04:19.313460+00:00',
            launch=dict(boot_id='fixture-boot-id', pid=101, start_ticks=7174140),
            post_settle_sim_s=5.005, post_settle_qpos_qvel_sha256='7'*64,
            note='Reset invocation and process identity; not a success receipt.')
        self.write(path/'video/scene_setup.json', dict(env_id=ENV1, reset_provenance=reset))
        self.write(path/'result.json', dict(episode_id=path.name, actions=28, success=True,
            native_outcome='success', skill_updated=True, codex_turns=1,
            turn_record_contract='codex-terminal-sequence-v1', codex_thread_id='fixture-thread',
            codex_turn_ids=['fixture-turn']))
        self.write(path/'turn_001.json', dict(id='fixture-turn', status='completed',
            _rsi_terminal=dict(contract='codex-terminal-sequence-v1', sequence=1,
                thread_id='fixture-thread', reset_id=reset['reset_id'])))
        review = dict(audited_task_success=True, task=ENV1, reset=copy.deepcopy(reset),
                      full_turn_and_skill_update=True)
        self.write(path/'success_review.json', review)
        return path, reset, review

    def test_full_reset_audit_schema_matches_canonical_and_retires(self):
        path, reset, review = self.reset_bound_audit()
        self.assertNotIn('independent_reset_verified', review)
        self.assertTrue(episode_status(self.root/path)['audited_task_success'])
        canonical = canonical_snapshot(self.root)
        c = self.snapshot()['simple_coverage']
        self.assertEqual((c['completed_tasks'], c['audited_successes']),
                         (canonical['completed_tasks'], canonical['audited_successes']))
        self.assertEqual((c['completed_tasks'], c['audited_successes'], c['pending_audit']), (1, 1, 0))
        row = c['environments'][0]
        self.assertEqual(row['state'], 'complete'); self.assertTrue(row['retired'])
        self.assertEqual(c['next'], [])
        self.assertEqual(review, json.loads((self.root/path/'success_review.json').read_text()))

    def test_reset_bound_schema_mismatches_do_not_claim_pending_audit(self):
        path, reset, review = self.reset_bound_audit()
        changes = dict(reset_id='another-reset', seed=2, method='replay',
            launch={**reset['launch'], 'start_ticks':1}, post_settle_qpos_qvel_sha256='8'*64)
        for field, value in changes.items():
            with self.subTest(field=field):
                altered = copy.deepcopy(review); altered['reset'][field] = value
                self.write(path/'success_review.json', altered)
                c = self.snapshot()['simple_coverage']
                self.assertEqual(c['completed_tasks'], 0)
                self.assertEqual(c['pending_audit'], 0)
                self.assertEqual(c['environments'][0]['state'], 'audit-unverified')
        for field in changes:
            with self.subTest(missing=field):
                altered = copy.deepcopy(review); del altered['reset'][field]
                self.write(path/'success_review.json', altered)
                self.assertEqual(self.snapshot()['simple_coverage']['completed_tasks'], 0)

    def test_reset_bound_schema_still_requires_complete_host_terminal_and_dedup(self):
        path, reset, review = self.reset_bound_audit()
        result_path = path/'result.json'; result = json.loads((self.root/result_path).read_text())
        for key, value in [('success',False), ('skill_updated',False), ('actions',0), ('error','fixture error')]:
            with self.subTest(field=key):
                self.write(result_path, {**result, key:value})
                self.assertFalse(episode_status(self.root/path)['audited_task_success'])
                self.assertEqual(self.snapshot()['simple_coverage']['completed_tasks'], 0)
        self.write(result_path, result)
        turn = json.loads((self.root/path/'turn_001.json').read_text())
        self.write(path/'turn_001.json', {**turn, 'status':'failed'})
        self.assertEqual(self.snapshot()['simple_coverage']['completed_tasks'], 0)
        self.write(path/'turn_001.json', turn)
        other = self.episode(number=2, actions=28)
        self.write(other/'video/scene_setup.json', dict(env_id=ENV1, reset_provenance=reset))
        self.write(other/'success_review.json', review)
        self.write(other/'result.json', {**result, 'episode_id':other.name})
        self.write(other/'turn_001.json', turn)
        self.assertEqual(self.snapshot()['simple_coverage']['audited_successes'], 1)

    def test_reset_bound_audit_file_symlink_is_never_followed(self):
        path, reset, review = self.reset_bound_audit()
        original = self.root/path/'success_review.json'
        target = original.with_suffix('.before'); original.rename(target); original.symlink_to(target)
        self.assertEqual(self.snapshot()['simple_coverage']['completed_tasks'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
