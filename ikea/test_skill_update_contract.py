"""Reproduce inherited updater mismatch without live memory, network or physics."""
from pathlib import Path
import time
import unittest
from validate_skill_update_contract import ROOT,validate


class ContractTests(unittest.TestCase):
    output=ROOT/'engineering-evidence/skill-update-contract'/str(time.time_ns())

    def test_initial_apple_name_rejected_by_real_updater(self):
        original=(ROOT/'campaign/apple-0001/SKILL.md').read_text()
        result=validate(original,'',self.output/'original')
        self.assertFalse(result['accepted'])
        self.assertIn('loco-manip-direct',result['error'])
        self.assertFalse((self.output/'original/synthetic-memory/experience.jsonl').exists())

    def test_name_normalization_passes_real_updater(self):
        candidate=(ROOT/'campaign/apple-0001/SKILL.md').read_text().replace('name: ikea-apple-grasp\n','name: loco-manip-direct\n',1)
        result=validate(candidate,'',self.output/'normalized')
        self.assertTrue(result['accepted'])

    def test_combined_prefix_cannot_exceed_limit(self):
        skill='---\nname: loco-manip-direct\ndescription: Synthetic preflight.\n---\n'+'s'*3900
        result=validate(skill,'r'*2500,self.output/'overflow')
        self.assertFalse(result['accepted'])
        self.assertIn('Combined skill',result['error'])


if __name__=='__main__':unittest.main()
