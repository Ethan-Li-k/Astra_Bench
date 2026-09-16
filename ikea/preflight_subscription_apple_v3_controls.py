"""Offline new-boundary admission and public projection checks. No activation."""
import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import run_subscription_apple_v3 as runner
import policy_support_apple_v3 as support

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'engineering-evidence/subscription-apple-v3-controls'
OUT.mkdir(exist_ok=False)

def fixture(name):
    root=OUT/name;root.mkdir()
    ep=root/'campaign/apple-prior';ep.mkdir(parents=True)
    ready=dict(ready=True,previous_episode='apple-prior',previous_terminal_kind='physical_budget',
        previous_skill_preserved=True,operator_confirmed_previous_process_exit=True,source_sha256={})
    result=dict(terminal_kind='physical_budget',error=None)
    review=dict(audited_task_success=False)
    for p,d in [(root/'subscription-apple-v3-READY.json',ready),(ep/'result.json',result),(ep/'independent-review.json',review)]:
        p.write_text(json.dumps(d))
    return root,ep

def change(path,**kwargs):
    value=json.loads(path.read_text());value.update(kwargs);path.write_text(json.dumps(value))

def host_fixture(name):
    root=OUT/name;root.mkdir()
    web=dict(tasks={'apple':dict(physical_attempts=0,audited_successes=0,verification='unverified')},
        last_actual_progress_at='last-physical',last_progress_at='last-engineering',audited_successes=1)
    (root/'web-progress.json').write_text(json.dumps(web))
    h=support.Host.__new__(support.Host)
    h.backend=NS(data=NS(time=25.));h.episode_start_sim_s=5.;h.actions=4;h.episode_id='apple-synthetic';h.finished=False
    return root,h

class Checks(unittest.TestCase):
    def test_sealed_physical_budget_with_audit_admitted(self):
        root,_=fixture('admitted');self.assertTrue(runner.admitted_configuration(root)['ready'])
    def test_live_result_absent_rejected(self):
        root=OUT/'no-result';root.mkdir()
        (root/'subscription-apple-v3-READY.json').write_text(json.dumps(dict(ready=True,previous_episode='apple-live')))
        with self.assertRaises(FileNotFoundError):runner.admitted_configuration(root)
    def test_usage_limit_is_not_automatic_next_episode(self):
        root,ep=fixture('usage');change(ep/'result.json',terminal_kind='usage_limit',error={'message':'usageLimitExceeded'})
        with self.assertRaisesRegex(RuntimeError,'Usage limit'):runner.admitted_configuration(root)
    def test_unknown_system_error_requires_boundary_review(self):
        root,ep=fixture('system');change(ep/'result.json',terminal_kind='system',error={'message':'EOF'})
        with self.assertRaisesRegex(RuntimeError,'explicit boundary'):runner.admitted_configuration(root)
    def test_task_success_not_repeated(self):
        root,ep=fixture('success');change(ep/'independent-review.json',audited_task_success=True)
        with self.assertRaisesRegex(RuntimeError,'already passed'):runner.admitted_configuration(root)
    def test_unconfirmed_old_process_exit_rejected(self):
        root,_=fixture('old-process');change(root/'subscription-apple-v3-READY.json',operator_confirmed_previous_process_exit=False)
        with self.assertRaisesRegex(RuntimeError,'process exit'):runner.admitted_configuration(root)
    def test_projection_fields_use_one_live_tuple(self):
        root,h=host_fixture('projection')
        with patch.object(support,'ROOT',root):h.progress('physical_action_completed')
        web=json.loads((root/'web-progress.json').read_text());actor=json.loads((root/'actor-progress.json').read_text())
        self.assertEqual(web['simulated_seconds'],actor['sim_s']);self.assertEqual(web['actions'],actor['actions'])
        self.assertEqual(web['metric_snapshot']['simulated_seconds'],web['sim_s'])
        self.assertEqual(web['backend'],'MuJoCo');self.assertEqual(web['last_progress_at'],actor['at'])
        self.assertIsNone(web['original_usd_joints']);self.assertEqual(web['physical_attempts'],0)
    def test_inference_and_action_start_do_not_fabricate_progress(self):
        root,h=host_fixture('waiting')
        with patch.object(support,'ROOT',root):
            h.progress('inference_waiting');h.progress('action_executing')
        web=json.loads((root/'web-progress.json').read_text());actor=json.loads((root/'actor-progress.json').read_text())
        self.assertEqual(web['last_actual_progress_at'],'last-physical');self.assertEqual(web['last_progress_at'],'last-engineering')
        self.assertEqual(web['state'],'action_executing');self.assertFalse(actor['physics_paused'])
    def test_rejected_no_execution_does_not_refresh_progress(self):
        root,h=host_fixture('rejected')
        with patch.object(support,'ROOT',root),patch.object(support.LearningHost,'dispatch',return_value={'no_execution':True}):
            self.assertTrue(h.dispatch('scalebfm_act',{})['no_execution'])
        web=json.loads((root/'web-progress.json').read_text())
        self.assertEqual(web['last_actual_progress_at'],'last-physical')
    def test_partial_action_exception_keeps_progress_and_classification(self):
        root,h=host_fixture('partial')
        def partial(self,name,args):self.backend.data.time+=.02;raise RuntimeError('synthetic partial execution')
        with patch.object(support,'ROOT',root),patch.object(support.LearningHost,'dispatch',new=partial):
            with self.assertRaisesRegex(RuntimeError,'partial'):h.dispatch('scalebfm_act',{})
        web=json.loads((root/'web-progress.json').read_text())
        self.assertEqual(web['phase'],'physical_action_partial');self.assertAlmostEqual(web['simulated_seconds'],20.02)

with (OUT/'tests.log').open('w') as stream:
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
files=['run_subscription_apple_v3.py','policy_support_apple_v3.py','runtime-apple-v3/manifest.json','fridge_physical_guard_v1.py']
result=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=tests.wasSuccessful(),tests_run=tests.testsRun,
    models_started=0,physics_steps=0,activation_created=False,final_skill_missing_by_design=True,
    remaining='After prior episode seal/exit/audit: preserve final actor skill, merge new conditions, validate full prompt and actual updater, freeze exact hashes; then and only then READY.',
    source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)
