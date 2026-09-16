import json
import unittest
from server import byte_range, progress, MEDIA
from store import ROOT, digest


class VideoHomeTests(unittest.TestCase):
    def test_complete_range(self):
        self.assertEqual(byte_range(None, 100), (0, 99, 200))

    def test_seek_range(self):
        self.assertEqual(byte_range('bytes=20-49', 100), (20, 49, 206))
        self.assertEqual(byte_range('bytes=20-', 100), (20, 99, 206))
        self.assertEqual(byte_range('bytes=90-999', 100), (90, 99, 206))

    def test_suffix(self):
        self.assertEqual(byte_range('bytes=-10', 100), (90, 99, 206))
        self.assertEqual(byte_range('bytes=-1000', 100), (0, 99, 206))

    def test_invalid_ranges(self):
        for value in ['bytes=100-', 'bytes=50-20', 'bytes=-0', 'bytes=-', 'bytes=0-4,8-9', '../host_audit', 'other=0-4']:
            with self.assertRaises(ValueError): byte_range(value, 100)

    def test_precise_video_whitelist_and_hashes(self):
        data=progress()
        self.assertEqual(len(MEDIA),3)
        self.assertEqual(set(MEDIA),{v['url'] for v in data['videos']})
        for v in data['videos']:
            self.assertEqual(digest(MEDIA[v['url']].read_bytes()),v['sha256'])
        self.assertNotIn('/videos/../host_audit/evaluation.json',MEDIA)

    def test_public_status_closed_and_sanitized(self):
        data=progress()
        self.assertFalse(data['human_help']['open'])
        self.assertEqual(data['human_help']['minimum_comparable_independent_exploration_failures'],3)
        self.assertIsNone(data['human_help']['verified_count'])
        self.assertTrue(data['h001_progress']['failure_reproduced'])
        self.assertFalse(data['h001_progress']['correction_success_claimed'])
        for token in ['host_audit','qpos','qvel','contact_points','primary_question','next_targeted_question']:
            self.assertNotIn(token,json.dumps(data))

    def test_existing_feedback_matches_originals(self):
        data=progress()
        self.assertEqual(len(data['feedback']['H001']['replies']),4)
        for i,reply in enumerate(data['feedback']['H001']['replies'],1):
            source=json.loads((ROOT/f'H001-user-feedback-{i:03d}.json').read_text())
            self.assertEqual(reply['verbatim'],source.get('verbatim',source.get('user_original_words')))
        source=json.loads((ROOT.parent/'api-ground-to-table/cases/F001/user-feedback-001.json').read_text())
        self.assertEqual(data['feedback']['F001']['verbatim'],source['user_original_words'])

    def test_authorized_scoped_feedback_visible(self):
        # 2026-09-16 user explicitly authorized new browser feedback. Legacy remains closed.
        html=(ROOT/'ui/index.html').read_text()
        self.assertIn('<form',html)
        self.assertIn('<textarea',html)
        self.assertIn('/api/feedback',(ROOT/'ui/app.js').read_text())
        self.assertNotIn('/api/annotations',(ROOT/'ui/app.js').read_text())


if __name__=='__main__': unittest.main(verbosity=2)
