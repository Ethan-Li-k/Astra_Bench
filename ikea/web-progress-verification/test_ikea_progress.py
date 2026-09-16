import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path.insert(0, str(ROOT / 'human-feedback/tools'))
sys.path.insert(0, str(EVIDENCE / 'candidate'))
from ikea_progress import IKEAProgress, last_known_runtime


class IKEAProgressTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=EVIDENCE))
        self.boot = time.time() - 600
        self.api = IKEAProgress(self.root, boot=('fixture-current-boot', self.boot))

    def write(self, p, d):
        path = self.root / p;path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(d))

    def test_legacy_state_old_heartbeat_and_reboot(self):
        self.write('state.json', dict(updated_at=self.boot-100, state='continue', phase='door_physics_validation',
            backend='MuJoCo FBX-derived no-latch variant v1', physical_attempts=0, audited_successes=0))
        self.write('heartbeat.json', dict(at=time.time(), actor_progress={'actions':999}))
        self.write('recovery-20260916/incident.json', dict(classification='host_restart_infrastructure_interruption'))
        d=self.api.snapshot()
        self.assertTrue(d['interrupted_by_restart']);self.assertIn('系统中断',d['state_label'])
        self.assertEqual(d['last_progress_at_unix'],self.boot-100)
        self.assertGreater(d['heartbeat_at_unix'],d['last_progress_at_unix'])
        self.assertEqual(d['physical_attempts'],0);self.assertIsNone(d['actions'])
        self.assertEqual(d['backend'],'MuJoCo');self.assertFalse(d['runtime_evidence_confirmed'])
        self.assertTrue(all(x['verification']=='未验证' for x in d['tasks']))

    def test_normal_new_schema_prefers_explicit_progress(self):
        self.write('state.json',dict(physical_attempts=999))
        self.write('web-progress.json',dict(schema_version=1,backend='MuJoCo',variant='fbx-derived-no-latch-v1',
            state='inference_waiting',phase='bedroom_door',physical_attempts=2,audited_successes=0,
            actions=7,simulated_seconds=14.2,updated_at=time.time(),last_progress_at=time.time()-40,
            live_evidence=dict(boot_id='fixture-current-boot',observed_at=time.time(),state='inference_waiting')))
        d=self.api.snapshot();self.assertEqual(d['source_schema'],'web-progress-v1')
        self.assertEqual(d['physical_attempts'],2);self.assertEqual(d['actions'],7)
        self.assertTrue(d['runtime_evidence_confirmed']);self.assertEqual(d['simulated_seconds'],14.2)
        self.assertGreater(d['source_updated_at_unix'],d['last_progress_at_unix'])

    def test_engineer_actual_schema_one_aliases(self):
        self.write('web-progress.json',dict(schema=1,backend='MuJoCo FBX-derived no-latch variant v1',
            execution_kind='engineering',phase='source_physics_confirmed_scene_alignment',attempts=0,
            actions=0,sim_s=0,audited_successes=0,last_actual_progress_at=time.time(),
            diagnostic_runs=1,diagnostic_sim_s=6,human_help_needed=False,engineering_state='NEVER-PUBLISH-RAW'))
        d=self.api.snapshot();self.assertEqual(d['state'],'engineering')
        self.assertEqual(d['physical_attempts'],0);self.assertEqual(d['simulated_seconds'],0)
        self.assertEqual(d['diagnostic_runs'],1);self.assertEqual(d['diagnostic_simulated_seconds'],6)
        self.assertFalse(d['needs_human']);self.assertNotIn('NEVER-PUBLISH-RAW',json.dumps(d))

    def test_missing_fields_are_unknown_not_zero(self):
        self.write('web-progress.json',dict(schema_version=1))
        d=self.api.snapshot()
        for key in ['physical_attempts','audited_successes','actions','simulated_seconds','last_progress_at_unix','needs_human']:
            self.assertIsNone(d[key],key)
        self.assertEqual(d['videos'],[]);self.assertEqual(d['media_note'],'首个连续视频尚未完成')

    def test_unknown_schema_falls_back_without_leaking_raw_data(self):
        self.write('web-progress.json',dict(schema_version=800,backend='PRIVATE-PAYLOAD',host_truth='HIDDEN'))
        self.write('state.json',dict(state='continue',current_problem='PRIVATE-PAYLOAD',actions=None))
        d=self.api.snapshot();self.assertEqual(d['source_schema'],'legacy-state')
        self.assertNotIn('PRIVATE-PAYLOAD',json.dumps(d));self.assertNotIn('HIDDEN',json.dumps(d))

    def test_terminal_budget_and_infrastructure_separate(self):
        for terminal,expected in [('budget_limited_incomplete','不是物理失败'),('infrastructure_error','基础设施'),('safety_stop','安全停止')]:
            self.write('web-progress.json',dict(schema_version=1,state='ended',terminal_kind=terminal))
            self.assertIn(expected,self.api.snapshot()['terminal_label'])

    def test_heartbeat_does_not_prove_live_inference(self):
        self.write('web-progress.json',dict(schema_version=1,state='inference_waiting',updated_at=self.boot-1,
            live_evidence=dict(boot_id='old-boot',state='inference_waiting',observed_at=time.time())))
        self.write('heartbeat.json',dict(at=time.time()))
        d=self.api.snapshot();self.assertFalse(d['runtime_evidence_confirmed'])
        self.assertTrue(d['interrupted_by_restart'])

    def test_api_old_state_is_last_known_without_reclassifying_result(self):
        source=dict(updated_at_unix=self.boot-10,state_label='正在推理',terminal_kind=None)
        d=last_known_runtime(source,self.boot)
        self.assertIn('主机重启前最后已知',d['state_label']);self.assertFalse(d['runtime_confirmed'])
        self.assertIsNone(d['terminal_kind']);self.assertEqual(source['state_label'],'正在推理')

    def test_recovery_ack_is_not_progress(self):
        self.write('recovery-ack.json',dict(at=time.time(),actor_running=True,actions=999,private='secret'))
        d=self.api.snapshot();self.assertIsNotNone(d['recovery_ack_at_unix'])
        self.assertIsNone(d['last_progress_at_unix']);self.assertIsNone(d['actions'])
        self.assertNotIn('secret',json.dumps(d))

    def video_entry(self):
        p=self.root/'videos/synthetic-fixture/episode.mp4';p.parent.mkdir(parents=True)
        shutil.copyfile(ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0001/video/episode.mp4',p)
        return dict(id='synthetic-fixture',path=str(p.relative_to(self.root)),completed=True,continuous=True,
            category='diagnostic',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),completed_at=time.time()-2)

    def test_fixture_completed_video_verified_and_revoked(self):
        item=self.video_entry();self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
        d=self.api.snapshot();self.assertEqual(len(d['videos']),1)
        v=d['videos'][0];self.assertEqual(v['category_label'],'诊断')
        self.assertEqual(self.api.video(v['url'])[0],self.root/item['path'])
        (self.root/item['path']).write_bytes(b'writing')
        self.assertIsNone(self.api.video(v['url']))

    def test_reviewed_legacy_diagnostic_manifest(self):
        entry=self.video_entry();original=self.root/entry['path']
        p=self.root/'diagnostics/door-v1-001/video/episode.mp4';p.parent.mkdir(parents=True);shutil.copyfile(original,p)
        self.write('video-manifest.json',dict(schema=1,videos=[dict(path=str(p),complete=True,kind='diagnostic',episode='door-v1-001')]))
        d=self.api.snapshot();self.assertEqual(len(d['videos']),1)
        v=d['videos'][0];self.assertEqual(v['category'],'diagnostic')
        self.assertEqual(v['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertFalse(v['source'].startswith('/'))

    def test_unfinished_video_not_probed_and_no_success_promotion(self):
        item=self.video_entry();item['completed']=False
        self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
        with patch('ikea_progress.subprocess.run') as p:
            self.assertEqual(self.api.snapshot()['videos'],[]);p.assert_not_called()
        item.update(completed=True,category='audited_success')
        self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
        self.assertEqual(self.api.snapshot()['videos'],[])

    def test_illegal_paths_and_symlinks_rejected(self):
        item=self.video_entry()
        for path in ['../../api.json','/etc/passwd','videos/../state.json','videos/../../outside.mp4','host_audit/episode.mp4']:
            item['path']=path;self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
            self.assertEqual(self.api.snapshot()['videos'],[],path)
        link=self.root/'videos/link.mp4';link.symlink_to(ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0001/video/episode.mp4')
        item['path']='videos/link.mp4';self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
        self.assertEqual(self.api.snapshot()['videos'],[])
        self.assertIsNone(self.api.video('/videos/ikea-../../api.json'))

    def test_wrong_hash_or_unreadable_video_not_published(self):
        item=self.video_entry();item['sha256']='0'*64
        self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
        self.assertEqual(self.api.snapshot()['videos'],[])
        p=self.root/item['path'];p.write_bytes(b'not-a-complete-mp4');item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        self.write('video-manifest.json',dict(schema_version=1,videos=[item]))
        self.assertEqual(self.api.snapshot()['videos'],[])


if __name__=='__main__':unittest.main(verbosity=2)
