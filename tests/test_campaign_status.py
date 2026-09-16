import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',ROOT/'tools/audit_simple_campaigns.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class CampaignStatusTests(unittest.TestCase):
    def test_focus_uses_reset_time_and_never_relabels_old_success_as_new(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp') as directory:
            root=Path(directory);(root/'six-task-focus').mkdir()
            (root/'six-task-focus/supervisor-ack.json').write_text(json.dumps({
                'source':'user-scope','effective_utc':'2026-09-16T12:28:40+00:00',
                'scope':['XMovePick','Grasp'],'campaign_families':{'xmovepick-campaign':'XMovePick'},
                'inflight':[{'campaign':'xmovepick-campaign','episode':'episode-0002'}]}))
            def ep(n,stamp,success=True):
                return {'episode_id':f'episode-{n:04d}','reset_recorded_utc':stamp,
                        'physical_attempt':True,'audited_task_success':success}
            campaigns=[{'campaign':'xmovepick-campaign','episodes':[
                ep(1,'2026-09-16T11:00:00+00:00'),ep(2,'2026-09-16T12:20:00+00:00'),
                ep(3,'2026-09-16T12:28:40+00:00'),ep(4,'2026-09-16T12:29:00+00:00',False),
                ep(5,None),ep(6,'bad-date'),ep(7,'2026-09-16T13:00:00')]},
                {'campaign':'xmovepicksim-campaign','episodes':[ep(1,'2026-09-16T12:30:00+00:00')]}]
            report=audit.focused_cohorts(root,campaigns)
            cohorts=report['families']['XMovePick'][0]['cohorts']
            self.assertEqual(cohorts['historical']['episodes'],['episode-0001'])
            self.assertEqual(cohorts['transition_inflight']['episodes'],['episode-0002'])
            self.assertEqual(cohorts['post_focus']['physical_attempts'],2)
            self.assertEqual(cohorts['post_focus']['audited_successes'],1)
            self.assertEqual(cohorts['unknown_reset_time']['physical_attempts'],3)
            self.assertEqual(report['families']['Grasp'],[])
            self.assertEqual(len(report['families']['XMovePick']),1)

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
