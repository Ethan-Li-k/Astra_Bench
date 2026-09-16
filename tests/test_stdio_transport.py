import sys
import tempfile
import unittest
from pathlib import Path

from rsi.stdio_transport import StdioAppServer


CHILD = r'''
import json, sys
for line in sys.stdin:
    message = json.loads(line)
    if message.get('method') == 'echo' and 'id' in message:
        print(json.dumps({'jsonrpc': '2.0', 'id': message['id'],
                          'result': message['params']}), flush=True)
    elif message.get('method') == 'emit' and 'id' in message:
        print(json.dumps({'jsonrpc': '2.0', 'id': message['id'],
                          'result': {'accepted': True}}), flush=True)
        print(json.dumps({'jsonrpc': '2.0', 'method': 'event/test',
                          'params': {'value': 7}}), flush=True)
'''


class StdioTransportTests(unittest.TestCase):
    def test_request_notification_queue_and_logs(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            transport = StdioAppServer(
                [sys.executable, '-u', '-c', CHILD], root)
            try:
                self.assertEqual(transport.request('echo', {'x': 1}, 2), {'x': 1})
                self.assertEqual(transport.request('emit', {}, 2), {'accepted': True})
                event = transport.next_message(2)
                self.assertEqual(event['method'], 'event/test')
                transport.notify('ignored', {})
            finally:
                transport.close()
            self.assertTrue((root/'rpc_in.jsonl').read_text())
            self.assertTrue((root/'rpc_out.jsonl').read_text())


if __name__ == '__main__':
    unittest.main()
