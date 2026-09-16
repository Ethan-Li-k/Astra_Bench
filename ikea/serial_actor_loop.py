"""Future caller loop. One host/history; only verified batch transitions."""
import hashlib
import json
from pathlib import Path
from serial_batch_continuation import SerialBatchContinuation


class SerialActorLoop:
    def __init__(self,host,gate,history,session,replacement_factory,output,save,
                 *,model,effort,max_tokens,max_body):
        self.host,self.gate,self.history=host,gate,history
        self.output,self.save=Path(output),save
        self.base=dict(model=model,reasoning={'effort':effort},store=False,stream=True,
            max_output_tokens=max_tokens,parallel_tool_calls=False,
            include=['reasoning.encrypted_content'])
        self.max_body=max_body
        self.bridge=SerialBatchContinuation(session,host,replacement_factory,
            self.output/'serial-batch-transitions.jsonl')
        self.flat_calls=self.output/'api-calls';self.flat_calls.mkdir()
        self.global_calls=0

    def run(self):
        host,gate,history=self.host,self.gate,self.history
        while not gate.concluded:
            session=self.bridge.ready(phase='terminal_review' if host.finished else 'policy')
            host.progress('inference_waiting')
            choice=({'type':'function','name':'experience_select'} if not host.selection_recorded else
                {'type':'function','name':'conclude'} if host.finished else 'required')
            payload=history.payload(dict(self.base,tool_choice=choice,tools=gate.specs()),self.max_body)
            before_count=session.count
            try:
                response=session.call(payload)
            finally:
                if session.count>before_count:
                    self.global_calls+=1
                    source=session.output/f'{session.count:02d}'
                    if source.exists():(self.flat_calls/f'{self.global_calls:02d}').symlink_to(source,target_is_directory=True)
                    with (self.output/'api-call-series.jsonl').open('a') as stream:
                        stream.write(json.dumps(dict(global_call=self.global_calls,run_id=session.run_id,
                            batch_call=session.count,source=str(source)))+'\n')
            calls=[item for item in response.get('output',[]) if item.get('type')=='function_call']
            if len(calls)!=1:raise RuntimeError('Exactly one completed actor tool exchange required; no automatic retry')
            call=calls[0]
            try:packet=gate.dispatch(call['name'],json.loads(call['arguments']))
            except ValueError as exc:
                if host.execution_error or (host.backend and host.backend.active):raise
                packet=dict(error_type='validation_rejected',error=str(exc),no_execution=True,
                    observation_path=str(host.harness.latest_path),next_call=host.next_call())
            if not isinstance(packet,dict):packet=dict(public_evidence=packet)
            packet['current_batch_calls_remaining']=session.max_calls-session.count
            packet['same_episode_continuation']='Completed batches continue through the unchanged shared budget; no reset or action replay.'
            evidence=host.rollout_root/f'public_tool_{self.global_calls:04d}.json'
            self.save(evidence,packet);gate.register({'path':str(evidence)})
            history.append(response['output'],call,packet,gate.content(packet),
                dict(path=str(evidence),sha256=hashlib.sha256(evidence.read_bytes()).hexdigest()))
            self.save(self.output/'public-history-index.json',history.index)
            public_index=host.rollout_root/'public-history-index.json'
            self.save(public_index,history.index);gate.register({'path':str(public_index)})
        return self.global_calls
