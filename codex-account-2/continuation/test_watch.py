import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('watch', Path(__file__).with_name('watch.py'))
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class ContinuationPolicyTests(unittest.TestCase):
    def test_incomplete_turn_never_resumed(self):
        self.assertNotEqual(watch.disposition(False, None, None, True), 'continue')

    def test_quota_error_never_retried(self):
        self.assertNotEqual(watch.disposition(True, {'code': 'usageLimitExceeded'}, None, True), 'continue')

    def test_first_completed_turn_can_accept_new_handoff(self):
        self.assertEqual(watch.disposition(True, None, None, True), 'continue')

    def test_subsequent_turn_requires_explicit_state(self):
        self.assertNotEqual(watch.disposition(True, None, None, False), 'continue')
        for status in ['blocked', 'complete']:
            self.assertEqual(watch.disposition(True, None, {'status': status}, False), status)

    def test_historical_quota_quotes_do_not_trigger_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'events.jsonl'
            path.write_text('{"type":"turn.started"}\n{"type":"item.completed","item":{"text":"old usageLimitExceeded"}}\n{"type":"turn.completed"}\n')
            self.assertEqual(watch.event_status(path), (True, None))

    def test_new_incomplete_turn_cannot_reuse_old_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'events.jsonl'
            path.write_text('{"type":"turn.completed"}\n{"type":"turn.started"}\n')
            self.assertEqual(watch.event_status(path), (False, None))


if __name__ == '__main__':
    unittest.main()
