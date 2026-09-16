"""Focused regression tests; fixtures/evidence stay in the UI verification domain."""
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from api_progress import APIProgress, ADAPTER
from server import make_server, MEDIA

EVIDENCE = ADAPTER.parents[1] / 'human-feedback/dashboard-upgrade'


class PublicProgressTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=EVIDENCE))
        self.api = APIProgress(self.root)
        self.folder = self.root / 'campaign/episode-0002'
        self.folder.mkdir(parents=True)
        self.write('auxiliary-progress.json', dict(run_id='api-ground-002', episode='episode-0002',
            state='inference_waiting_no_deadline', api_calls_completed=20, actions=10,
            physical_s=49.54, updated_at_unix=time.time(), physics_paused=True))

    def write(self, relative, value):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value))

    def finish(self, kind='budget_limited_incomplete', **kwargs):
        self.write('campaign/episode-0002/result.json', dict(episode_id='episode-0002',
            run_id='api-ground-002', terminal_kind=kind, api_calls=24, actions=12,
            backend='MuJoCo', **kwargs))

    def test_no_result_keeps_inference_and_unverified(self):
        d = self.api.snapshot()
        self.assertEqual(d['state'], 'inference_waiting_no_deadline')
        self.assertTrue(d['physics_paused'])
        self.assertEqual(d['api_calls_completed'], 20)
        self.assertEqual(d['actions'], 10)
        self.assertEqual(d['physical_s'], 49.54)
        self.assertIsNone(d['terminal_kind'])
        self.assertEqual(set(d['verification'].values()), {'未验证'})
        self.assertEqual(d['videos'], [])

    def test_budget_cutoff_is_not_physical_failure(self):
        self.finish(physical_failure=False, native_outcome='in_progress')
        d = self.api.snapshot()
        self.assertEqual(d['state'], 'ended')
        self.assertEqual(d['terminal_kind'], 'budget_limited_incomplete')
        self.assertIn('不是物理失败', d['terminal_label'])
        self.assertEqual(d['api_calls_completed'], 24)
        self.assertIsNone(d['physical_s'])  # Never equate video duration with physical time.

    def test_backend_error_not_inference_timeout(self):
        self.finish('infrastructure_error', error='do-not-return-private-exception')
        d = self.api.snapshot()
        self.assertEqual(d['terminal_kind'], 'infrastructure_error')
        self.assertNotIn('do-not-return', json.dumps(d))

    def test_stale_source_only_has_age(self):
        p = self.root / 'auxiliary-progress.json';d=json.loads(p.read_text())
        d['updated_at_unix'] = time.time()-7200;p.write_text(json.dumps(d))
        data = self.api.snapshot()
        self.assertGreater(data['age_s'], 7199)
        self.assertEqual(data['state'], 'inference_waiting_no_deadline')
        self.assertIsNone(data['terminal_kind'])

    def test_broken_progress_and_source_projection(self):
        (self.root / 'auxiliary-progress.json').write_text('{unfinished')
        self.assertEqual(self.api.snapshot()['state'], 'unknown')
        self.finish(host_audit={'secret': 'never-return-this'}, video='/etc/passwd')
        d = self.api.snapshot()
        self.assertNotIn('never-return-this', json.dumps(d))
        self.assertNotIn('/etc/passwd', json.dumps(d))
        self.assertEqual(d['videos'], [])

    def test_no_result_does_not_probe_writing_video(self):
        (self.folder / 'video').mkdir()
        (self.folder / 'video/episode.mp4').write_bytes(b'writing')
        with patch('api_progress.subprocess.run') as probe:
            self.assertEqual(self.api.snapshot()['videos'], [])
            probe.assert_not_called()

    def test_invalid_video_remains_unpublished(self):
        self.finish();(self.folder / 'video').mkdir()
        (self.folder / 'video/episode.mp4').write_bytes(b'incomplete-mp4')
        self.assertEqual(self.api.snapshot()['videos'], [])

    def test_complete_video_and_mutation_revocation(self):
        self.finish();(self.folder / 'video').mkdir()
        p=self.folder / 'video/episode.mp4'
        shutil.copyfile(ADAPTER / 'campaign/episode-0001/video/episode.mp4', p)
        data=self.api.snapshot();v=data['videos'][0]
        self.assertEqual(len(v['sha256']),64)
        self.assertEqual(self.api.video(v['url'])[0],p)
        self.assertIsNone(self.api.video('/videos/api-ground-../../api.json'))
        p.write_bytes(b'changed')
        with self.assertRaises(ValueError): self.api.video(v['url'])
        self.assertEqual(self.api.snapshot()['videos'], [])

    def test_symlink_and_path_injection_rejected(self):
        (self.folder / 'result.json').symlink_to(ADAPTER/'campaign/episode-0001/result.json')
        self.assertEqual(self.api.snapshot()['videos'], [])
        self.write('auxiliary-progress.json', {'episode':'../../api.json','run_id':'/etc/passwd'})
        d=self.api.snapshot()
        self.assertIsNone(d['episode']);self.assertIsNone(d['run_id'])


class HTTPRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path,headers=None,method='GET'):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=15)
        c.request(method,path,headers=headers or {})
        r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result

    def test_old_range_still_matches_original_bytes(self):
        for route,p in MEDIA.items():
            status,headers,body=self.request(route,{'Range':'bytes=100-199'})
            self.assertEqual(status,206)
            self.assertEqual(body,p.read_bytes()[100:200])
            self.assertTrue(headers['Content-Range'].startswith('bytes 100-199/'))

    def test_new_video_range_and_hash_source(self):
        status,_,body=self.request('/api/ground-progress');self.assertEqual(status,200)
        d=json.loads(body);v=next(x for x in d['videos'] if 'episode-0001' in x['id'])
        status,headers,body=self.request(v['url'],{'Range':'bytes=0-99'})
        self.assertEqual(status,206);self.assertEqual(len(body),100)
        self.assertEqual(self.request(v['url'],method='HEAD')[0],200)
        self.assertNotIn('host_audit',json.dumps(d))

    def test_arbitrary_paths_and_host_origin_refused(self):
        for p in ['/api.json','/tools/server.py','/host_audit/evaluation.json',
                  '/videos/api-ground-../../api.json','/videos/api-ground-episode-9999.mp4',
                  '/videos/%2e%2e/host_audit/evaluation.json',
                  '/api/ground-progress/../../api.json']:
            self.assertEqual(self.request(p)[0],404,p)
        self.assertEqual(self.request('/api/ground-progress',{'Host':'evil.example'})[0],409)
        self.assertEqual(self.request('/api/ground-progress',{'Origin':'http://evil.example'})[0],409)
        self.assertEqual(self.request('/api/annotations',method='POST')[0],410)


if __name__=='__main__': unittest.main(verbosity=2)
