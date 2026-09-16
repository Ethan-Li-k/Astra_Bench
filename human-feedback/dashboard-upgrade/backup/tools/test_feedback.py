import concurrent.futures
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from store import ROOT, CASE, SOURCE, Store, build_lock, immutable, verify, contained


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='isolated-', dir=ROOT/'reviews/tests'))
        self.case = self.temp / 'case'
        shutil.copytree(CASE, self.case)
        self.lock = self.temp / 'source-lock.json'
        immutable(self.lock, build_lock(self.case))
        self.store = Store(self.temp, self.case, self.lock)
        self.payload = {'request_id': 'synthetic-test-request', 'case_id': 'H001',
            **self.store.binding(), 'synthetic': True, 'phase': 'independent',
            'answers': {'observation': 'SYNTHETIC：不足以判断', 'priority': 'SYNTHETIC：需要另一视角', 'gate': 'SYNTHETIC：测试文本'},
            'exposure': {'known_failure_outcome': True, 'agent_assessment_seen': False}}

    def test_no_answer_refused(self):
        for value in ['', '  ', None]:
            self.payload['answers']['gate'] = value
            with self.assertRaises(ValueError): self.store.submit(self.payload)

    def test_missing_image_refused(self):
        (self.case/'frames/0059/head_stereo_left.png').rename(self.case/'missing-image-test.png')
        with self.assertRaises(OSError): self.store.submit(self.payload)

    def test_tampered_image_refused(self):
        with (self.case/'frames/0059/head_stereo_left.png').open('ab') as out: out.write(b'synthetic-tampering')
        with self.assertRaises(ValueError): self.store.submit(self.payload)

    def test_tampered_robot_state_refused(self):
        with (self.case/'frames/0059/robot_observation.json').open('ab') as out: out.write(b' ')
        with self.assertRaises(ValueError): self.store.submit(self.payload)

    def test_tampered_case_refused(self):
        with (self.case/'case.json').open('ab') as out: out.write(b' ')
        with self.assertRaises(ValueError): self.store.submit(self.payload)

    def test_missing_original_source_refused(self):
        # Never mutate the real source: point the verifier at an empty synthetic directory.
        with self.assertRaises((ValueError, OSError)): verify(self.case, self.lock, self.temp/'missing-source')

    def test_duplicate_submission_idempotent_and_conflict_refused(self):
        first = self.store.submit(self.payload)
        second = self.store.submit(self.payload)
        self.assertEqual(first['annotation_id'], second['annotation_id'])
        self.assertTrue(second['duplicate'])
        self.payload['answers']['priority'] += ' changed'
        with self.assertRaises(ValueError): self.store.submit(self.payload)
        self.assertEqual(len(list((self.temp/'annotations/synthetic').glob('HF-*.json'))),1)

    def test_concurrent_duplicate_single_record(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            replies = list(pool.map(lambda _: self.store.submit(copy.deepcopy(self.payload)), range(6)))
        self.assertEqual(len({r['annotation_id'] for r in replies}),1)
        self.assertEqual(sum(not r['duplicate'] for r in replies),1)

    def test_outside_paths_refused(self):
        for rel in ['../outside', '/etc/passwd', 'frames/../../elsewhere']:
            with self.assertRaises(ValueError): contained(self.case, rel)
        (self.case/'outside-link').symlink_to(self.temp/'source-lock.json')
        with self.assertRaises(ValueError): contained(self.case, 'outside-link')
        self.payload['request_id']='../../traversal'
        with self.assertRaises(ValueError): self.store.submit(self.payload)
        with self.assertRaises(ValueError): self.store.read('../../anything')

    def test_stale_binding_refused(self):
        self.payload['case_sha256']='0'*64
        with self.assertRaises(ValueError): self.store.submit(self.payload)

    def test_synthetic_never_production(self):
        reply=self.store.submit(self.payload)
        self.assertFalse((self.temp/'annotations/production').exists())
        record=json.loads(self.store.read(reply['annotation_id']))
        self.assertFalse(record['human_feedback_used'])
        self.assertEqual(record['submission']['answers'],self.payload['answers'])
        self.assertEqual(record['rule_status'],'human_proposed')

    def test_exposure_and_parent_required(self):
        self.payload['exposure']['known_failure_outcome']=False
        with self.assertRaises(ValueError): self.store.submit(self.payload)
        self.payload['exposure']['known_failure_outcome']=True
        self.payload['phase']='comparison'
        with self.assertRaises(ValueError): self.store.submit(self.payload)
        self.payload['exposure']['agent_assessment_seen']=True
        with self.assertRaises(ValueError): self.store.submit(self.payload)

    def test_tampered_original_source_refused(self):
        fake_source=self.temp/'public-source'
        fake_source.mkdir()
        case=json.loads((self.case/'case.json').read_text())
        for item in case['source_manifest']:
            relative=Path(item['path']).relative_to(SOURCE)
            dest=fake_source/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(SOURCE/relative,dest)
            item['path']=str(dest)
        (self.case/'case.json').write_text(json.dumps(case))
        new_lock=self.temp/'fake-source-lock.json'
        immutable(new_lock,build_lock(self.case,fake_source))
        with (fake_source/'observations/0059/observation.json').open('ab') as out:out.write(b' ')
        with self.assertRaises(ValueError):verify(self.case,new_lock,fake_source)

    def test_import_rejects_invented_or_changed_source(self):
        from import_answers import import_payload
        from store import digest
        transcript=self.temp/'transcript.json'
        source={'source':'explicit_user_reply_in_desktop_thread','case_id':'H001','verbatim':'SYNTHETIC transcript'}
        transcript.write_text(json.dumps(source))
        payload=copy.deepcopy(self.payload)
        payload['phase']='desktop_transcription'
        payload['transcripts']=[{'file':str(transcript.relative_to(ROOT)),'sha256':digest(transcript.read_bytes()),'verbatim':source['verbatim']}]
        inp=self.temp/'input.json';inp.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):import_payload(inp)
        with transcript.open('a') as out:out.write(' ')
        with self.assertRaises(ValueError):import_payload(inp)


if __name__ == '__main__': unittest.main(verbosity=2)
