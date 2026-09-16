"""No HTTP connection, credentials or provider calls in these tests."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path('/home/galbot/lizekai/RSI')
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))

class Stream:
    status=200
    def __init__(self,events):self.lines=[b'data: '+json.dumps(x).encode()+b'\n' for x in events]
    def __iter__(self):return iter(self.lines)
    def getheader(self,name):return {'x-request-id':'req-test','content-type':'text/event-stream'}.get(name)

class StreamTests(unittest.TestCase):
    def test_missing_terminal_has_safe_evidence(self):
        from stream_evidence import consume,StreamEvidenceError
        stream=Stream([{'type':'response.created','response':{'id':'resp-secret-test','private':'NEVER_EXPORT'}},
                       {'type':'response.reasoning_text.delta','delta':'NEVER_EXPORT'}])
        stream.lines.append(b'data: [DONE]\n')
        with self.assertRaises(StreamEvidenceError) as ctx:consume(stream)
        e=ctx.exception;self.assertEqual(e.code,'missing_terminal_response');self.assertTrue(e.public['done_marker_seen'])
        self.assertFalse(e.public['terminal_event_seen']);self.assertNotIn('NEVER_EXPORT',json.dumps(e.public))
        self.assertNotIn('resp-secret-test',json.dumps(e.public))
    def test_complete_return_and_full_drain(self):
        from stream_evidence import consume
        s=Stream([{'type':'response.completed','response':{'id':'resp-test','status':'completed','output':[]}}])
        s.lines.append(b'data: [DONE]\n');d=consume(s)
        self.assertEqual(d['status'],'completed');self.assertEqual(d['_transport']['http_status'],200)
        self.assertTrue(d['_transport']['stream_evidence']['done_marker_seen'])
    def test_malformed_event_never_becomes_completion(self):
        from stream_evidence import consume,StreamEvidenceError
        s=Stream([]);s.lines=[b'data: malformed_private_body\n']
        with self.assertRaises(StreamEvidenceError) as ctx:consume(s)
        self.assertEqual(ctx.exception.code,'malformed_stream_event')
        self.assertNotIn('malformed_private_body',str(ctx.exception))
    def test_failed_response_remains_failed(self):
        from stream_evidence import consume
        d=consume(Stream([{'type':'response.failed','response':{'status':'failed','error':{'code':'test'}}}]))
        self.assertEqual(d['status'],'failed')

if __name__=='__main__':unittest.main(verbosity=2)
