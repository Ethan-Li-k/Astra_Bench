"""Responses SSE consumption with content-free evidence; no retries/deadlines."""
import json
import re
import time

KNOWN={'response.created','response.queued','response.in_progress','response.completed',
       'response.failed','response.incomplete','response.output_item.added','response.output_item.done',
       'response.content_part.added','response.content_part.done','response.output_text.delta',
       'response.output_text.done','response.function_call_arguments.delta','response.function_call_arguments.done',
       'response.reasoning_summary_text.delta','response.reasoning_summary_text.done',
       'response.reasoning_text.delta','response.reasoning_text.done','error'}
TERMINAL={'response.completed','response.failed','response.incomplete'}

class StreamEvidenceError(RuntimeError):
    def __init__(self,code,public):
        super().__init__(code+'; no retry; remote result/expense may be unknown')
        self.code,self.public=code,public

def consume(stream):
    started=time.monotonic();request_id=stream.getheader('x-request-id')
    request_id=request_id if isinstance(request_id,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',request_id) else None
    info=dict(http_status=stream.status,provider_request_id=request_id,bytes_received=0,data_lines=0,
        event_counts={},done_marker_seen=False,terminal_event_seen=False,stream_eof=False,
        inference_deadline=None,automatic_retries=0,private_content_recorded=False)
    terminal=None
    def fail(code):
        info['duration_s']=time.monotonic()-started
        raise StreamEvidenceError(code,dict(info)) from None
    try:
        for line in stream:
            info['bytes_received']+=len(line)
            if not line.startswith(b'data:'):continue
            info['data_lines']+=1;data=line[5:].strip()
            if data==b'[DONE]':info['done_marker_seen']=True;continue
            try:event=json.loads(data)
            except (ValueError,UnicodeError):fail('malformed_stream_event')
            if not isinstance(event,dict):fail('malformed_stream_event')
            kind=event.get('type');label=kind if isinstance(kind,str) and kind in KNOWN else 'other'
            info['event_counts'][label]=info['event_counts'].get(label,0)+1
            if isinstance(kind,str) and kind in TERMINAL:
                if not isinstance(event.get('response'),dict):fail('malformed_terminal_event')
                terminal=event['response'];info['terminal_event_seen']=True
        info['stream_eof']=True
    except StreamEvidenceError:raise
    except Exception:fail('stream_read_error')
    if terminal is None:fail('missing_terminal_response')
    info['duration_s']=time.monotonic()-started
    terminal['_transport']=dict(http_status=stream.status,provider_request_id=request_id,stream_evidence=info)
    return terminal
