"""Public receipt projection only; no equality diagnostics, actor, model or delivery calls."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from dashboard import Dashboard

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('candidate_fixtures',OUT.parent/'explicit-blockers/test_explicit_blockers.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous);previous.OUT=OUT
PUB='artifacts/R019/robot-stability-integration-20260916/'
CANDIDATE=previous.STABILITY


class PublicationTests(unittest.TestCase):
    setUp=previous.ExplicitBlockerTests.setUp
    write=previous.ExplicitBlockerTests.write
    nt_published=previous.ExplicitBlockerTests.nt_published

    def receipts(self, verify=True, candidate=True):
        if candidate:
            for name in ('result.json','progress.json','manager-status.json'):
                self.write(CANDIDATE+name,json.loads((OUT/'candidate-source-snapshot'/name).read_text()),at=1800000100)
        pub=json.loads((OUT/'publisher-source-snapshot/status.json').read_text())
        first=json.loads((OUT/'publisher-source-snapshot/first-action-physical-verification.json').read_text())
        self.write(PUB+'status.json',pub)
        if verify:self.write(PUB+'first-action-physical-verification.json',first)
        return pub,first

    def test_actual_publisher_overrides_old_candidate_without_changing_nt(self):
        self.nt_published();old=self.d.framework();pub,first=self.receipts()
        d=self.d.framework()
        (OUT/'actual-observed.json').write_text(json.dumps({k:d[k] for k in
            ('current_work','summary','problem','next','milestones','nt_publication')},ensure_ascii=False,indent=2)+'\n')
        self.assertEqual(d['current_work']['state'],'published-fields-verified')
        self.assertIs(d['current_work']['deployed'],True)
        self.assertIs(d['current_work']['publisher_acknowledged'],True)
        self.assertIs(d['current_work']['first_action_fields_verified'],True)
        self.assertIs(d['current_work']['physical_benefit_verified'],False)
        self.assertEqual(d['current_work']['samples'],251)
        self.assertEqual(d['current_work']['max_height_difference_m'],first['max_height_difference_m'])
        self.assertEqual(d['current_work']['max_tilt_difference_deg'],first['max_tilt_difference_deg'])
        self.assertIn('本体状态观测已发布；首动作字段验证通过',d['summary'])
        self.assertIn('完整回合和任务收益尚未验证',d['problem'])
        self.assertIn('完整回合审计',d['next'])
        self.assertIn('不重复',d['next']);self.assertIn('旧版冻结',d['next'])
        self.assertNotIn('未部署',d['problem'])
        self.assertNotIn('负责人尚未确认',json.dumps(d,ensure_ascii=False))
        self.assertEqual(d['nt_publication'],old['nt_publication'])
        self.assertEqual(d['state_label'],old['state_label'])
        for milestone in old['milestones']:self.assertIn(milestone,d['milestones'])
        self.assertIsNone(d['last_action_at'])

    def test_missing_verification_keeps_published_but_fields_unknown(self):
        self.receipts(verify=False);d=self.d.framework()
        self.assertIs(d['current_work']['deployed'],True)
        self.assertIsNone(d['current_work']['first_action_fields_verified'])
        self.assertIsNone(d['current_work']['samples'])
        self.assertIn('首动作字段验证尚未确认',d['summary'])
        self.assertNotIn('首动作字段验证通过',d['summary'])

    def test_episode_identity_and_explicit_verification_flags_required(self):
        pub,first=self.receipts()
        for label,patches in [('other_episode',{'episode':'artifacts/R019/xmovepick-campaign/episode-0004'}),
            ('outside_path',{'episode':'/etc/episode-0003'}),('unknown_action',{'actual_formal_physical_action':None}),
            ('unknown_samples',{'samples':None}),('mismatched_sources',{'published_sources_match_formal_runtime':False}),
            ('mismatched_time',{'same_action_time_and_episode_identity':False}),('unverified_summary',{'summary_recomputation_exact':False})]:
            with self.subTest(label=label):
                self.write(PUB+'first-action-physical-verification.json',dict(first,**patches));d=self.d.framework()
                self.assertIs(d['current_work']['deployed'],True)
                self.assertIsNone(d['current_work']['first_action_fields_verified'])
                self.assertIn('尚未确认',d['summary'])
        self.write(PUB+'first-action-physical-verification.json',first)
        for boundary in ('../xmovepick-campaign/episode-0003','/artifacts/R019/xmovepick-campaign/episode-0003','xmovepick-campaign/../episode-0003'):
            self.write(PUB+'status.json',dict(pub,first_physical_boundary=boundary))
            self.assertIsNone(self.d.framework()['current_work']['first_action_fields_verified'])

    def test_invalid_publisher_falls_back_to_candidate_and_valid_publisher_needs_no_candidate(self):
        pub,first=self.receipts()
        for changes in ({'ack':'OTHER ACK'},{'status':'candidate_only'},{'source_hashes_match':False},
                        {'source_sha256':{'rsi/live.py':'bad'}},{'source_sha256':None}):
            with self.subTest(changes=changes):
                self.write(PUB+'status.json',dict(pub,**changes));d=self.d.framework()
                self.assertEqual(d['current_work']['state'],'candidate-delivered')
                self.assertIs(d['current_work']['deployed'],False)
                self.assertIn('发布者回执尚未确认',json.dumps(d,ensure_ascii=False))
        self.setUp();self.receipts(candidate=False)
        self.assertEqual(self.d.framework()['current_work']['state'],'published-fields-verified')
        self.write(PUB+'status.json',dict(pub,ack='UNKNOWN ACK'))
        d=self.d.framework();self.assertIsNone(d['current_work']['source_at'])
        self.assertNotIn('1970-',d['source_time_note'])

    def test_physical_benefit_does_not_follow_action_or_numeric_agreement(self):
        pub,first=self.receipts();self.assertIs(self.d.framework()['current_work']['physical_benefit_verified'],False)
        pub.pop('physical_benefit_verified');pub.pop('full_episode_and_task_benefit');first.pop('physical_task_benefit_verified')
        self.write(PUB+'status.json',pub);self.write(PUB+'first-action-physical-verification.json',first);d=self.d.framework()
        self.assertIs(d['current_work']['first_action_fields_verified'],True)
        self.assertIsNone(d['current_work']['physical_benefit_verified'])
        self.assertIn('收益验证尚未上报',d['problem'])
        pub['physical_benefit_verified']=True;first['physical_task_benefit_verified']=False
        self.write(PUB+'status.json',pub);self.write(PUB+'first-action-physical-verification.json',first);d=self.d.framework()
        self.assertIsNone(d['current_work']['physical_benefit_verified'])
        self.assertIn('不一致',d['problem']);self.assertNotEqual(d['state'],'complete')

    def test_only_fixed_files_read_and_only_allowlisted_engineering_fields_projected(self):
        pub,first=self.receipts()
        pub.update(first_action_evidence='/etc/PRIVATE_PATH_SENTINEL',private_auth='AUTH_SENTINEL')
        first.update(root_mapping_receipt='HOST_PATH_SENTINEL',note='HOST_NOTE_SENTINEL',
                     object_position='OBJECT_TRUTH_SENTINEL',raw_error={'secret':'ERROR_SENTINEL'})
        self.write(PUB+'status.json',pub);self.write(PUB+'first-action-physical-verification.json',first)
        with patch.object(self.d,'read',wraps=self.d.read) as read,patch('subprocess.run') as call:
            body=json.dumps(self.d.framework(),ensure_ascii=False);call.assert_not_called()
        for sentinel in ('PRIVATE_PATH_SENTINEL','AUTH_SENTINEL','HOST_PATH_SENTINEL','HOST_NOTE_SENTINEL','OBJECT_TRUTH_SENTINEL','ERROR_SENTINEL'):
            self.assertNotIn(sentinel,body)
            self.assertFalse(any(sentinel in str(c.args) for c in read.call_args_list))
        self.assertIn('首动作字段验证通过',body)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PublicationTests)
    for name in ('test_offline_candidate_and_published_nt_remain_independent',
                 'test_ready_candidate_is_delivered_not_deployed_even_tests_pass',
                 'test_progress_only_candidate_status_and_missing_fields_are_unknown',
                 'test_ready_without_candidate_contract_not_promoted','test_new_source_symlinks_rejected'):
        suite.addTest(previous.ExplicitBlockerTests(name))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
