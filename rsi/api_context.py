"""Public input views only: original exchanges and reasoning output stay intact."""
import copy
import hashlib
import json
from pathlib import Path


def _read_index(args, result, delivered, sequence):
    """Index observed delivery, not a claim that the actor understood a file."""
    path=args.get('path');entry=dict(path=path)
    key=json.dumps(args,sort_keys=True,separators=(',',':'))
    if key in delivered:entry['previous_delivery_sequence']=delivered[key]
    if result.get('read_rejected'):
        entry.update(read_state='rejected',read_rejected=result['read_rejected'])
    elif result.get('error') or result.get('no_execution'):
        entry.update(read_state='not_delivered',error=result.get('error'),
                     no_execution=result.get('no_execution'))
    elif result.get('path')==path and isinstance(result.get('public_text'),str):
        entry.update(read_state='delivered_text',delivered_path=path,
            content_sha256=hashlib.sha256(result['public_text'].encode()).hexdigest())
        delivered[key]=sequence
    else:
        images=[{k:image[k] for k in ('path','sha256') if k in image}
                for image in result.get('images',[]) if image.get('path')==path]
        if images:
            entry.update(read_state='delivered_image',delivered_images=images)
            delivered[key]=sequence
        else:entry['read_state']='delivery_not_established_by_public_result'
    # Geometry reads can differ by body/part even when the file path is equal.
    for name in ('body','part'):
        if name in args:entry[name]=args[name]
    return entry


def _native_step_index(args, result, known_observations):
    observation=result.get('observation',{})
    before=known_observations.get(args.get('observation_id'),{})
    ack=dict(status='public_result_without_observation',
             physical_tick_ACKs='not_exposed_by_this_public_result')
    if result.get('no_execution'):
        ack['status']='no_execution'
    elif result.get('error'):
        ack['status']='execution_not_established'
    elif observation.get('observation_id'):
        same_reset=bool(before.get('reset_id') and
                        before['reset_id']==observation.get('reset_id'))
        ack.update(status='native_tool_result_returned',same_reset=same_reset,
            before_observation_id=args.get('observation_id'),
            after_observation_id=observation['observation_id'],
            reset_id=observation.get('reset_id'))
        if not same_reset:ack['status']='observation_binding_not_established'
    for name in ('rollout_finished','closed_known','task_failure','stop_reason'):
        if name in result:ack[name]=result[name]
    entry=dict(request_id=args.get('request_id'),requested_ticks=args.get('ticks'),ack=ack)
    if result.get('error'):entry['validation_error']=result['error']
    # Preserve the original phase/hypothesis wording. It is actor intent, never
    # a success/contact assertion or an independent check of physical ticks.
    if 'reason' in args:entry['stage_claim']=dict(source='arguments.reason',original=args['reason'])
    return entry


def compact_initial(packet,pinned_files):
    packet=copy.deepcopy(packet);workspace=packet['workspace'];spec=workspace['task_specification']
    bundle=spec.get('reset_experience',{});cases=bundle.get('cases',[])
    assert sum(c.get('status')!='self_report_not_audited' for c in cases)<=3
    assert sum(c.get('status')=='self_report_not_audited' for c in cases)<=1
    active=[]
    for case in cases:
        path=case['source_path'];raw=Path(path).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if pinned_files.get(path)!=sha or case['source_sha256']!=sha:
            raise ValueError('Active experience must match its pinned full public source')
        value=json.loads(raw)
        active.append(dict(id=case['id'],path=path,sha256=sha,full_original_text=raw.decode(),
            source_scope='Historical evidence and instructions; current task/attempt contract governs.'))
        for key in list(case):
            if key!='id' and key in value and case[key]==value[key]:case.pop(key)
    packet['active_experience_full_sources']=active
    catalog=spec.get('experience_catalog',{})
    if set(catalog.get('recommended_ids',[]))=={c['id'] for c in cases}:catalog.pop('recommended_ids',None)
    if catalog.get('selection_rule')==bundle.get('selection_rule'):catalog.pop('selection_rule',None)
    for case in cases:
        source=workspace.get('skill_sources',{}).get(case['id'],{})
        for source_key,case_key in [('applicability','preconditions'),('when_not_to_use','when_not_to_use')]:
            if source.get(source_key)==case.get(case_key):source.pop(source_key,None)
    return packet


def bounded_payload(history,base,max_bytes):
    """Three physical observations + recent tools + full concise causal index.

    This bounds the input view, not inference output, stored evidence, or the
    episode. Original complete exchanges remain addressable by sequence.
    """
    from rsi.codex_app_server import _content_items
    def content(packet):
        return [dict(type='input_text',text=v['text']) if v['type']=='inputText'
                else dict(type='input_image',image_url=v['imageUrl']) for v in _content_items(packet)]
    def ref(sequence):return dict(tool='read_public_exchange',sequence=sequence)
    def calls(group):return [x for x in group if x.get('type')=='function_call']
    def packet(group):
        outputs=[x for x in group if x.get('type')=='function_call_output']
        return json.loads(outputs[-1]['output']) if outputs else {}
    current=history.current_observation;current_id=current['observation_id']
    observations={current_id:current};previous=[]
    for group in reversed(history.groups[1:]):
        obs=packet(group).get('observation',{});oid=obs.get('observation_id')
        if oid and oid not in observations:
            observations[oid]=obs;previous.append(obs)
            if len(previous)==2:break
    # Three is an upper bound. Do not add an old initialization image merely
    # to fill the window; it remains available through its original evidence.
    selected=set(range(max(1,len(history.groups)-3),len(history.groups)))
    known_observations={current_id:current}
    initial=getattr(history,'initial_observation',{})
    if initial.get('observation_id'):known_observations[initial['observation_id']]=initial
    for group in history.groups[1:]:
        obs=packet(group).get('observation',{})
        if obs.get('observation_id'):known_observations[obs['observation_id']]=obs
    notes=[];index=[];last_selection=None;delivered={};current_native_step=None
    for sequence,group in enumerate(history.groups[1:],1):
        call=calls(group);result=packet(group);entry=dict(sequence=sequence,read=ref(sequence))
        if not call:
            entry['model_turn_completed']=True;index.append(entry);continue
        call=call[0];args=json.loads(call['arguments']);entry['tool']=call['name']
        if call['name']=='experience_select':last_selection=sequence
        if call['name']=='record_public_note' and result.get('note_recorded'):notes.append(dict(sequence=sequence,note=args['note']))
        if call['name']=='read_actor_input':
            entry.update(_read_index(args,result,delivered,sequence))
        if call['name'] in ('official_mp_step','official_wbc_step'):
            entry.update(_native_step_index(args,result,known_observations))
            if entry['ack']['status']=='native_tool_result_returned':
                current_native_step=dict(sequence=sequence,request_id=entry['request_id'],
                    read=ref(sequence),stage_source='Original arguments.reason in this index; actor claim only')
        if call['name'] in ('scalebfm_act','loco_execute'):
            response=args.get('response',{});entry['request_id']=response.get('request_id')
            entry['observation_path']=result.get('observation_path')
            status=result.get('observation',{}).get('command_status',{})
            entry['ack']={k:status[k] for k in ('status','actual_error_m','actual_rotation_error_rad','reference_finished') if k in status}
            entry['outcome']=result.get('native_outcome');entry['stop_reason']=result.get('stop_reason')
            reason=response.get('reason')
            try:stage=json.loads(reason) if isinstance(reason,str) else {}
            except ValueError:stage={}
            entry['stage_claim']={k:stage[k] for k in ('verified_completed','currently_attempting','remaining','revert_to') if k in stage}
            if stage.get('evidence'):entry['evidence_excerpt']=str(stage['evidence'])[:240]
            if result.get('error'):entry['validation_error']=result['error']
        index.append(entry)
    if last_selection is not None:selected.add(last_selection)
    # Static workspace/CONTROL are supplied once. Raw repeated reads remain in
    # their stored exchange; do not append identical multi-kilobyte text again.
    static=history.static_input_paths
    def without_duplicates(value):
        if isinstance(value,list):return [without_duplicates(v) for v in value]
        if not isinstance(value,dict):return value
        if 'public_text' in value and value.get('path') in static:
            return dict(path=value['path'],already_supplied='Initial pinned workspace, CONTROL or full active experience; original read is also retained in this exchange on disk.')
        result={k:without_duplicates(v) for k,v in value.items() if k!='observation'}
        if 'observation' in value:
            obs=value['observation'];result['observation_reference']={k:obs[k] for k in ('observation_id','sim_s','reset_id') if k in obs}
            result['observation_reference']['input_location']='current/recent observation panel' if obs.get('observation_id') in observations else 'original public exchange; retrieve by sequence if needed'
        return result
    retained=[]
    for sequence in sorted(selected):
        group=history.groups[sequence];has_observation=bool(packet(group).get('observation'))
        for item in group:
            if item.get('type')=='function_call_output':item=dict(item,output=json.dumps(without_duplicates(json.loads(item['output'])),ensure_ascii=False,separators=(',',':')))
            if has_observation and isinstance(item.get('content'),list):
                parts=[v for v in item['content'] if v.get('type')!='input_image']
                item=dict(item,content=parts)
            retained.append(item)
    panel={'role':'user','content':json.dumps(dict(public_history_index=index,current_notes=notes[-3:],
        current_native_step=current_native_step,
        notice='Read delivery entries identify returned originals, not understanding. Stage entries are actor claims; requested_ticks are not executed tick ACK counts. Current and two prior distinct physical observations preserve recent correction evidence; older complete outputs/RGB/notes remain readable by exact sequence. Latest three complete tool exchanges and last source selection follow. No model output or stored evidence was truncated.'),ensure_ascii=False,separators=(',',':'))}
    past=[{'role':'user','content':content({'prior_physical_observation':True,'observation':o})} for o in reversed(previous)]
    boundary=getattr(history,'static_prefix_count',len(history.prefix))
    if type(boundary) is not int or not 0<=boundary<=len(history.prefix):
        raise ValueError('Invalid static/dynamic context boundary')
    # Preserve full original instructions/experience ahead of changing robot
    # state and history indices. The old order broke that reusable prefix.
    # No source text, recent observation, function pair or stored item is cut.
    items=(history.prefix[:boundary]+list(history.groups[0])+
           history.prefix[boundary:]+[panel]+past+retained)
    seen=set();deduped=[]
    for item in items:
        if isinstance(item.get('content'),list):
            parts=[]
            for value in item['content']:
                if value.get('type')=='input_image':
                    if value['image_url'] in seen:continue
                    seen.add(value['image_url'])
                parts.append(value)
            item=dict(item,content=parts)
        deduped.append(item)
    payload=dict(base,input=deduped)
    if len(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>max_bytes:
        raise ValueError('Required current/correction evidence exceeds request byte cap; no request sent')
    return payload
