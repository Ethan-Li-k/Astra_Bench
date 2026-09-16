"""Fake dispatch only: no simulator, controller inference or actor process."""
import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from rsi.skill_release import execution_profile
path=os.environ.get('RSI_CANDIDATE_CALLER')
if path:
 spec=importlib.util.spec_from_file_location('candidate_caller',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);LearningHost=module.LearningHost
else:
 from tools.learn_grasp_skill import LearningHost
ROOT=Path(os.environ['RSI_TEST_ROOT'])
class LearningHorizonTests(unittest.TestCase):
 def host(self,d,phase):
  profile=execution_profile(phase,12000 if phase=='evaluation' else None)
  h=LearningHost(d,None,'same-reset',0,max_episode_steps=profile['max_episode_steps'],execution_profile=profile)
  h.backend=SimpleNamespace(data=SimpleNamespace(time=245.02),active=None,status=lambda:{'status':'idle'})
  h.harness=SimpleNamespace(latest_path=d/'obs.json',evaluator=SimpleNamespace(outcome=lambda b:'in_progress'))
  return h
 def action(self,h,n):
  out=h.rollout_root/f'call-{n}';out.mkdir()
  with patch('rsi.tool_host.LocoManipToolHost.dispatch',return_value={'request_id':str(n)}):
   return h.dispatch('scalebfm_act',{'output_dir':str(out),'response':{'trajectory':[{}]}})
 def test_learning_and_stability_cross_old_budget_without_reset_or_duplicate_action(self):
  for phase in ('learning','stability'):
   with self.subTest(phase=phase),tempfile.TemporaryDirectory(dir=ROOT) as td:
    h=self.host(Path(td),phase);backend=h.backend
    for n,time in enumerate((245.02,485.04),1):
     h.backend.data.time=time;p=self.action(h,n)
     self.assertFalse(p['rollout_finished']);self.assertIsNone(p['remaining_steps'])
     self.assertEqual(p['request_id'],str(n));self.assertEqual(h.actions,n);self.assertIs(h.backend,backend)
    self.assertEqual(h.episode_id,'same-reset');self.assertEqual(p['progress_checkpoint'],2)
 def test_evaluation_still_terminates_at_preregistered_budget(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   h=self.host(Path(td),'evaluation');p=self.action(h,1)
   self.assertTrue(p['rollout_finished']);self.assertEqual(p['stop_reason'],'episode_step_budget')
 def test_native_success_and_safety_end_learning(self):
  for outcome in ('success','failure'):
   with self.subTest(outcome=outcome),tempfile.TemporaryDirectory(dir=ROOT) as td:
    h=self.host(Path(td),'learning');h.harness.evaluator.outcome=lambda b:outcome
    p=self.action(h,1);self.assertTrue(p['rollout_finished']);self.assertEqual(p['stop_reason'],'native_'+outcome)
 def test_invalid_profiles_cannot_disable_evaluation_budget(self):
  for args in [('evaluation',None),('evaluation',True),('evaluation',0),('unknown',12000),('learning',12000)]:
   with self.subTest(args=args),self.assertRaises(ValueError):execution_profile(*args)
  with tempfile.TemporaryDirectory(dir=ROOT) as td,self.assertRaises(ValueError):LearningHost(Path(td),None,'bad',0,max_episode_steps=None)
if __name__=='__main__':unittest.main()
