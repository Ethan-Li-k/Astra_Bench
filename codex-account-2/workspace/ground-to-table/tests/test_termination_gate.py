"""Real archived stall content plus host boundary cases; no LLM calls."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.learn_grasp_skill import LearningHost


class TerminationGateTests(unittest.TestCase):
    def host(self,directory,time=59.48,outcome='in_progress',reason=None):
        host=LearningHost(Path(directory),None,'termination-test',0,max_episode_steps=9000)
        host.backend=SimpleNamespace(active=None,reason=reason,data=SimpleNamespace(time=time),
            status=lambda:{'status':'aborted' if reason else 'timed_out'})
        host.harness=SimpleNamespace(latest_path=host.rollout_root/'observation.json',
            evaluator=SimpleNamespace(outcome=lambda b:outcome))
        host.actions=12
        return host

    def test_archived_0011_stall_must_continue_with_budget_remaining(self):
        old=json.loads((Path(__file__).resolve().parents[1]/'campaign/episode-0011/rollout/policy_stop.json').read_text())
        self.assertTrue(old['rollout_finished']) # Preserve real counterexample provenance.
        with tempfile.TemporaryDirectory() as directory:
            host=self.host(directory);evidence=host.rollout_root/'receipt.json';evidence.write_text('{}')
            args={k:old[k] for k in ('reason','next_hypothesis')};args['evidence_paths']=[str(evidence)]
            with patch('rsi.tool_host.LocoManipToolHost.dispatch') as physics:
                result=host.dispatch('finish_attempt',args);physics.assert_not_called()
            self.assertFalse(result['rollout_finished'])
            self.assertFalse(host.finished);self.assertIsNone(host.stop_reason)
            self.assertEqual(result['next_call']['tool'],'scalebfm_act')
            self.assertTrue((host.rollout_root/'policy_stall.jsonl').is_file())
            self.assertFalse((host.rollout_root/'policy_stop.json').exists())
            self.assertEqual(host.backend.data.time,59.48)

    def dispatch_action(self,host):
        out=host.rollout_root/'action';out.mkdir()
        with patch('rsi.tool_host.LocoManipToolHost.dispatch',return_value={}):
            return host.dispatch('scalebfm_act',{'output_dir':str(out),'response':{'trajectory':[{}]}})

    def test_runtime_stop_ends_even_when_task_native_stays_in_progress(self):
        for reason in ('diagnostic_stability_stop','nonfinite_policy_output','external_sim_time_change'):
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as directory:
                host=self.host(directory,reason=reason);result=self.dispatch_action(host)
                self.assertTrue(result['rollout_finished']);self.assertTrue(host.finished)
                self.assertEqual(result['next_call']['tool'],'skill_update')
                self.assertEqual(result['backend_stop_reason'],reason)
                self.assertEqual(result['native_outcome'],'in_progress')

    def test_native_success_failure_and_budget_still_terminal(self):
        for native,time,expected in [('success',10.,'native_success'),('failure',10.,'native_failure'),('in_progress',185.,'episode_step_budget')]:
            with self.subTest(native=native,time=time),tempfile.TemporaryDirectory() as directory:
                host=self.host(directory,time=time,outcome=native);result=self.dispatch_action(host)
                self.assertTrue(result['rollout_finished']);self.assertEqual(result['stop_reason'],expected)
                self.assertEqual(result['next_call']['tool'],'skill_update')

    def test_normal_nonterminal_action_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.dispatch_action(self.host(directory))
            self.assertFalse(result['rollout_finished']);self.assertEqual(result['next_call']['tool'],'scalebfm_act')


if __name__=='__main__':unittest.main()
