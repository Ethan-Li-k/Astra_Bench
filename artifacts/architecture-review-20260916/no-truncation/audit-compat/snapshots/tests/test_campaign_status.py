import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',ROOT/'tools/audit_simple_campaigns.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class CampaignStatusTests(unittest.TestCase):
    def test_missing_result_after_reboot_is_interrupted_without_fabrication(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp') as directory:
            ep=Path(directory)/'door-campaign/episode-0015';(ep/'video').mkdir(parents=True)
            (ep/'video/scene_setup.json').write_text(json.dumps({'reset_provenance':{
                'launch':{'boot_id':'old-boot'}}}))
            state=audit.episode_status(ep)
            self.assertEqual(state['state'],'interrupted')
            self.assertEqual(state['termination_class'],'infrastructure_interruption')
            self.assertFalse(state['full_turn_completed'])
            self.assertFalse(state['audited_task_success'])
            self.assertFalse((ep/'result.json').exists())

    def test_same_boot_without_result_does_not_infer_failure_from_delay(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp') as directory:
            ep=Path(directory)/'door-campaign/episode-0016';(ep/'video').mkdir(parents=True)
            (ep/'video/scene_setup.json').write_text(json.dumps({'reset_provenance':{
                'launch':{'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}}}))
            self.assertEqual(audit.episode_status(ep)['state'],'running')


if __name__=='__main__':unittest.main()
