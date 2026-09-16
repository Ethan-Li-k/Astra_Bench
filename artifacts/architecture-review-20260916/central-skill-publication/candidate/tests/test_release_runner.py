"""Exercise actual staged SIMPLE main using fake run_episode, never a backend factory."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,os,sys,tempfile,unittest
ROOT=Path('/home/galbot/lizekai/RSI');HERE=Path(__file__).resolve().parents[2]
from rsi.skill_release import runtime_instructions,verify_release
spec=importlib.util.spec_from_file_location('candidate_learning_host',HERE/'candidate/tools/learn_grasp_skill.py');caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)
spec=importlib.util.spec_from_file_location('candidate_simple_runner',HERE/'candidate/tools/learn_simple_task.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
class RunnerTests(unittest.TestCase):
 def test_actual_main_loads_verified_release_and_isolates_terminal_proposal(self):
  release=Path(os.environ['RSI_TEST_RELEASE']);h=os.environ['RSI_TEST_RELEASE_SHA'];runtime=runtime_instructions(HERE/'candidate/tools/learn_grasp_skill.py',ROOT/'rsi/codex_app_server.py')
  env='simple/G1WholebodyXMovePickTeleop-v0';manifest=verify_release(release,h,env,runtime)
  actual_digest=runner.digest
  def staged_digest(p):
   p=Path(p)
   if p in [ROOT/'tools/learn_grasp_skill.py',ROOT/'tools/learn_simple_task.py']:return actual_digest(HERE/'candidate/tools'/p.name)
   return actual_digest(p)
  with tempfile.TemporaryDirectory(dir=HERE/'checks/tmp') as td:
   root=Path(td);out=root/'campaign';calls=[]
   def fake_episode(output,memory,eid,successes,**kw):
    calls.append(eid);host=kw['host_factory'](output,memory,eid,successes)
    self.assertIsNone(host.max_episode_steps);self.assertEqual(host.execution_profile['id'],'learning-horizon-v1')
    self.assertTrue(all(str(release/'public') in p for p in kw['transfer_sources']))
    before=memory.read();proof=host.rollout_root/'public.json';proof.write_text('{}')
    host.finished=True;host.harness=SimpleNamespace(evaluator=SimpleNamespace(outcome=lambda b:'failure'));host.backend=SimpleNamespace()
    host.dispatch('skill_update',{'markdown':memory.skill.read_text(),'lesson':'Fixture terminal failure, no physical benefit.', 'evidence_paths':[str(proof)],'transfer_scope':'task_specific','change_summary':'Evidence retained only'})
    self.assertEqual(memory.read(),before)
    self.assertTrue((out/'skill-proposals'/eid/'accepted.json').exists())
    return {'success':False,'native_outcome':'failure','error':None}
   args=['runner','--env-id',env,'--task-spec',str(ROOT/'ref/tasks/simple-xmove-pick.json'),'--output',str(out),'--continuous-chunks','--human-feedback',str(ROOT/'human-feedback/H001-user-feedback-004.json'),'--skill-release',str(release),'--release-sha256',h]
   with patch.object(sys,'argv',args),patch.object(runner,'runtime_instructions',return_value=runtime),patch.object(runner,'digest',side_effect=staged_digest),patch.object(runner,'LearningHost',caller.LearningHost),patch.object(runner,'run_episode',side_effect=fake_episode):runner.main()
   self.assertEqual(calls,['episode-0001']);self.assertTrue((out/'release-load-receipts/episode-0001.json').exists())
 def test_pending_stability_does_not_start_any_episode(self):
  args=['runner','--env-id','exact','--task-spec','absent','--output','absent','--skill-release','absent','--release-sha256','x','--phase','stability']
  with patch.object(sys,'argv',args),patch.object(runner,'run_episode') as physical,self.assertRaisesRegex(ValueError,'registration'):runner.main()
  physical.assert_not_called()
if __name__=='__main__':unittest.main()
