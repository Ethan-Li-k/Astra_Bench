"""Freeze isolation and candidate identity boundaries, independent of any model call."""
from pathlib import Path
import tempfile,unittest,json
from rsi.skill_learning import SkillMemory
from rsi.frozen_skill import FrozenSkillMemory,snapshot_memory,stability_count,validate_evaluation_seeds
ROOT=Path(__file__).resolve().parents[1]
SKILL='---\nname: loco-manip-direct\ndescription: Frozen test skill.\n---\nUse current RGB.\n'
class FrozenSkillTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp');self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def setup_memory(self):
  skill=self.root/'learning.md';skill.write_text(SKILL);memory=SkillMemory(self.root/'learning',skill)
  snapshot=self.root/'snapshot';manifest=snapshot_memory(memory,snapshot)
  return memory,snapshot,manifest
 def test_suggestion_is_saved_without_changing_frozen_reads_or_learning(self):
  learning,snapshot,manifest=self.setup_memory();f=FrozenSkillMemory(snapshot,self.root/'audit/episode1',manifest)
  before=f.read();e=self.root/'rollout';e.mkdir();proof=e/'history.jsonl';proof.write_text('{}\n')
  row=f.update(SKILL+'New proposal.\n','observed evidence',[proof],e,'episode1','failure')
  self.assertTrue(row['frozen_proposal_only']);self.assertEqual(f.read(),before)
  self.assertEqual(learning.read()['version'],0);self.assertEqual(learning.skill.read_text(),SKILL)
  self.assertTrue((self.root/'audit/episode1/attempt-0001/experience.jsonl').exists())
 def test_invalid_revision_can_be_corrected_without_publishing_or_losing_rejection(self):
  _,snapshot,manifest=self.setup_memory();f=FrozenSkillMemory(snapshot,self.root/'audit/episode1',manifest)
  e=self.root/'rollout';e.mkdir();p=e/'proof';p.write_text('fixture')
  with self.assertRaises(ValueError):f.update('invalid markdown','lesson',[p],e,'e1','failure')
  f.update(SKILL+'proposal','lesson',[p],e,'e1','failure')
  self.assertTrue((self.root/'audit/episode1/attempt-0001/rejected.json').exists())
  self.assertTrue((self.root/'audit/episode1/attempt-0002/experience.jsonl').exists())
  self.assertEqual(f.read()['version'],0)
 def test_changed_skill_added_memory_or_symlink_are_rejected(self):
  for mode in ['skill','new_experience','symlink']:
   with self.subTest(mode=mode):
    d=self.root/mode;d.mkdir();skill=d/'source.md';skill.write_text(SKILL);memory=SkillMemory(d/'source',skill)
    snap=d/'snapshot';manifest=snapshot_memory(memory,snap);f=FrozenSkillMemory(snap,d/'audit',manifest)
    if mode=='skill':(snap/'SKILL.md').write_text(SKILL+'changed')
    elif mode=='new_experience':(snap/'memory/versions/0001.md').write_text(SKILL)
    else:(snap/'unlisted_link').symlink_to(skill)
    with self.assertRaises(ValueError):f.read()
 def test_live_learning_changes_do_not_enter_snapshot(self):
  learning,snapshot,manifest=self.setup_memory();f=FrozenSkillMemory(snapshot,self.root/'audit',manifest);before=f.read()
  learning.skill.write_text(SKILL+'later learning')
  learning.journal.write_text(json.dumps({'version':1,'episode_id':'later','native_outcome':'success','lesson':'new','evidence_paths':[]})+'\n')
  self.assertEqual(f.read(),before)
 def row(self,n,success=True):return dict(task_id='exact-task',candidate_sha256='a'*64,reset_id=f'reset-{n}',seed=n,physical_attempt=True,native_outcome='success' if success else 'in_progress',full_turn_completed=True,skill_updated=True,audited_task_success=success,termination_class='native_success' if success else 'budget_truncation')
 def test_candidate_streak_fails_on_wrong_version_task_or_repeated_reset(self):
  for change in [{'candidate_sha256':'b'*64},{'task_id':'nearby-variant'},{'reset_id':'reset-0'}]:
   with self.subTest(change=change):
    with self.assertRaises(ValueError):stability_count('exact-task','a'*64,[self.row(0),self.row(1)|change])
 def test_real_non_success_resets_streak_unknown_blocks_gate_and_legal_five_pass(self):
  rows=[self.row(i) for i in range(3)]+[self.row(3,False)]+[self.row(i) for i in range(4,9)]
  self.assertEqual(stability_count('exact-task','a'*64,rows)['consecutive_successes'],5)
  unknown=self.row(9)|{'full_turn_completed':False,'termination_class':'infrastructure_interruption'}
  self.assertFalse(stability_count('exact-task','a'*64,rows+[unknown])['eligible_for_evaluation'])
 def test_evaluation_seeds_are_ten_unique_and_disjoint_from_stability(self):
  self.assertEqual(validate_evaluation_seeds(list(range(20,30)),list(range(5))),list(range(20,30)))
  for seeds in [list(range(9)),[20]*10,list(range(10)),[False]+list(range(21,30))]:
   with self.assertRaises(ValueError):validate_evaluation_seeds(seeds,list(range(5)))
if __name__=='__main__':unittest.main()
