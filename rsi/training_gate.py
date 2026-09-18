"""Fixed train/test exclusion and completed-response cancellation for six-task transfer."""
import hashlib
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
BASE=R/'artifacts/six-transfer-20260917'

def read(path):return json.loads(Path(path).read_text())

def _current_roles(plan, roles=None):
    path=plan.get('task_roles_path')
    if not path:return None
    value=read(R/Path(path)) if roles is None else roles
    if value.get('schema')!='rsi-task-family-roles-v2' or value.get('unlock')!='per_family_native_success':
        raise ValueError('Unsupported current task-family role contract')
    rows=value.get('training_tasks',[])
    if len({row['env_id'] for row in rows})!=len(rows) or len({row['label'] for row in rows})!=len(rows):
        raise ValueError('Ambiguous training family identities')
    return value


def require_training(env_id, *, plan=None, split=None, complete_attempts=0, roles=None):
    plan=read(BASE/'plan.json') if plan is None else plan
    if plan.get('new_training_launch_allowed') is not True:raise ValueError('Training admission paused by owner/user')
    current=_current_roles(plan,roles)
    if current is not None:
        row=next((r for r in current['training_tasks'] if r['env_id']==env_id),None)
        if not row or row.get('role')!='training':
            raise ValueError('Only designated core training tasks may enter the new training queue')
        if env_id not in plan.get('selected_training_env_ids',[]) or env_id not in plan.get('launch_scope',[]):
            raise ValueError('Training task is outside the current launch scope')
        # Old split/quota/historical labels cannot reverse the new user-assigned role.
        return row
    split=read(BASE/'task-split.json') if split is None else split
    if env_id in {r['env_id'] for r in split['test_tasks']}:raise ValueError('Test-only task cannot enter training')
    if env_id in {r['env_id'] for r in split['historical_success_exclusions']}:raise ValueError('Historical success is experience only')
    row=next((r for r in split['training_candidates'] if r['env_id']==env_id),None)
    if not row or not row.get('ready') or row.get('already_succeeded') is not False:raise ValueError('Verified not-yet-successful training candidate required')
    if env_id not in plan.get('launch_scope',[]):raise ValueError('Candidate not selected in current training wave')
    if complete_attempts>=plan['minimum_complete_attempts_per_selected_training_task']:raise ValueError('Training quota reached')
    return row


def _hashed(path, expected):
    path=Path(path)
    if not path.is_absolute():path=R/path
    if not isinstance(expected,str) or len(expected)!=64:
        raise ValueError('A pinned evidence hash is required')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:
            raise ValueError('Changed evidence: '+str(path))
    return path


def _evidence_object(value, label):
    if not isinstance(value,dict):raise ValueError('Expected evidence object: '+label)
    return value


def _evidence_rows(path):
    return [_evidence_object(json.loads(line),str(path))
            for line in path.read_text().splitlines() if line.strip()]


def _native_api_terminal(actor, reset, actions):
    """Validate native-api-bridge receipts, without inventing Codex turns."""
    actor=actor.resolve();api_root=actor/'api-continuation'
    def document(path):return _evidence_object(read(path),str(path))
    def reference(value, expected=None):
        value=_evidence_object(value,'API evidence reference');path=Path(value['path'])
        path=(path if path.is_absolute() else R/path).resolve()
        if not path.is_relative_to(actor) or (expected is not None and path!=expected.resolve()):
            raise ValueError('API reference belongs to another episode or receipt')
        _hashed(path,value['sha256'])
        return path,read(path)
    if list(actor.glob('turn_*.json')) or (api_root/'blocked.json').exists():
        raise ValueError('Mixed Codex/API or blocked unknown API terminal')
    terminal=document(actor/'api-terminal.json');route=document(actor/'api-route-receipt.json')
    if (terminal.get('contract')!='native-api-terminal-v1' or terminal.get('closure')!='known_closed'
            or terminal.get('reset_id')!=reset or terminal.get('actions')!=actions
            or terminal.get('finished') is not True or terminal.get('all_tool_results_acknowledged') is not True
            or route.get('account_route')!='api' or route.get('status')!='completed'
            or route.get('terminal_class')!='known_host_terminal' or route.get('same_native_reset') is not True
            or route.get('reset_id')!=reset or route.get('actions')!=actions or route.get('codex_started') is not False
            or route.get('automatic_POST_retries')!=0
            or (route.get('model'),route.get('effort'))!=('gpt-6-astra','xhigh')):
        raise ValueError('Native API route did not close on this reset')
    _,api=reference(terminal.get('original_api_terminal'),api_root/'result.json')
    api=_evidence_object(api,'original API terminal')
    _,initial=reference(api.get('initial_receipt'),actor/'api-initial-host.json')
    initial=_evidence_object(initial,'initial API host')
    if (api.get('contract')!='same-reset-api-terminal-v1' or api.get('status')!='host_finished_and_skill_recorded'
            or api.get('reset_id')!=reset or api.get('same_host') is not True or api.get('same_backend') is not True
            or api.get('host_finished') is not True or api.get('skill_updated') is not True
            or (api.get('model'),api.get('effort'))!=('gpt-6-astra','xhigh')
            or api.get('codex_thread_id') is not None or api.get('codex_turn_id') is not None
            or api.get('start_actions')!=0 or api.get('end_actions')!=actions
            or initial.get('contract')!='api-first-live-host-v1' or initial.get('reset_id')!=reset
            or initial.get('actions')!=0 or initial.get('codex_turns')!=0
            or initial.get('physical_backend_unchanged') is not True):
        raise ValueError('Native API initial/final host identity mismatch')
    calls=terminal.get('calls');tools=terminal.get('tools');exchanges=api.get('exchanges')
    if (not isinstance(calls,list) or not calls or not isinstance(tools,list) or not tools
            or not isinstance(exchanges,list) or len(exchanges)!=len(calls)
            or type(api.get('new_requests')) is not int or api['new_requests']!=len(calls)
            or route.get('api_requests')!=len(calls)):
        raise ValueError('Missing native API request/tool sequence')
    readonly={'read_actor_input','read_history_archive','read_confirmed_receipt','read_public_exchange','record_public_note'}
    native={'official_mp_step','official_mp_observe','official_mp_finish','official_wbc_step','official_wbc_observe','official_wbc_finish'}
    seen_receipts=set();seen_responses=set();seen_tool_calls=set();tool_paths=[];action_receipts=set()
    step_deltas={};position=0;previous=0
    for number,(call,exchange) in enumerate(zip(calls,exchanges),1):
        call=_evidence_object(call,'API call');exchange=_evidence_object(exchange,'API exchange')
        receipt_path,receipt=reference(call.get('request_receipt'))
        if receipt_path.name!='receipt.json' or receipt_path.parent.parent.name!='calls' or receipt_path in seen_receipts:
            raise ValueError('Duplicate or misplaced API request receipt')
        receipt=_evidence_object(receipt,'API request receipt')
        output_path,public=reference(call.get('public_output'),receipt_path.with_name('public_output.json'))
        reference(exchange.get('receipt'),receipt_path);reference(exchange.get('public_output'),output_path)
        response_id=receipt.get('response_id')
        reasoning=_evidence_object(receipt.get('returned_reasoning'),'API returned reasoning')
        if (call.get('state')!='completed' or receipt.get('state')!='completed' or receipt.get('error_type')
                or not isinstance(response_id,str) or not response_id or response_id in seen_responses
                or call.get('response_id')!=response_id or receipt.get('automatic_POST_retries')!=0
                or (receipt.get('model'),receipt.get('effort'),receipt.get('returned_model'),reasoning.get('effort'))
                    !=('gpt-6-astra','xhigh','gpt-6-astra','xhigh')
                or exchange.get('sequence')!=number or exchange.get('reset_id')!=reset
                or exchange.get('actions_before')!=previous or type(exchange.get('actions_after')) is not int
                or not previous<=exchange['actions_after']<=actions or not isinstance(public,list)):
            raise ValueError('Unknown, repeated or inconsistent API response')
        seen_receipts.add(receipt_path);seen_responses.add(response_id)
        public=[_evidence_object(x,'API public output') for x in public]
        functions=[x for x in public if x.get('type')=='function_call'];after=exchange['actions_after']
        if not functions:
            if exchange.get('tool') is not None or after!=previous:raise ValueError('Lost API function call')
            continue
        if len(functions)!=1:raise ValueError('Ambiguous API tool dispatch')
        function=functions[0];name=function.get('name');call_id=function.get('call_id')
        args=_evidence_object(json.loads(function['arguments']),'API tool arguments')
        arguments_sha=hashlib.sha256(json.dumps(args,sort_keys=True).encode()).hexdigest()
        if (not isinstance(call_id,str) or not call_id or call_id in seen_tool_calls
                or exchange.get('tool')!=name or exchange.get('call_id')!=call_id
                or exchange.get('arguments_sha256')!=arguments_sha):
            raise ValueError('API function identity/arguments changed or replayed')
        seen_tool_calls.add(call_id)
        if name in readonly:
            if after!=previous:raise ValueError('Read-only API tool advanced native actions')
        elif name in native:
            if position>=len(tools) or exchange.get('confirmed_tool') is not True:
                raise ValueError('Unconfirmed native API tool')
            tool=_evidence_object(tools[position],'native API tool');position+=1
            request_path,request=reference(tool.get('request'))
            if request_path.parent!=(actor/'agent/rpc_calls') or not request_path.name.endswith('_request.json'):
                raise ValueError('Native API RPC reference is outside its dispatcher')
            result_path=request_path.with_name(request_path.name.replace('_request.json','_result.json'))
            _,packet=reference(tool.get('result'),result_path)
            request=_evidence_object(request,'native API RPC');packet=_evidence_object(packet,'native API packet')
            if (request.get('reset_id')!=reset or request.get('tool')!=name or request.get('arguments')!=args
                    or tool.get('tool')!=name or tool.get('request_id')!=args.get('request_id')):
                raise ValueError('API response differs from native host RPC')
            # Provider call IDs and NativeHostView's local RPC IDs are different namespaces.
            key='tool:'+call_id;action_path=api_root/'actions'/(hashlib.sha256(key.encode()).hexdigest()+'.json')
            acknowledgment=document(action_path)
            fingerprint=hashlib.sha256(json.dumps(dict(name=name,arguments=args),sort_keys=True).encode()).hexdigest()
            if (acknowledgment.get('status')!='completed' or acknowledgment.get('reset_id')!=reset
                    or acknowledgment.get('request_id')!=key or acknowledgment.get('fingerprint')!=fingerprint
                    or acknowledgment.get('packet')!=packet):
                raise ValueError('Unknown or foreign API native tool acknowledgment')
            action_receipts.add(action_path);tool_paths.append(request_path)
            if name.endswith('_step'):
                command=args.get('request_id')
                if packet.get('no_execution') is True:
                    if after!=previous:raise ValueError('Rejected API tool changed native actions')
                elif not isinstance(command,str) or command in step_deltas or after<=previous:
                    raise ValueError('Repeated or unexecuted API native action')
                else:step_deltas[command]=after-previous
            elif after!=previous:raise ValueError('Non-action native API tool advanced physics')
        else:raise ValueError('Unknown API tool contract')
        previous=after
    if (position!=len(tools) or previous!=actions
            or seen_receipts!={p.resolve() for p in api_root.glob('*/calls/*/receipt.json')}
            or tool_paths!=sorted(p.resolve() for p in (actor/'agent/rpc_calls').glob('*_request.json'))
            or {p.with_name(p.name.replace('_request.json','_result.json')) for p in tool_paths}
                !={p.resolve() for p in (actor/'agent/rpc_calls').glob('*_result.json')}
            or action_receipts!={p.resolve() for p in (api_root/'actions').glob('*.json')}):
        raise ValueError('Incomplete API request/result or action receipt inventory')
    return 'complete_native_api_terminal_sequence',step_deltas


def _native_family_success(proof, training_env, expected_setting):
    """Read existing MP/WBC evidence; no new score, action, or quality gate."""
    ep=Path(proof['episode'])
    if not ep.is_absolute():ep=R/ep
    result_path=_hashed(ep/'result.json',proof['result_sha256'])
    result=_evidence_object(read(result_path),'result')
    if (result.get('task_id')!=training_env or result.get('phase')!='complete'
            or result.get('native_terminal_observed') is not True
            or result.get('native_success') is not True or result.get('engineering_reset_only') is not False
            or type(result.get('actions')) is not int or result['actions']<1
            or any(result.get(k) for k in ('error','execution_error','unknown_request','api_interrupted'))):
        raise ValueError('Not a complete original native task success')
    if (result.get('physics')!='MuJoCo' or result.get('requested_backend')!='mujoco_isaac'
            or result.get('actor_render')!='Isaac' or not result.get('live_isaac_render_calls')
            or (result.get('model'),result.get('effort'))!=('gpt-6-astra','xhigh')):
        raise ValueError('Source run differs from required native online setting')
    if proof['manifest_sha256']!=expected_setting:
        raise ValueError('Success is from a different registered training setting')
    manifest_path=_hashed(proof['manifest_path'],expected_setting)
    manifest=_evidence_object(read(manifest_path),'manifest')
    if result.get('training_manifest_sha256',result.get('frozen_manifest_sha256'))!=expected_setting:
        raise ValueError('Result is not bound to the registered setting manifest')
    if manifest.get('status') not in ('frozen_ready','training_inputs_ready','training_ready'):
        raise ValueError('Source inputs were not frozen or registered for training')
    # Preserve the exact source bytes used by a completed run after later
    # runtime releases. The original manifest/result/ACKs are never rewritten.
    harness_sources=manifest.get('harness_files')
    if 'harness_snapshot_path' in proof or 'harness_snapshot_sha256' in proof:
        archive_path=_hashed(proof['harness_snapshot_path'],proof['harness_snapshot_sha256'])
        archive=_evidence_object(read(archive_path),'harness source snapshot')
        entries=archive.get('entries')
        if (archive.get('schema')!='rsi-native-harness-snapshot-v1'
                or archive.get('manifest_sha256')!=expected_setting
                or Path(archive.get('episode','')).resolve()!=ep.resolve()
                or not isinstance(entries,list) or not isinstance(harness_sources,list)
                or len(entries)!=len(harness_sources)):
            raise ValueError('Harness snapshot differs from original episode/manifest')
        for original,snapshot in zip(harness_sources,entries):
            original=_evidence_object(original,'original harness reference')
            snapshot=_evidence_object(snapshot,'archived harness reference')
            original_path=Path(original['path'])
            if not original_path.is_absolute():original_path=R/original_path
            if (snapshot.get('original_path')!=str(original_path.resolve())
                    or snapshot.get('sha256')!=original['sha256']):
                raise ValueError('Harness snapshot does not match original source reference')
        harness_sources=entries
    for category in ('harness_files','public_inputs','saved_reset_files'):
        if not isinstance(manifest.get(category),list) or not manifest[category]:
            raise ValueError('Missing setting/input provenance: '+category)
        refs=harness_sources if category=='harness_files' else manifest[category]
        for ref in refs:
            ref=_evidence_object(ref,category);_hashed(ref['path'],ref['sha256'])
    saved=_hashed(result['saved_config_path'],result['saved_config_file_sha256'])
    if not any(Path(x['path']).resolve()==saved.resolve() and x['sha256']==result['saved_config_file_sha256']
               for x in manifest['saved_reset_files']):
        raise ValueError('Reset config is outside the frozen records')
    reset=result.get('reset_id')
    if not isinstance(reset,str) or not reset:raise ValueError('Missing reset identity')
    actor=ep/'main-actor'
    spec=_evidence_object(read(actor/'agent/task_specification.json'),'actor task specification')
    workspace=_evidence_object(read(actor/'agent/workspace.json'),'actor workspace')
    if spec.get('env_id')!=training_env or workspace.get('reset_id')!=reset:
        raise ValueError('Actual actor task/reset differs from result')
    api_deltas=None
    if (workspace.get('route')=='api' or result.get('account_route')=='api'
            or (actor/'api-terminal.json').exists() or (actor/'api-route-receipt.json').exists()):
        reason,api_deltas=_native_api_terminal(actor,reset,result['actions'])
    else:
        turn_paths=sorted(actor.glob('turn_*.json'))
        turns=[_evidence_object(read(p),'model terminal') for p in turn_paths]
        if not turns or any(_evidence_object(t.get('_rsi_terminal'),'terminal identity').get('reset_id')!=reset for t in turns):
            raise ValueError('Missing or foreign model terminal reset')
        from tools.audit_simple_campaigns import turn_completeness
        terminal=dict(result,turn_record_contract='codex-terminal-sequence-v1',codex_turns=len(turns),
                      codex_turn_ids=[t['id'] for t in turns],codex_thread_id=turns[0]['_rsi_terminal']['thread_id'])
        ok,reason=turn_completeness(actor,terminal)
        if not ok:raise ValueError('Incomplete model terminal: '+reason)
    mp=(ep/'actions.jsonl').exists();journal=ep/'actions.jsonl' if mp else actor/'native-actions.jsonl'
    if mp and (actor/'native-actions.jsonl').exists():raise ValueError('Ambiguous native backend journals')
    records=_evidence_rows(journal)
    config=_evidence_object(read(saved),'saved reset config');uid=config.get('uid')
    resets=([x for x in records if x.get('event')=='reset'] if mp else
            [x for x in _evidence_rows(ep/'reset-stabilization.jsonl') if x.get('event')=='saved_reset_ack'])
    if (not isinstance(uid,str) or not uid or len(resets)!=1 or resets[0].get('reset_id')!=reset
            or (mp and resets[0].get('task_uid')!=uid)
            or (not mp and (resets[0].get('saved_uid')!=uid or resets[0].get('actual_uid')!=uid))):
        raise ValueError('Native saved reset task/identity mismatch')
    if mp and resets[0].get('saved_config_sha256')!=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest():
        raise ValueError('Native reset config differs from frozen record')
    acks=[x for x in records if x.get('event')==('action_ack' if mp else 'ack')]
    if (len(acks)!=result['actions'] or any(x.get('reset_id')!=reset for x in acks)
            or any(x.get('terminated') or x.get('truncated') for x in acks[:-1])):
        raise ValueError('Native ACK identity/count or post-terminal action mismatch')
    final=acks[-1]
    if final.get('terminated') is not True:raise ValueError('TimeLimit alone is not native success')
    if mp:
        endings=[x for x in records if x.get('event')=='native_terminal']
        if (len(endings)!=1 or endings[0].get('request_id')!=final.get('request_id')
                or endings[0].get('reset_id')!=reset or endings[0].get('native_success') is not True
                or endings[0].get('terminated')!=final.get('terminated')
                or endings[0].get('truncated')!=final.get('truncated')):
            raise ValueError('Native terminal and final action disagree')
    motion=[];commands={};expected_tool='official_mp_step' if mp else 'official_wbc_step'
    for p in sorted((actor/'agent/rpc_calls').glob('*_request.json')):
        req=_evidence_object(read(p),'model request')
        if req.get('tool') not in ('official_mp_step','official_wbc_step'):continue
        response=_evidence_object(read(p.with_name(p.name.replace('_request.json','_result.json'))),'tool response')
        # An explicitly rejected, unexecuted tool call has no native intent/ACK.
        if response.get('no_execution') is True:continue
        if req['tool']!=expected_tool:raise ValueError('Model tool differs from native backend')
        args=_evidence_object(req.get('arguments'),'action arguments');command=args.get('request_id')
        observation=args.get('observation_id');ticks=args.get('ticks')
        if (not isinstance(command,str) or not command or command in commands
                or not isinstance(observation,str) or not observation.startswith(reset+':')
                or type(ticks) is not int or ticks<1):
            raise ValueError('Action request identity/tick mismatch')
        public=_evidence_object(response.get('observation'),'tool observation')
        if public.get('reset_id')!=reset or type(response.get('rollout_finished')) is not bool:
            raise ValueError('Incomplete or foreign action tool response')
        commands[command]=(p,req,response);motion.append(command)
    if not motion:raise ValueError('Missing model-dispatched native action')

    # Replay only journal structure, never actions: one intent per native tick
    # in MP, one intent per chunk in WBC, with contiguous unique acknowledgments.
    groups=[];current=None;pending=None;terminal_seen=False
    chunk_event='actor_chunk_intent' if mp else 'intent'
    ack_event='action_ack' if mp else 'ack'
    for row in records:
        event=row.get('event')
        if event=='reset' and mp:
            if groups or pending:raise ValueError('Reset after native action')
            continue
        if event=='native_terminal' and mp:
            if not terminal_seen or pending:raise ValueError('Unbound native terminal event')
            continue
        if event not in (chunk_event,ack_event) and not (mp and event=='action_intent'):
            raise ValueError('Unexpected native journal event')
        if terminal_seen:raise ValueError('Action intent or ACK after native terminal')
        if row.get('reset_id')!=reset:raise ValueError('Native intent/ACK reset mismatch')
        if event==chunk_event:
            if pending or (current is not None and len(current['acks'])!=current['ticks']):
                raise ValueError('Unacknowledged previous native chunk')
            command=row.get('request_id')
            if not isinstance(command,str) or command not in commands or command in [g['id'] for g in groups]:
                raise ValueError('Unknown or duplicate native chunk intent')
            args=commands[command][1]['arguments']
            if _evidence_object(row.get('arguments'),'chunk intent arguments')!=args:
                raise ValueError('Native chunk differs from model request')
            current={'id':command,'ticks':args['ticks'],'acks':[]};groups.append(current)
            continue
        if current is None:raise ValueError('Native tick without chunk intent')
        index=len(current['acks']);native_id=current['id']+':'+str(index) if mp else current['id']
        if row.get('request_id')!=native_id or index>=current['ticks']:
            raise ValueError('Duplicate, missing or out-of-order native tick')
        if event=='action_intent':
            if pending is not None:raise ValueError('Unacknowledged native tick intent')
            pending=native_id;continue
        if (mp and pending!=native_id) or (not mp and (type(row.get('tick')) is not int or row['tick']!=index+1)):
            raise ValueError('Native ACK lacks its exact sequential intent/tick')
        if type(row.get('terminated')) is not bool or type(row.get('truncated')) is not bool:
            raise ValueError('Malformed native terminal flags')
        pending=None;current['acks'].append(row)
        terminal_seen=row['terminated'] or row['truncated']
    if pending or not terminal_seen or [g['id'] for g in groups]!=motion:
        raise ValueError('Unacknowledged or unmatched model/native action intent')
    if api_deltas is not None and api_deltas!={g['id']:len(g['acks']) for g in groups}:
        raise ValueError('API exchange action count differs from native ACK ticks')
    for group in groups:
        response=commands[group['id']][2]
        if response['rollout_finished']!=(group is groups[-1]):
            raise ValueError('Model tool terminal differs from native chunk')
    command=motion[-1];request_path,request,response=commands[command]
    args=request['arguments']
    native_command=final.get('request_id')
    if (mp and not str(native_command).startswith(command+':')) or (not mp and native_command!=command):
        raise ValueError('Final native ACK belongs to a different model action')
    if response.get('rollout_finished') is not True or response.get('observation',{}).get('reset_id')!=reset:
        raise ValueError('Final tool response not complete on this reset')
    frame=_evidence_object(final.get('binding'),'final frame binding').get('head_stereo_left_sha256') if mp else final.get('frame_sha256')
    images=response['observation'].get('images',[])
    if not isinstance(images,list):raise ValueError('Malformed actor images')
    images=[_evidence_object(image,'actor image') for image in images]
    if (not isinstance(frame,str) or len(frame)!=64 or not any(
            image.get('camera')=='head_stereo_left' and image.get('renderer')=='Isaac' and image.get('sha256')==frame
            for image in images)):
        raise ValueError('Final online actor frame is not bound to the native ACK')
    if response['observation'].get('observation_id')!=f'{reset}:{result["actions"]}:{frame[:16]}':
        raise ValueError('Final observation identity differs from the native action/frame')
    # Video encoding is presentation/diagnostic, never an extra success veto.
    return dict(episode=str(ep),reset_id=reset,native_success=True,actions=result['actions'],
                result_sha256=proof['result_sha256'],training_setting_sha256=expected_setting,
                final_command_id=native_command,model_terminal=reason,
                source_role=result.get('role','historical_frozen_evaluation'),history_relabelled=False)


def require_related_test(env_id, *, training_setting_sha256, plan=None, roles=None):
    """Unlock only the named family from original same-setting native evidence.

    training_setting_sha256 is the manager's pre-registered core-task manifest,
    not the different task's test-manifest hash or a boolean 'same_setting'.
    unlock_evidence rows: episode, result_sha256, manifest_path, manifest_sha256.
    Each target still uses its own native setting; disclosed Sonic/AMO transfer
    does not require different tasks' manifests to be identical.
    """
    plan=read(BASE/'plan.json') if plan is None else plan
    if plan.get('test_launch_allowed') is False:
        raise ValueError('Tests paused by user pending training capability review')
    current=_current_roles(plan,roles)
    if current is None:raise ValueError('Related tests require the current family-role contract')
    targets=[x for x in current.get('test_candidates',[]) if x['env_id']==env_id]
    if len(targets)!=1 or targets[0].get('role')!='related_test':raise ValueError('Task is not a selected related test')
    target=targets[0]
    families=[x for x in current['training_tasks'] if x['env_id']==target.get('training_env_id') and x['label']==target.get('family')]
    if len(families)!=1 or families[0].get('role')!='training':raise ValueError('Related-test family binding is ambiguous')
    if families[0].get('minimum_native_successes_to_unlock')!=1:
        raise ValueError('Current contract unlocks on one native success; no extra success quota')
    errors=[]
    for proof in families[0].get('unlock_evidence',[]):
        try:verified=_native_family_success(proof,families[0]['env_id'],training_setting_sha256)
        except (ValueError,KeyError,TypeError,OSError) as error:
            errors.append(str(error));continue
        return dict(target,admission='unlocked_by_family_native_success',evidence=verified)
    raise ValueError('Family lacks verified native success in the registered setting: '+'; '.join(errors[:3]))

class UserBoundaryStop(RuntimeError):pass

def check_stop(host, output, *, plan_path=BASE/'plan.json'):
    """Call before POST and after complete model response, before tool dispatch."""
    episode=Path(output).parent
    plan=read(plan_path)
    if not ((episode/'stop-request.json').exists() or (BASE/'STOP.json').exists()
            or plan.get('new_training_launch_allowed') is not True):return
    if getattr(host.backend,'active',None):raise RuntimeError('Cancellation cannot interrupt an active physics command')
    host.stop_reason='user_stop_at_completed_boundary';host.finished=True
    receipt={'reason':host.stop_reason,'new_request_sent':False,'next_model_action_executed':False,
             'actions':host.actions,'inference_interrupted':False}
    (episode/'user_stop.json').write_text(json.dumps(receipt,indent=2))
    raise UserBoundaryStop('User stopped this episode after completed inference/tool boundary')


def reviewed_attempt(episode, classified):
    """A configured native event alone is not complete valuable training credit."""
    # New user-selected native-terminal mode keeps the existing reset, final
    # model/tool ACK and sealed-video checks in classify(). Extra grasp/hold
    # quality review is diagnostic and cannot veto its native success.
    result_path=Path(episode)/'result.json'
    result=read(result_path) if result_path.exists() else {}
    native=result.get('native_terminal_contract')
    if native and classified.get('reset_id'):
        from rsi.native_training import contract
        event=result.get('native_terminal_event') or {}
        episode=Path(episode)
        reset=read(episode/'reset-receipt.json')
        registration=read(episode/'protocol-registration.json')
        executions=sorted((episode/'rollout/episode').glob('execution*.json'))
        execution=read(executions[-1]) if executions else {}
        final=execution.get('final_status',{})
        command=event.get('command_id') if classified.get('success') else final.get('command_id')
        request=execution.get('response',{}).get('request_id')
        physical_ack=(isinstance(command,str) and isinstance(request,str)
            and command.startswith(request+':') and final.get('command_id')==command
            and final.get('status') in ('cancelled_after_native_success','target_reached',
                'gripper_duration_elapsed','timed_out','ik_blocked','cancelled','aborted')
            and any(r.get('command_id')==command and r.get('status')==final['status']
                    for r in execution.get('receipts',[])))
        terminals=[read(p) for p in episode.glob('turn_*.json')]
        terminal_reset_ok=all((r.get('_rsi_terminal') or {}).get('reset_id')==reset.get('reset_id')
            for r in terminals)
        api=result.get('api_continuation')
        if api:terminal_reset_ok=terminal_reset_ok and api.get('reset_id')==reset.get('reset_id')
        identities=(native==contract(native.get('env_id'))
                and native.get('env_id')==reset.get('env_id')==registration.get('task_id')
                and physical_ack and terminal_reset_ok and result.get('skill_updated') is True)
        if (identities and classified.get('complete') and classified.get('success')
                and final.get('status')=='cancelled_after_native_success' and event.get('original_native_success') is True
                and event.get('reset_id')==classified.get('reset_id')
                and event.get('remaining_reference_cancelled') is True):
            return dict(classified, complete=True, state='native_complete',
                reason='Native terminal and existing reset/ACK/video checks passed; stricter diagnostics do not veto',
                native_success=True, audited_success=False, diagnostic_review_pending=True)
        if identities and not classified.get('success') and not result.get('error'):
            reason=result.get('stop_reason')
            physical_failure=(reason in ('native_failure','task_failure')
                and result.get('backend_stop_reason')=='diagnostic_stability_stop')
            evidence_failure=False
            stall=episode/'rollout/policy_stall.jsonl'
            if reason in ('actor_learning_deferral','progress_actor_stall') and stall.exists():
                rows=[json.loads(line) for line in stall.read_text().splitlines()]
                last=rows[-1] if rows else {};paths=[Path(p) for p in last.get('evidence_paths',[])]
                evidence_failure=(bool(last.get('reason')) and bool(last.get('next_hypothesis')) and bool(paths)
                    and all(p.is_file() and episode.resolve() in p.resolve().parents for p in paths))
            if physical_failure or evidence_failure:
                return dict(classified,complete=True,state='native_attempt_complete',success=False,
                    native_success=False,configured_success=False,audited_success=False,
                    reason='Completed native-mode unsuccessful attempt with evidence; quality review asynchronous',
                    diagnostic_review_pending=True)
        return dict(classified,complete=False,state='pending_native_identity_evidence',
            reason='Native event, task, reset and final action/model ACK must match; no extra task-quality gate')
    if classified.get('curriculum_complete'):
        episode=Path(episode);path=episode/'curriculum-review.json'
        row=read(path) if path.exists() else {}
        files=row.get('evidence_paths',[])
        valid=(row.get('reset_id')==classified.get('reset_id')
            and row.get('curriculum_level')==classified.get('curriculum_level')
            and row.get('curriculum_spec_sha256')==classified.get('curriculum_spec_sha256')
            and row.get('complete_valuable_attempt') is True
            and type(row.get('audited_curriculum_success')) is bool
            and (row['audited_curriculum_success'] is False or classified.get('curriculum_success') is True)
            and bool(row.get('reviewer')) and bool(row.get('reason')) and bool(files)
            and all(Path(p).is_file() and episode.resolve() in Path(p).resolve().parents for p in files))
        return dict(classified,reviewed_curriculum_attempt=bool(valid),audited_curriculum_success=bool(valid and row['audited_curriculum_success']),
            state='curriculum_complete' if valid else 'pending_curriculum_review',
            review=str(path) if valid else None)
    if not classified.get('complete'):return classified
    episode=Path(episode);path=episode/'training-attempt-review.json'
    row=read(path) if path.exists() else {}
    files=row.get('evidence_paths',[])
    valid=(row.get('reset_id')==classified.get('reset_id') and row.get('complete_valuable_attempt') is True
           and bool(row.get('reviewer')) and bool(row.get('reason')) and bool(files)
           and all(Path(p).is_file() and episode.resolve() in Path(p).resolve().parents for p in files))
    if not valid:return dict(classified,complete=False,state='pending_training_review',reason='Configured terminal recorded; complete valuable attempt and grasp/hold success require review')
    return dict(classified,audited_success=row.get('audited_task_success') is True,review=str(path))
