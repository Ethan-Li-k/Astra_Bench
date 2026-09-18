"""Candidate transport for CENTRAL integration inside the still-live host scope.

No reset, process launcher, credential reader or stand-alone actor entry point.
The existing owner supplies a normally reviewed schema2 batch factory. Every
request uses the unchanged ResponsesSession reserve/begin/settle path.
"""
import hashlib,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('/home/galbot/lizekai/RSI/codex-account-2/continuation')))
from rsi.actor_transport import modules,MODEL,EFFORT
from rsi.actor_transport import atomic
from rsi.actor_inputs import read_evidence
from rsi.actor_quota_boundary import quota_terminal
from rsi.actor_inputs import verify_actor_inputs

# Transport serialization limit only; the fixed evidence window and budget gates
# remain unchanged. Original PNGs plus their base64 envelope can exceed 2 MB.
REQUEST_BYTE_CAP = 16 * 1024 * 1024

def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def complete_history_payload(history,base,max_bytes):
    from rsi.api_context import bounded_payload
    return bounded_payload(history,base,max_bytes)

class SameResetAPI:
    @staticmethod
    def build_specs(host):
        specs=[dict(type='function',name=s['name'],description=s.get('description',''),parameters=s['inputSchema'])
               for s in host.tool_specs() if s['name']!='loco_start']
        for spec in specs:
            if spec['name']=='experience_read':spec['description']+=' First call with {}. Only pass version if that version is actually listed in returned public memory.'
        for name,key in [('read_confirmed_receipt','request_id'),('read_actor_input','path'),
                         ('read_history_archive','id'),('read_public_exchange','sequence'),('record_public_note','note')]:
            specs.append(dict(type='function',name=name,description=('Append a short public observation/decision note to this episode NOTES; never executes an action.' if name=='record_public_note' else 'Read an exact pinned public input or issued past public record; never executes.'),parameters={'type':'object','properties':{key:{'type':'integer' if key=='sequence' else 'string'}},'required':[key],'additionalProperties':False}))
            if name == 'read_actor_input':
                specs[-1]['description'] += ' Current observation hand geometry: path alone gives exact local bounds, not contact surfaces; optional body and part read unchanged named geometry within 200KB. Workspace/CONTROL already appear in initial context.'
                specs[-1]['parameters']['properties'].update(body={'type':'string'}, part={'type':'integer'})
            if name == 'record_public_note':
                specs[-1]['parameters']['properties']['note'].update(minLength=1, maxLength=1400)
        # Responses otherwise normalizes optional fields into required fields.
        # Host-side argument and motion validation remains unchanged.
        for spec in specs:spec['strict']=False
        return specs

    def __init__(self,adapter,out,*,quota_receipt,binding,initial_public_packet,
                 instructions,batch_factory,send=None,content_items=None,initial_receipt=None):
        self.adapter,self.host=adapter,adapter.host
        self.backend=self.host.backend;self.reset=adapter._reset_id()
        self.out=Path(out);self.out.mkdir(exist_ok=False)
        self.batch_factory=batch_factory;self.send=send;self.binding=binding
        self.content_items=content_items
        self.receipts=self.out/'actions';self.receipts.mkdir()
        self.seen={};self.turns=0;self.tools_called=0;self.exchanges=[];self.archives={};self.start_actions=self.host.actions;self.read_keys=set();self.empty_outputs=set()
        self.initial_receipt=initial_receipt
        if initial_receipt is not None:
            initial=read_evidence(initial_receipt)
            if (quota_receipt is not None or initial.get('contract')!='api-first-live-host-v1'
                    or initial.get('reset_id')!=self.reset or initial.get('actions')!=self.host.actions
                    or adapter.turn_ids or adapter.thread_id is not None or adapter.turn_id is not None):
                raise ValueError('fresh_API_first_host_receipt_required')
        else:
            terminal=read_evidence(quota_receipt)
            meta=terminal.get('_rsi_terminal',{})
            if not quota_terminal(terminal) or not adapter.turn_ids or terminal.get('id')!=adapter.turn_ids[-1] or meta.get('thread_id')!=adapter.thread_id or meta.get('reset_id')!=self.reset or adapter.turn_id is not None:
                raise ValueError('matched_closed_quota_terminal_required')
        if not self.reset or self.host is not adapter._episode_host or self.backend is not adapter._episode_backend:
            raise ValueError('original_live_host_backend_reset_required')
        self.check_live()
        if self.host.finished: raise ValueError('already_terminal_not_a_recoverable_reset')
        if binding.get('user_authorization'):
            from rsi.direct_api import verify_direct_binding
            verify_direct_binding(binding)
        else:
            approval=read_evidence(binding['execution_approval'])
            from operation_review import verify_execution_review
            verify_execution_review(approval,{k:v for k,v in binding.items() if k!='execution_approval'})
        if binding.get('reset_id')!=self.reset or (not binding.get('user_authorization') and binding.get('owner')!='01a0a867-d7aa-71f2-8547-e264d6d09ede') or binding.get('model')!=MODEL or binding.get('effort')!=EFFORT:
            raise ValueError('owner_reset_model_binding_mismatch')
        if binding.get('instruction_sha256')!=hashlib.sha256(instructions.encode()).hexdigest():
            raise ValueError('unchanged_actor_instruction_manifest_required')
        for source in binding['sources']:read_evidence(source,json_document=False)
        # Import already ACKed request IDs without executing anything. Missing or
        # empty results at the old transport boundary prevent switching.
        for path in sorted(adapter.calls.glob('*_request.json')):
            request=json.loads(path.read_text());result=path.with_name(path.name.replace('_request.json','_result.json'))
            if not result.exists() or not result.stat().st_size:raise ValueError('unknown_prior_tool_no_replay')
            packet=json.loads(result.read_text());args=request.get('arguments',{})
            if isinstance(args,str):args=json.loads(args)
            key=(args.get('response',{}).get('request_id') or 'tool:'+str(request.get('call_id'))) if isinstance(args,dict) else None
            if key:self.seen[key]=dict(fingerprint=digest(dict(name=request['tool'],arguments=args)),packet=packet)
        if binding.get('direct_api') is True:
            from rsi.actor_transport import transport_only
            transport=transport_only()
        else:transport,_,_=modules()
        self.transport=transport
        class EpisodeHistory(transport.PublicHistory):
            # Keep complete exchanges in memory and on disk. The input view retains
            # current/correction observations, causal indices and exact lookup;
            # it never truncates model output or deletes source evidence.
            def append(self,*args,**kwargs):
                previous=list(self.groups);super().append(*args,**kwargs)
                self.groups=previous+[self.groups[-1]]
            def append_completed_turn(self,*args,**kwargs):
                previous=list(self.groups);super().append_completed_turn(*args,**kwargs)
                self.groups=previous+[self.groups[-1]]
            def payload(self,*args,**kwargs):
                return complete_history_payload(self,*args,**kwargs)
        from rsi.api_context import compact_initial
        initial_public_packet=compact_initial(initial_public_packet,self.adapter.input_manifest['files'])
        self.history=EpisodeHistory(instructions,dict(reset_id=self.reset,backend='authorized_responses_api',
            tools='Original frozen host dynamic tools; same reset; no loco_start or normal shell.',
            confirmed_public_receipt_ids=list(self.seen)),self.content({k:v for k,v in initial_public_packet.items() if k not in ('observation','observation_path','next_call')}))
        # Keep the latest public RGB/state available even after read-only tool
        # exchanges evict the original observation from the two-group history.
        self.history.static_input_paths={str(self.adapter.workspace/name) for name in ('workspace.json','CONTROL_CONTRACT.md')} | {s['path'] for s in initial_public_packet['active_experience_full_sources']}
        self.history.initial_observation=initial_public_packet['observation']
        self.initial_public_packet=initial_public_packet
        self.current_context_index=len(self.history.prefix)
        self.history.static_prefix_count=self.current_context_index
        self.history.prefix.append({'role':'user','content':[]})
        self.refresh_current_public_context()
        atomic(self.out/'initial-public-packet.json',initial_public_packet)
        atomic(self.out/'binding.json',dict(binding=binding,quota_receipt=quota_receipt,initial_receipt=initial_receipt,reset_id=self.reset,
            pid=os.getpid(),same_host=True,same_backend=True,prior_request_ids=list(self.seen),new_requests=0))

    def check_live(self):
        verify_actor_inputs(self.adapter.input_manifest,self.adapter.developer_instructions)
        if self.binding.get('api_tool_contract_sha256')!=digest(self.build_specs(self.host)):
            raise ValueError('API_tool_contract_changed_or_unreviewed')
        if not getattr(self.host,'_actor_caller_open',False):raise ValueError('original_caller_closed_no_resume')
        if self.host is not self.adapter.host or self.host.backend is not self.backend or self.adapter._reset_id()!=self.reset:
            raise ValueError('live_identity_changed_no_resume')
        # LiveSim.closed is the Dex3 target array, not a lifecycle flag.
        if self.host.harness is None or getattr(self.backend,'closed',False) is True:raise ValueError('host_closed_no_resume')
        if getattr(self.backend,'active',None):raise ValueError('inflight_action_wait_without_switch')
        if getattr(self.host,'execution_error',None) or getattr(self.host,'initialization_error',None):raise ValueError('host_system_error_no_resume')

    def content(self,packet):
        if self.content_items is None:
            from rsi.codex_app_server import _content_items
            items=_content_items(packet)
        else:items=self.content_items(packet)
        return [dict(type='input_text',text=v['text']) if v['type']=='inputText'
                else dict(type='input_image',image_url=v['imageUrl']) for v in items]

    def refresh_current_public_context(self):
        path=Path(self.host.harness.latest_path)
        packet=dict(observation_path=str(path),observation=json.loads(path.read_text()),next_call=self.host.next_call())
        self.history.current_observation=packet['observation']
        self.history.prefix[self.current_context_index]={'role':'user','content':self.content(packet)}

    def dispatch(self,call):
        self.check_live();name=call['name'];arguments=json.loads(call['arguments'])
        if name in ('read_actor_input','read_history_archive','read_confirmed_receipt','read_public_exchange'):
            key=digest({'name':name,'arguments':arguments})
            if key not in self.read_keys:self.read_keys.add(key);self.tools_called+=1
        if name=='record_public_note':
            if (not isinstance(arguments,dict) or set(arguments)!={'note'}
                    or not isinstance(arguments['note'],str) or not 1<=len(arguments['note'].strip())<=1400):
                return dict(error='note must be a nonempty string of at most 1400 characters.',
                    no_execution=True, retryable=True, note_recorded=False,
                    hint='Shorten the note or continue the task. No note or physical action was executed.')
            path=self.adapter.workspace/'NOTES.md'
            if path.is_symlink():raise ValueError('Episode note cannot be a symlink')
            with path.open('a') as stream:stream.write(arguments['note'].strip()+'\n')
            self.tools_called+=1
            return dict(path=str(path),note_recorded=True,actions=self.host.actions)
        if name=='read_actor_input':
            from rsi.public_hand_geometry import read_hand_geometry
            geometry = read_hand_geometry(self.host.harness.latest_path, arguments)
            if geometry is not None: return geometry
            if set(arguments)!={'path'} or arguments['path'] not in self.adapter.input_manifest['files']:
                # A denied read is feedback, not a reason to close the scene.
                # Only exact already-issued history references receive a hint;
                # never read or register the requested unapproved path.
                for entry in self.exchanges:
                    paths=[entry.get('public_output',{}).get('path'),str(self.out/f'public-exchange-{entry["sequence"]:06d}.json')]
                    if arguments.get('path') in paths:
                        return dict(read_rejected='History is read by sequence, not read_actor_input.',use_tool='read_public_exchange',arguments={'sequence':entry['sequence']},no_physical_action=True)
                return dict(read_rejected='exact_pinned_public_input_required',hint='Use public_input_paths for static files or read_public_exchange for issued history.',no_physical_action=True)
            path=Path(arguments['path'])
            if path.stat().st_size>200000:return dict(read_rejected='Public input exceeds the file-read size limit; select a smaller pinned input.',no_physical_action=True)
            if path.suffix=='.png':return {'images':[{'path':str(path)}]}
            return {'path':str(path),'public_text':path.read_text()}
        if name=='read_history_archive':
            if set(arguments)!={'id'} or arguments['id'] not in self.archives:raise ValueError('issued_history_archive_required')
            return dict(archive_id=arguments['id'],
                public_history_index=json.loads(Path(self.archives[arguments['id']]).read_text()))
        if name=='read_public_exchange':
            if set(arguments)!={'sequence'} or type(arguments['sequence']) is not int or not 1<=arguments['sequence']<=len(self.exchanges):
                raise ValueError('Issued_public_exchange_required')
            # Entire public response and ACKed tool output remain accessible after
            # history compaction; host receipts/budget data are never returned.
            path=self.out/f'public-exchange-{arguments["sequence"]:06d}.json'
            original=json.loads(path.read_text());packet=original.get('packet') or {}
            observation=packet.get('observation',{})
            if observation.get('images'):
                # Explicit retrieval reattaches the original RGB pair. This is
                # historical evidence, never a fresh robot-state observation.
                return dict(original,images=observation['images'],observation_path=packet.get('observation_path'),
                    historical_observation_reference={'observation_id':observation.get('observation_id'),
                        'sim_s':observation.get('sim_s'),'is_current':False})
            return original
        if name=='read_confirmed_receipt':
            if set(arguments)!={'request_id'}:raise ValueError('exact_receipt_ID_required')
            return self.seen[arguments['request_id']]['packet']
        allowed={s['name'] for s in self.host.tool_specs()}-{'loco_start'}
        if name not in allowed or not isinstance(arguments,dict):raise ValueError('original_host_tool_required')
        key=arguments.get('response',{}).get('request_id') or 'tool:'+str(call['call_id'])
        fingerprint=digest(dict(name=name,arguments=arguments))
        if key in self.seen:
            if self.seen[key]['fingerprint']!=fingerprint:raise ValueError('request_ID_changed_arguments')
            return self.seen[key]['packet']
        path=self.receipts/(hashlib.sha256(key.encode()).hexdigest()+'.json')
        if path.exists():raise ValueError('unknown_action_receipt_never_replayed')
        atomic(path,dict(status='inflight',request_id=key,fingerprint=fingerprint,reset_id=self.reset))
        before_actions=self.host.actions
        before_sim_s=float(self.backend.data.time)
        try:
            packet=self.host.dispatch(name,arguments)
        except ValueError as error:
            # Match the existing Codex adapter's validation feedback, while
            # proving that no physical execution occurred before retrying.
            if (self.host.actions!=before_actions or float(self.backend.data.time)!=before_sim_s
                    or getattr(self.backend,'active',None) or self.host.execution_error):
                raise
            packet=dict(error_type='ValueError',error=str(error),no_execution=True,retryable=True,next_call=self.host.next_call())
            if name=='experience_read':packet['hint']='Call experience_read with {} for the current index; do not invent version numbers.'
        self.check_live()
        atomic(path,dict(status='completed',request_id=key,fingerprint=fingerprint,reset_id=self.reset,packet=packet))
        self.seen[key]=dict(fingerprint=fingerprint,packet=packet);self.tools_called+=1
        return packet

    def run(self):
        if (self.out/'blocked.json').exists():raise ValueError('unknown_or_blocked_API_route_not_replayed')
        from rsi.training_gate import check_stop
        try:
            while not self.host.skill_updated:
                check_stop(self.host,self.out)
                self.check_live()
                run,folder,hook=self.batch_factory(self.reset,self.out)
                if hook.batch.get('branch')!='simple' or hook.batch.get('batch_id')!=run or hook.batch.get('model')!=MODEL or hook.batch.get('reasoning_effort')!=EFFORT:
                    raise ValueError('reviewed_actor_schema2_batch_required')
                allowance=hook.batch['max_calls']
                if type(allowance) is not int or not 1<=allowance<=120:raise ValueError('reviewed_batch_allowance_required')
                session_type=getattr(hook,'session_type',self.transport.ResponsesSession)
                session=session_type(Path(folder)/'calls',hook,self.send or self.transport.HTTPSResponses(),run,max_calls=6)
                session.max_calls=allowance
                while not self.host.skill_updated and session.count<allowance:
                    check_stop(self.host,self.out)
                    self.check_live()
                    specs=self.build_specs(self.host)
                    if len(self.history.index)>=115:
                        key='archive-'+str(len(self.archives)+1);path=self.out/(key+'.json')
                        atomic(path,self.history.index);self.archives[key]=str(path);self.history.index=[]
                        self.history.prefix.append({'role':'user','content':'Earlier complete public receipts remain in history archive '+key})
                    self.refresh_current_public_context()
                    request_options=dict(model=MODEL,reasoning={'effort':EFFORT},store=False,stream=True,
                        max_output_tokens=16384,parallel_tool_calls=False,tools=specs)
                    if getattr(hook,'direct_requests',False):request_options.pop('max_output_tokens')
                    if getattr(self.send,'background',False) is True:
                        request_options['background']=True
                    payload=self.history.payload(request_options,REQUEST_BYTE_CAP)
                    response=session.call(payload);self.turns+=1
                    receipt=Path(folder)/'calls'/f'{session.count:02d}'/'receipt.json'
                    exchange=dict(sequence=self.turns,reset_id=self.reset,receipt={'path':str(receipt),'sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()},public_output={'path':str(receipt.parent/'public_output.json'),'sha256':hashlib.sha256((receipt.parent/'public_output.json').read_bytes()).hexdigest()},actions_before=self.host.actions,actions_after=self.host.actions,tool=None)
                    self.exchanges.append(exchange)
                    public_exchange=self.out/f'public-exchange-{self.turns:06d}.json'
                    atomic(public_exchange,dict(sequence=self.turns,response=self.transport.public_response(response),packet=None))
                    check_stop(self.host,self.out)
                    calls=[v for v in response['output'] if v['type']=='function_call']
                    evidence=dict(path=str(public_exchange),tool='read_public_exchange',sequence=self.turns)
                    if not calls:
                        marker=digest(dict(output=self.transport.public_response(response),next_call=self.host.next_call(),actions=self.host.actions))
                        repeated=marker in self.empty_outputs
                        self.empty_outputs.add(marker)
                        self.history.append_completed_turn(response['output'],[dict(type='input_text',text='Same live reset; natural model turn end does not finish physics. Next call: '+json.dumps(self.host.next_call()))],evidence)
                        atomic(self.out/'exchanges.json',self.exchanges)
                        if repeated:
                            from rsi.episode_continuation import wait_for_network_diagnosis
                            wait_for_network_diagnosis(self.adapter,self.out,boundary_name='api-empty-'+str(self.turns),reason='repeated_identical_completed_API_turn_without_new_information')
                        continue
                    if len(calls)!=1:raise ValueError('one_host_tool_per_exchange')
                    before_calls=self.tools_called
                    packet=self.dispatch(calls[0])
                    atomic(public_exchange,dict(sequence=self.turns,response=self.transport.public_response(response),packet=packet))
                    exchange.update(actions_after=self.host.actions,tool=calls[0]['name'],call_id=calls[0]['call_id'],confirmed_tool=self.tools_called>before_calls,arguments_sha256=digest(json.loads(calls[0]['arguments'])))
                    atomic(self.out/'exchanges.json',self.exchanges)
                    self.history.append(response['output'],calls[0],packet,self.content(packet),evidence)
                    atomic(self.out/'public-history-index.json',self.history.index)
                    if self.tools_called>before_calls:self.empty_outputs.clear()
                    if self.tools_called==before_calls and calls[0]['name'] in ('scalebfm_act','loco_execute'):
                        from rsi.episode_continuation import wait_for_network_diagnosis
                        wait_for_network_diagnosis(self.adapter,self.out,boundary_name='api-cached-'+str(self.turns),reason='API_reused_receipt_no_new_execution')
            if not self.host.finished:raise ValueError('skill_updated_without_episode_terminal')
            result=dict(contract='same-reset-api-terminal-v1',status='host_finished_and_skill_recorded',reset_id=self.reset,same_host=True,
                same_backend=True,model=MODEL,effort=EFFORT,new_requests=self.turns,tool_calls=self.tools_called,
                physical_success_claimed=False,skill_updated=bool(self.host.skill_updated),host_finished=bool(self.host.finished),
                codex_thread_id=self.adapter.thread_id,codex_turn_id=(self.adapter.turn_ids[-1] if self.adapter.turn_ids else None),initial_receipt=self.initial_receipt,start_actions=self.start_actions,end_actions=self.host.actions,exchanges=self.exchanges)
            atomic(self.out/'result.json',result);return result
        except Exception as error:
            atomic(self.out/'blocked.json',dict(status='blocked',reason=type(error).__name__,reset_id=self.reset,
                original_hold_retained=True,unknown_replay=False,goal_complete=False,new_requests=self.turns))
            raise
