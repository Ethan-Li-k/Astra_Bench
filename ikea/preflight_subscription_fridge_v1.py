"""Offline checks of the next-task candidate; no model or simulation dispatch."""
import datetime
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import run_subscription_fridge_v1 as runner

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'engineering-evidence/subscription-fridge-v1-preflight'
OUT.mkdir(exist_ok=False)

class Transport:
    def __init__(self,status='completed'):self.status=status;self.starts=0;self.waits=[];self.timeouts=[]
    def notify(self,*args):pass
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
        t=Transport();a=runner.CodexPolicyAdapter(t,NS(tool_specs=lambda:[]),OUT/'adapter-test',
            developer_instructions='synthetic',normal_tools=True,timeout=None)
        a.connect();a.run_turn('first');a.run_turn('continue same reset')
        self.assertEqual(a.thread_id,'synthetic-same-thread');self.assertEqual(t.starts,2)
        self.assertIsNone(a.turn_id);self.assertEqual(t.waits,[None,None]);self.assertTrue(all(x is None for x in t.timeouts))
    def test_usage_failure_propagates_without_retry(self):
        t=Transport('failed');a=runner.CodexPolicyAdapter(t,NS(tool_specs=lambda:[]),OUT/'usage-test',
            developer_instructions='synthetic',timeout=None)
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
        packet=h.dispatch('scalebfm_act',{'response':{'trajectory':[{'duration_s':1.}]}})
        self.assertTrue(packet['no_execution']);self.assertTrue(h.finished)
        self.assertEqual(h.backend.data.time,244.);self.assertEqual(packet['next_call']['tool'],'skill_update')
    def test_activation_absent_before_task_prerequisite(self):
        root=OUT/'missing';root.mkdir()
        with self.assertRaises(FileNotFoundError):runner.admitted_configuration(root)
        self.assertEqual(list(root.iterdir()),[])
    def test_public_success_cannot_override_rejected_independent_audit(self):
        root=OUT/'rejected';ep=root/'campaign/apple-synthetic';ep.mkdir(parents=True)
        (root/'fridge-subscription-v1-READY.json').write_text(json.dumps(dict(ready=True,
            prerequisite_apple_episode='apple-synthetic',source_sha256={})))
        (ep/'public-review.json').write_text('{"audited_success":true}')
        (ep/'independent-review.json').write_text('{"audited_task_success":false}')
        with self.assertRaisesRegex(RuntimeError,'Audited apple'):runner.admitted_configuration(root)
        self.assertFalse((root/'campaign/fridge-0001').exists())

with (OUT/'tests.log').open('w') as stream:
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
skill=ROOT/'skills/fridge-open-v1/SKILL.md'
length=runner.validate_policy_instructions(skill.read_text(),runner.RUNTIME+runner.TURN_PROMPT)
updater=OUT/'updater';updater.mkdir()
candidate=updater/'SKILL.md';candidate.write_text(skill.read_text())
evidence=updater/'synthetic-public-evidence.json';evidence.write_text('{"synthetic":true,"physical_actions":0,"success_credit":0}')
memory=runner.SkillMemory(updater/'memory',candidate);memory.runtime_instructions=runner.RUNTIME+runner.TURN_PROMPT
updated=memory.update(candidate.read_text(),'Synthetic interface check, no physical experience.',[str(evidence)],
    updater,'synthetic-preflight','not_started',change_summary='No live skill change')
loaded={x.__name__:inspect.getfile(x) for x in (runner.SkillMemory,runner.CodexPolicyAdapter,runner.FridgeEvaluator,runner.create_backend)}
frozen=all(Path(p).is_relative_to(ROOT/'runtime-fridge-v1') for p in loaded.values())
files=['run_subscription_fridge_v1.py','policy_support_fridge_v1.py','fridge_physical_guard_v1.py',
    'runtime-fridge-v1/manifest.json','skills/fridge-open-v1/SKILL.md']
result=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=tests.wasSuccessful() and frozen,
    tests_run=tests.testsRun,length=length,actual_updater_accepted=updated['version']==1,loaded_modules=loaded,
    frozen_imports=frozen,models_started=0,simulations_started=0,api_requests=0,activation_created=False,
    source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
