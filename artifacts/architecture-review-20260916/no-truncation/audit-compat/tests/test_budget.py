from support import *
import tempfile,unittest
class BudgetTests(unittest.TestCase):
 def test_recovery_space_reserved_before_host_and_in_future_updates(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory(dir=B/'tests') as tmp:
   root=Path(tmp)
   ep,r,s,t,h,a=run_case(root,recovered())
   budget=json.loads((ep/'policy_instruction_budget.json').read_text())
   self.assertEqual(budget['network_continuation'],'Observe; next_call: ')
   self.assertEqual(h.memory.runtime_instructions,self.runtime()+budget['network_continuation'])
   self.assertEqual(budget['combined_size']['characters'],len((ep/'SKILL.md').read_text())+len(self.runtime())+len(budget['network_continuation']))
 def runtime(self):
  t=ast.parse((B/'candidate/tools/learn_grasp_skill.py').read_text())
  n=next(n for n in ast.walk(t) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='immutable' for x in n.targets))
  return ast.literal_eval(n.value)
 def test_entry_rejected_if_it_only_fits_without_continuation(self):
  adapter=load('budget_adapter',B/'candidate/rsi/codex_app_server.py');memory=load('budget_memory',B/'snapshots/rsi/skill_learning.py')
  runtime=self.runtime();body='x'*(5357-len(''.join(runtime.split())))
  memory.validate_policy_instructions(body,runtime)
  with self.assertRaises(ValueError):memory.validate_policy_instructions(body,runtime+adapter.NETWORK_CONTINUATION)
 def test_update_rejects_consuming_reserved_recovery_space(self):
  m=load('update_memory',B/'snapshots/rsi/skill_learning.py');a=load('update_adapter',B/'candidate/rsi/codex_app_server.py')
  with tempfile.TemporaryDirectory(dir=B/'tests') as d:
   root=Path(d);skill=root/'SKILL.md';seed='---\nname: loco-manip-direct\ndescription: Fixture.\n---\nObserve.\n';skill.write_text(seed)
   memory=m.SkillMemory(root/'memory',skill);memory.runtime_instructions=self.runtime()+a.NETWORK_CONTINUATION
   front='---\nname: loco-manip-direct\ndescription: Fixture.\n---\n'
   revised=front+'x'*(5357-len(''.join((front+self.runtime()).split())))
   m.validate_policy_instructions(revised,self.runtime())
   public=root/'rollout';public.mkdir();evidence=public/'public.json';evidence.write_text('{}')
   with self.assertRaises(ValueError):memory.update(revised,'Public lesson',[evidence],public,'episode-0001','success')
   self.assertEqual(skill.read_text(),seed);self.assertFalse(memory.journal.exists())
 def test_all_current_task_entries_fit_without_editing_skills(self):
  m=load('size_memory',B/'snapshots/rsi/skill_learning.py');a=load('size_adapter',B/'candidate/rsi/codex_app_server.py')
  paths=[RSI/'skills/loco-manip-simple/SKILL.md']+[RSI/f'artifacts/R019/{name}-campaign/SKILL.md' for name in ('apple','faucet','boxplace','bendpick','oven')]
  rows=[]
  for p in paths:
   text=p.read_text();size=m.validate_policy_instructions(text,self.runtime()+a.NETWORK_CONTINUATION)
   rows.append({'path':str(p),'sha256':hashlib.sha256(text.encode()).hexdigest(),'size':size})
  (B/'evidence/length-final.json').write_text(json.dumps({'recovery_instructions':a.NETWORK_CONTINUATION,'runtime_sha256':hashlib.sha256(self.runtime().encode()).hexdigest(),'entries':rows},indent=2))
if __name__=='__main__':unittest.main(verbosity=2)
