"""Publication/load contracts only; no actor or physical backend."""
import fcntl,hashlib,json,os,tempfile,unittest
from pathlib import Path
from rsi.skill_release import (AUTHOR,ReleasedSkillMemory,publish_release,verify_release,
    verify_load_configuration,verify_frozen_release_inputs,select_sources,validate_public_payload)
from rsi.frozen_skill import file_hashes
ROOT=Path(os.environ.get('RSI_TEST_ROOT',Path(__file__).resolve().parents[1]/'artifacts/architecture-review-20260916/central-skill-publication/checks/tmp'))
SKILL='---\nname: loco-manip-direct\ndescription: Release test.\n---\nUse current public RGB.\n'
class ReleaseTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT);self.root=Path(self.temp.name);self.draft=self.root/'draft';snap=self.draft/'public/tasks/task';(snap/'memory/versions').mkdir(parents=True)
  (snap/'SKILL.md').write_text(SKILL);(snap/'memory/versions/0000.md').write_text(SKILL);(snap/'retrieval-labels.json').write_text('{}')
  self.runtime=' runtime';self.releases=self.root/'releases';self.manifest={'release_id':'v1','author':AUTHOR,'tasks':{'exact':{'snapshot':'tasks/task','ready_for_load':True,'bindings':{'task':'exact','feedback':False}}},'public_hashes':file_hashes(self.draft/'public'),'runtime_sha256':hashlib.sha256(self.runtime.encode()).hexdigest()};self.save()
 def save(self): (self.draft/'release.json').write_text(json.dumps(self.manifest))
 def tearDown(self):self.temp.cleanup()
 def publish(self):
  self.pointer=publish_release(self.draft,self.releases,'v1',author=AUTHOR,expected_previous=None,runtime=self.runtime);return self.releases/'v1'
 def test_published_hash_loads_and_proposal_cannot_replace_next_loaded_skill(self):
  release=self.publish();h=self.pointer['manifest_sha256'];m=ReleasedSkillMemory(release,h,'exact',self.root/'audit/e1',self.runtime)
  before=m.read();ev=self.root/'rollout';ev.mkdir();proof=ev/'public.json';proof.write_text('{}')
  row=m.update(SKILL+'Candidate only.','Observed fixture',[proof],ev,'e1','failure')
  self.assertTrue(row['frozen_proposal_only']);self.assertEqual(m.read(),before)
  next_m=ReleasedSkillMemory(release,h,'exact',self.root/'audit/e2',self.runtime);self.assertEqual(next_m.read(),before)
  self.assertIn('Candidate only.',(self.root/'audit/e1/attempt-0001/SKILL.md').read_text())
 def test_unpublished_wrong_hash_wrong_entry_runtime_and_added_input_rejected(self):
  with self.assertRaises(ValueError):verify_release(self.draft,hashlib.sha256((self.draft/'release.json').read_bytes()).hexdigest(),'exact',self.runtime)
  release=self.publish();h=self.pointer['manifest_sha256']
  for digest,entry,runtime in [('f'*64,'exact',self.runtime),(h,'nearby-variant',self.runtime),(h,'exact','changed')]:
   with self.subTest(entry=entry,runtime=runtime),self.assertRaises(ValueError):verify_release(release,digest,entry,runtime)
  (release/'public/tasks/task/memory/versions/0001.md').write_text('new evaluation lesson')
  with self.assertRaises(ValueError):verify_release(release,h,'exact',self.runtime)
 def test_author_lock_pointer_and_duplicate_publication(self):
  with self.assertRaises(ValueError):publish_release(self.draft,self.releases,'v1',author='actor',expected_previous=None,runtime=self.runtime)
  self.releases.mkdir()
  with (self.releases/'.publish.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):self.publish()
  self.publish()
  with self.assertRaises(ValueError):self.publish()
  self.assertEqual(json.loads((self.releases/'CURRENT.json').read_text()),self.pointer)
 def test_changed_configuration_feedback_and_pending_mp_are_not_admitted(self):
  self.publish();verify_load_configuration(self.manifest,'exact',{'task':'exact','feedback':False})
  for bindings in [{'task':'approx','feedback':False},{'task':'exact','feedback':True}]:
   with self.assertRaises(ValueError):verify_load_configuration(self.manifest,'exact',bindings)
  self.manifest['tasks']['exact']['ready_for_load']=False
  with self.assertRaises(ValueError):verify_load_configuration(self.manifest,'exact',{'task':'exact','feedback':False})
 def test_symlink_and_path_escape_rejected(self):
  (self.draft/'public/alias').symlink_to(self.draft/'release.json')
  with self.assertRaises(ValueError):self.publish()
  (self.draft/'public/alias').unlink();self.manifest['tasks']['exact']['snapshot']='../../escape';self.save()
  with self.assertRaises(ValueError):self.publish()
 def test_sealing_does_not_authorize_a_new_unpublished_experience(self):
  candidate=self.root/'sealed-public';candidate.mkdir();(candidate/'SKILL.md').write_text(SKILL)
  verify_frozen_release_inputs(self.manifest,candidate,env_id='exact',permitted_hashes=self.manifest['public_hashes'].values())
  (candidate/'new.md').write_text('New evaluation lesson not in release')
  with self.assertRaises(ValueError):verify_frozen_release_inputs(self.manifest,candidate,env_id='exact',permitted_hashes=self.manifest['public_hashes'].values())
 def test_other_task_assisted_source_cannot_leak_into_unassisted_freeze(self):
  candidate=self.root/'public-copy';candidate.mkdir();(candidate/'SKILL.md').write_text(SKILL)
  approved=set(self.manifest['public_hashes'].values())
  assisted=b'Human-assisted other-task source';other=hashlib.sha256(assisted).hexdigest()
  self.manifest['public_hashes']['other-task.json']=other
  (candidate/'other-task.json').write_bytes(assisted)
  with self.assertRaises(ValueError):verify_frozen_release_inputs(self.manifest,candidate,env_id='exact',permitted_hashes=approved)
 def test_rollback_pointer_preserves_previous_release(self):
  first=self.publish();before=(first/'release.json').read_bytes();previous=dict(self.pointer)
  self.manifest['release_id']='v2';self.save()
  second=publish_release(self.draft,self.releases,'v2',author=AUTHOR,expected_previous=previous['manifest_sha256'],runtime=self.runtime)
  self.assertEqual(json.loads((self.releases/'v2/release.json').read_text())['rollback'],previous)
  self.assertEqual((first/'release.json').read_bytes(),before);self.assertEqual(json.loads((self.releases/'CURRENT.json').read_text()),second)
 def test_recursive_privileged_payload_is_rejected_not_rephrased(self):
  for key in ['object_pose','contacts','reward','evaluator','host_audit','oracle']:
   with self.subTest(key=key),self.assertRaises(ValueError):validate_public_payload({'sources':[{'nested':{key:'POISON_SENTINEL'}}]})
 def test_conditional_small_retrieval_orders_success_then_counterexample(self):
  def row(i,env,status,feedback=False,control='c'):
   return {'id':i,'env_id':env,'status':status,'human_feedback_used':feedback,'control_contract':control,'phases':['retention']}
  index={'sources':[row('z','exact','audited_source'),row('a','other','audited_source'),row('b','exact','counterexample'),row('c','exact','unknown'),row('d','exact','audited_source',True),row('e','exact','audited_source',control='different')]}
  out=select_sources(index,'exact',['retention'],'c',False)
  self.assertEqual([x['id'] for x in out],['z','a','b'])
 def test_current_task_counterexample_precedes_other_task_counterexample(self):
  def row(i,env,status):return dict(id=i,env_id=env,status=status,control_contract='c',phases=['retention'])
  index={'sources':[row('same-success','exact','audited_source'),row('other-success','other','audited_source'),
                    row('a-other-failure','other','counterexample'),row('z-current-failure','exact','counterexample')]}
  self.assertEqual([r['id'] for r in select_sources(index,'exact',['retention'],'c',False)],
                   ['same-success','other-success','z-current-failure'])
if __name__=='__main__':unittest.main()
