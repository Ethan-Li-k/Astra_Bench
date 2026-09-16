from support import *
import unittest
class Reproduction(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  root=B/'evidence/reproduction-episode';root.mkdir()
  cls.ep,cls.result,cls.status,_,_,_=run_case(root,recovered(),tree='snapshots',adapter_path=B/'evidence/previous-recovery-on-current.py')
  (B/'evidence/before.json').write_text(json.dumps({'turn_files':[p.name for p in cls.ep.glob('turn_*.json')],'result':cls.result,'auditor':cls.status,'fixture_only':True},indent=2))
 def test_every_terminal_has_its_numbered_receipt(self):self.assertEqual(sorted(p.name for p in self.ep.glob('turn_*.json')),['turn_001.json','turn_002.json'])
 def test_missing_failed_turn_cannot_be_complete_success(self):self.assertFalse(self.status['audited_task_success'])
unittest.main(verbosity=2)
