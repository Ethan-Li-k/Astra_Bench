"""Offline admission checks for one new subscription episode; no model or physics."""
import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import run_subscription_apple_v2 as runner
from validate_skill_update_contract import validate

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'engineering-evidence/subscription-apple-v2-preflight'
OUT.mkdir(exist_ok=False)

class Transport:
    def __init__(self,status='completed'):self.status=status;self.starts=0;self.waits=[];self.timeouts=[]
    def notify(self,*a):pass
    def request(self,method,params,timeout):
        self.timeouts.append(timeout)
        if method=='initialize':return {}
        if method=='thread/start':return dict(thread={'id':'synthetic-same-thread'},model='gpt-6-astra',reasoningEffort='xhigh')
        if method=='turn/start':
            self.starts+=1;return {'turn':{'id':f'turn-{self.starts}'}}
        raise AssertionError(method)
    def next_message(self,timeout):
        self.waits.append(timeout)
        return dict(method='turn/completed',params=dict(threadId='synthetic-same-thread',
            turn=dict(id=f'turn-{self.starts}',status=self.status,error='usageLimitExceeded' if self.status!='completed' else None)))

class Checks(unittest.TestCase):
    def test_full_wait_same_thread_after_completed_turn(self):
        t=Transport();host=NS(tool_specs=lambda:[])
        a=runner.CodexPolicyAdapter(t,host,OUT/'adapter-test',developer_instructions='synthetic',normal_tools=True,timeout=None)
        a.connect();a.run_turn('first');a.run_turn('continue current observation')
        self.assertEqual(a.thread_id,'synthetic-same-thread');self.assertEqual(t.starts,2)
        self.assertIsNone(a.turn_id);self.assertEqual(t.waits,[None,None]);self.assertTrue(all(x is None for x in t.timeouts))
    def test_usage_failure_propagates_without_retry(self):
        t=Transport('failed');a=runner.CodexPolicyAdapter(t,NS(tool_specs=lambda:[]),OUT/'usage-test',developer_instructions='synthetic',timeout=None)
        a.connect()
        with self.assertRaisesRegex(RuntimeError,'usageLimitExceeded'):a.run_turn('once')
        self.assertEqual(t.starts,1)
    def test_physical_budget_rejects_before_action(self):
        h=runner.SubscriptionHost.__new__(runner.SubscriptionHost)
        h.finished=False;h.backend=NS(active=None,data=NS(time=244.),continuous_chunks_enabled=True,
            physics_substeps=5,model=NS(opt=NS(timestep=.004)))
        h.episode_start_sim_s=5.;h.max_episode_steps=12000;h.rollout_root=OUT/'guard';h.rollout_root.mkdir()
        obs=h.rollout_root/'obs.json';obs.write_text('{}')
        h.harness=NS(latest_path=obs,evaluator=NS(outcome=lambda b:'in_progress'))
        result=h.dispatch('scalebfm_act',{'response':{'trajectory':[{'duration_s':1.}]}})
        self.assertTrue(result['no_execution']);self.assertTrue(h.finished)
        self.assertEqual(h.backend.data.time,244.);self.assertEqual(result['next_call']['tool'],'skill_update')

suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
with (OUT/'tests.log').open('w') as stream:
    test_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
skill=ROOT/'skills/apple-grasp-v2/SKILL.md'
validation=validate(skill.read_text(),runner.RUNTIME+runner.TURN_PROMPT,OUT/'updater')
files=['run_subscription_apple_v2.py','policy_support_apple_v2.py','api-apple-v2/transport_gate.py',
    'api-apple-v2/history_bound.py','runtime-apple-v2/manifest.json','skills/apple-grasp-v2/SKILL.md',
    'experience-candidates/apple-0001-public-failure-v1.json','experience-candidates/apple-0001-ankle-hold-v1.json',
    'downstream-reference/H001-user-feedback-004.json']
passed=test_result.wasSuccessful() and validation['accepted']
result=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=passed,
    tests_run=test_result.testsRun,length=validation['length'],actual_updater_accepted=validation['accepted'],
    models_started=0,simulations_started=0,api_requests=0,
    source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));raise SystemExit(0 if passed else 1)
