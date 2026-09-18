"""Isolated fixtures only; no production answers, owner queues or model calls."""
import copy
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from dashboard import Dashboard,RSI,hash_json
from feedback_board import FeedbackBoard,OWNERS
from store import digest,immutable
from server import make_server

OUT=RSI/'human-feedback/dashboard-upgrade'
VIDEO=RSI/'api-ground-to-table/actor-adapter/campaign/episode-0001/video/episode.mp4'
class BoardTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='fixture-unit-',dir=OUT));self.d=Dashboard(self.root);self.b=FeedbackBoard(self.d,self.root/'feedback',fixture=True)
        task={'id':'simple','sources':[],'summary':'测试公开证据'};task['version']=hash_json(task);self.task=task;self.b.publish_packages([task]);self.seq=0
    def write(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
    def payload(self,**changes):
        self.seq+=1
        return dict(request_id='fixture_request_'+str(self.seq),task_id='simple',case_id=None,source_version=self.task['version'],text='合成测试回答；不是用户反馈',choice='',user_timestamp='2026-09-16T00:00:00+00:00',correction_of=None,**changes)
    def test_unknown_not_zero_and_no_model_on_reads(self):
        with patch('subprocess.run') as run:
            d=self.d.snapshot();self.assertEqual(len(d['tasks']),4);self.assertIsNone(d['tasks'][0]['subtasks'][0]['success']);self.assertEqual(d['tasks'][0]['subtasks'][0]['state'],'unknown');self.assertEqual(d['tasks'][2]['state'],'unknown');self.assertEqual(d['tasks'][3]['state'],'unknown');run.assert_not_called()
        self.assertNotIn('hidden',json.dumps(d))
    def test_stale_inference_remains_waiting_not_failed(self):
        self.write('api-ground-to-table/actor-adapter/auxiliary-progress.json',{'state':'inference_waiting_no_deadline','updated_at_unix':time.time()-7200,'episode':'episode-0002','run_id':'api-ground-002'})
        d=self.d.ground();self.assertEqual(d['state'],'modelwaiting');self.assertGreater(time.time()-d['source_at'],7100);self.assertIsNone(d['last_action_at'])
    def test_finished_result_overrides_stale_supervisor(self):
        self.write('codex-account-2/continuation/supervisor-state.json',{'running':[{'episode':'artifacts/R019/apple-campaign/episode-0001'}]})
        self.write('artifacts/R019/apple-campaign/episode-0001/result.json',{'stop_reason':'episode_step_budget','actions':3})
        d=self.d.simple();self.assertEqual(d['subtasks'][1]['state'],'budgetstop')
    def test_latest_finalized_discovered_and_open_video_never_probed(self):
        base='artifacts/R019/door-campaign'
        for n in (1,2):
            f=self.root/base/f'episode-{n:04d}';(f/'video').mkdir(parents=True);shutil.copyfile(VIDEO,f/'video/episode.mp4')
            if n==1:self.write(str(f.relative_to(self.root)/'result.json'),{'stop_reason':'episode_step_budget'})
        d=self.d.simple()['subtasks'][0];self.assertEqual(d['videos'][0]['episode'],'episode-0001')
        with patch('dashboard.subprocess.run') as run:
            self.d.simple();run.assert_not_called()
        self.write(base+'/episode-0002/result.json',{'stop_reason':'episode_step_budget'})
        d=self.d.simple()['subtasks'][0];self.assertEqual(d['videos'][0]['episode'],'episode-0002')
        self.assertIsNone(self.d.media_file('/media/../../api.json'))
        route=d['videos'][0]['url'];(self.root/base/'episode-0002/video/episode.mp4').write_bytes(b'broken')
        self.assertIsNone(self.d.media_file(route))
    def test_incomplete_and_symlink_excluded(self):
        p=self.root/'artifacts/R019/door-campaign/episode-0001';(p/'video').mkdir(parents=True);(p/'video/episode.mp4').write_bytes(b'incomplete');self.write(str(p.relative_to(self.root)/'result.json'),{})
        self.assertEqual(self.d.simple()['subtasks'][0]['videos'],[])
        (self.root/'artifacts/R019/apple-campaign').symlink_to(p.parent)
        self.assertEqual(self.d.simple()['subtasks'][1]['videos'],[])
    def test_immutable_idempotent_correction_and_binding(self):
        p=self.payload();r=self.b.submit(p);self.assertTrue(self.b.submit(p)['duplicate']);self.assertEqual(len(self.b.all_answers()),1);self.assertFalse(r['human_feedback_used'])
        q=dict(p,text='changed')
        with self.assertRaises(ValueError):self.b.submit(q)
        q=self.payload();q['source_version']='f'*64
        self.assertEqual(self.b.submit(q)['evidence_binding']['state'],'unverified')
        q=self.payload();q['task_id']='ground'
        self.assertEqual(self.b.submit(q)['evidence_binding']['state'],'unverified')
        q=self.payload();q['correction_of']=r['feedback_id'];self.b.submit(q);self.assertEqual(len(self.b.all_answers()),4)
        path=self.b.root/'answers'/(r['feedback_id']+'.json');self.assertEqual(path.stat().st_mode&0o222,0);self.assertEqual(json.loads(path.read_text())['submission'],p)
        b=FeedbackBoard(self.d,self.b.root,fixture=True);self.assertEqual(len(b.receipts()),4)
    def test_queue_failure_saved_and_exact_bound_message_no_user_execution(self):
        captured=[]
        def fail(msg,owner):captured.append((msg,owner));return {'state':'failed'}
        b=FeedbackBoard(self.d,self.b.root,fixture=True,delivery=fail);p=self.payload();p['text']='$(touch never_execute) <script>alert(1)</script> host_hidden_sentinel';r=b.submit(p)
        for _ in range(100):
            if (b.root/'delivery'/(r['feedback_id']+'-result.json')).exists():break
            time.sleep(.01)
        self.assertEqual(len(captured),1);self.assertNotIn('never_execute',captured[0][0]);self.assertNotIn('host_hidden_sentinel',captured[0][0]);self.assertIn(p['source_version'],captured[0][0]);self.assertIn(r['feedback_id'],captured[0][0]);self.assertFalse(b.receipts()[0]['status']['queued']);self.assertTrue(b.receipts()[0]['status']['saved']);b.submit(p);self.assertEqual(len(captured),1)
    def test_priority_file_handoff_makes_no_account_call_and_ack_is_bound(self):
        b=FeedbackBoard(self.d,self.b.root,fixture=False)
        with patch('feedback_board.subprocess.run') as call:
            r=b.submit(self.payload());call.assert_not_called()
        st=b.receipts()[0]['status'];self.assertFalse(st['queued']);self.assertFalse(st['delivery_uncertain']);self.assertEqual(st['priority'],'highest');self.assertTrue(st['consumption_pending']);self.assertIsNone(st['physical_verified'])
        aid=r['feedback_id'];sha=digest((b.root/'answers'/(aid+'.json')).read_bytes())
        self.assertIn(json.loads((b.root/'delivery'/(aid+'-result.json')).read_text())['state'],('file_handoff','main_account_inbox'))
        self.assertTrue((b.root/'delivery'/(aid+'-message.json')).exists())
        immutable(b.root/'acks'/(aid+'-wrong.json'),{'feedback_id':aid,'owner':OWNERS['ground'],'answer_sha256':sha,'stage':'owner_ack'})
        self.assertIsNone(b.receipts()[0]['status']['owner_ack'])
        immutable(b.root/'acks'/(aid+'-right.json'),{'feedback_id':aid,'owner':OWNERS['simple'],'answer_sha256':sha,'stage':'owner_ack','at':'2026-09-16T00:00:00Z','note':'isolated fixture'})
        self.assertIsNotNone(b.receipts()[0]['status']['owner_ack']);self.assertIsNone(b.receipts()[0]['status']['actual_loaded']);self.assertIsNone(b.receipts()[0]['status']['physical_verified'])
        evidence=self.write('artifacts/fixture/feedback-load.json',{'feedback_id':aid,'answer_sha256':sha,'human_feedback_used':True})
        immutable(b.root/'acks'/(aid+'-loaded.json'),{'feedback_id':aid,'owner':OWNERS['simple'],'answer_sha256':sha,'stage':'loaded','evidence':str(evidence.relative_to(self.root)),'evidence_sha256':digest(evidence.read_bytes())})
        self.assertIsNotNone(b.receipts()[0]['status']['actual_loaded']);self.assertIsNone(b.receipts()[0]['status']['physical_verified'])
    def test_unverified_package_preserves_proactive_words_without_claiming_binding(self):
        p=self.b.root/'packages'/(self.task['version']+'.json');p.chmod(0o644);d=json.loads(p.read_text());d['summary']='tampered';p.write_text(json.dumps(d))
        r=self.b.submit(self.payload());self.assertEqual(r['evidence_binding']['state'],'unverified');self.assertFalse(r['human_feedback_used'])
        q=self.payload();q['case_id']='HC-test'
        with self.assertRaises(ValueError):self.b.submit(q)
    def test_coordinator_receipt_does_not_claim_actor_or_physical_use(self):
        rec=self.b.submit(self.payload());aid=rec['feedback_id']
        sha=digest((self.b.root/'answers'/(aid+'.json')).read_bytes())
        review={'feedback_id':aid,'answer_sha256':sha,'reviewer':'01a0a949-dc8e-70c3-b8a6-53131882e19d',
                'stage':'accepted_for_implementation','priority':'highest','note':'先抓起再搬运'}
        self.write('feedback/reviews/'+aid+'.json',review)
        st=self.b.status(rec)
        self.assertEqual(st['coordination']['priority'],'highest')
        self.assertIsNone(st['owner_ack']);self.assertIsNone(st['physical_verified'])
        review['answer_sha256']='0'*64;self.write('feedback/reviews/'+aid+'.json',review)
        self.assertIsNone(self.b.status(rec)['coordination'])
    def test_unconsumed_feedback_is_visible_without_three_failure_gate(self):
        rec=self.b.submit(self.payload());rec['saved_at']='2026-09-16T00:00:00+00:00'
        self.assertEqual(self.b.cases()['eligible_count'],0)
        self.assertTrue(self.b.status(rec)['attention_required'])
    def test_old_questions_and_insufficient_failures_rejected(self):
        self.assertEqual(self.b.cases()['eligible_count'],0)
        for c in ({'case_id':'H001'},{'case_id':'F001'}, {'case_id':'HC-test','task_id':'simple','unresolved':True,'attempts':[]}):
            with self.assertRaises(ValueError):self.b.validate_case(c)
    def test_physical_eligibility_excludes_budget_and_same_reset(self):
        c={'case_id':'HC-fixture','task_id':'simple','title':'合成问题','mechanism':'grasp','control_version':'test-v1','question':'哪一帧包夹成立？','choices':['A','B'],'facts':'合成事实','hypothesis':'合成假说','already_tried':'三次独立物理尝试','unresolved':True,'attempts':[]}
        for i in range(3):
            ep=f'episode-{i+1:04d}';rid='simple/apple/'+ep
            folder=self.root/'artifacts/R019/apple-campaign'/ep
            video=folder/'video/episode.mp4';video.parent.mkdir(parents=True);shutil.copyfile(VIDEO,video)
            frame=folder/'rollout/episode/observations/0001/head_stereo_left.png';frame.parent.mkdir(parents=True);frame.write_bytes(b'\x89PNG\r\n\x1a\n'+b'fixture'*20+b'\x00\x00\x00\x00IEND\xaeB`\x82')
            self.write(str(frame.parent.relative_to(self.root)/'observation.json'),{'sim_s':1})
            rp=self.write(str(folder.relative_to(self.root)/'result.json'),{'terminal_kind':'physical_failure','actions':1,'human_feedback_used':False})
            rec={'id':rid,'task':'simple','subtask':'apple','episode':ep,'actions':1,'state':'physical-failure','human_feedback_used':False,'independent_reset_verified':True,'no_replay_or_diagnostic_initial_state':True,'control_version':'test-v1','mechanism':'grasp','reset_id':'reset-'+str(i),'result_sha256':digest(rp.read_bytes())};self.d.records[rid]=rec
            evidence=self.d.case_media(rid)
            c['attempts'].append(dict(record_id=rid,result_sha256=rec['result_sha256'],reset_id=rec['reset_id'],video_url=evidence['video']['url'],keyframe_url=evidence['preview']['url'],timestamps=[1],change='test',outcome='failed'))
        self.assertIn('version',self.b.validate_case(c));self.d.records[c['attempts'][0]['record_id']]['state']='budgetstop'
        with self.assertRaises(ValueError):self.b.validate_case(c)
        self.d.records[c['attempts'][0]['record_id']]['state']='physical-failure';c['attempts'][1]=copy.deepcopy(c['attempts'][0])
        with self.assertRaises(ValueError):self.b.validate_case(c)

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(tempfile.mkdtemp(prefix='fixture-http-',dir=OUT));cls.d=Dashboard(cls.root);cls.server=make_server(0,dashboard=cls.d,feedback_root=cls.root/'feedback',fixture=True);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def req(self,path,method='GET',body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10);c.request(method,path,body,headers or {});r=c.getresponse();out=(r.status,r.read());c.close();return out
    def test_csrf_origin_paths_and_no_get_delivery(self):
        with patch('feedback_board.subprocess.run') as run:
            code,raw=self.req('/api/dashboard');d=json.loads(raw);self.assertEqual(code,200);run.assert_not_called()
        p={'request_id':'fixture-http-id','task_id':'simple','case_id':None,'source_version':d['tasks'][0]['version'],'text':'isolated fixture','choice':'','user_timestamp':'2026-09-16T00:00:00Z','correction_of':None};body=json.dumps(p);headers={'Origin':f'http://127.0.0.1:{self.server.server_port}','Content-Type':'application/json','X-CSRF-Token':d['csrf']}
        self.assertEqual(self.req('/api/feedback','POST',body,{})[0],403)
        self.assertEqual(self.req('/api/feedback','POST',body,dict(headers,**{'X-CSRF-Token':'bad'}))[0],403)
        self.assertEqual(self.req('/api/feedback','POST',body,dict(headers,Origin='http://evil.example'))[0],409)
        with patch('feedback_board.subprocess.run') as run:
            self.assertEqual(self.req('/api/feedback','POST',body,headers)[0],200);run.assert_not_called()
        self.assertEqual(self.req('/api/feedback','POST',body,headers)[0],200)
        self.assertEqual(len(json.loads(self.req('/api/feedback')[1])['answers']),1)
        for url in ['/api.json','/media/%2e%2e/api.json','/media/../../api.json','/feedback/answers/x','/agent/events.jsonl']:
            self.assertEqual(self.req(url)[0],404)

if __name__=='__main__':unittest.main()
