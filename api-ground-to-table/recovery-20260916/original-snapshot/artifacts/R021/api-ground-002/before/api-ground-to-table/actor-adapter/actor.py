"""Pinned Responses actor. Importing this module is offline and credential-free."""
import argparse
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RSI = ROOT.parents[1]
SOURCE = RSI/'codex-account-2/workspace/ground-to-table'
FROZEN = SOURCE/'provenance/episodes/episode-0007'
PROVIDER = 'https://llm-gateway.galbot.com'
MODEL, EFFORT, MAX_CALLS, MAX_TOKENS, MAX_BODY = 'gpt-6-astra', 'xhigh', 6, 16384, 2_000_000
DECISION_KEYS = ('observations','hypothesis','evidence','uncertainty','expected','next_test')
INSTRUCTIONS = ('Use only public RGB, named robot state and tools. Give concise public evidence '
    'summaries, not private reasoning. Never replay old world targets blindly. Reobserve after '
    'motion. No human questions: first collect three comparable autonomous physical failures '
    'and diagnose them. Keep skill changes local. Only public native outcome confirms success; '
    'never request host audit. Safe useful tests should continue; approaching a target is not failure.')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def save(path, value):
    Path(path).write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode())


def validate_endpoint(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.hostname != 'llm-gateway.galbot.com'
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path.rstrip('/') not in ('', '/v1')):
        raise ValueError('Provider must be pinned Galbot HTTPS /v1 endpoint')
    return '/v1/responses'


def public_response(response):
    """Do not persist reasoning items, summaries, encrypted reasoning, or raw events."""
    result = []
    for item in response.get('output', []):
        if item.get('type') == 'function_call':
            result.append({k:item[k] for k in ('type','name','call_id','arguments') if k in item})
        elif item.get('type') == 'message':
            result.append({'type':'message','text':'\n'.join(
                c['text'] for c in item.get('content',[]) if c.get('type')=='output_text')})
    return result


class HTTPSResponses:
    def __call__(self, payload):
        # Only reached after the shared budget reservation. Never copied into context/logs.
        config = json.loads((RSI/'api.json').read_text())
        endpoint = validate_endpoint(config['BASE_URL'])
        key = config['API_KEY']
        if not isinstance(key, str) or not key.strip(): raise ValueError('Missing API credential')
        conn = http.client.HTTPSConnection('llm-gateway.galbot.com', timeout=None)
        try:
            conn.request('POST', endpoint, body=encoded(payload), headers={
                'Authorization':'Bearer '+key, 'Content-Type':'application/json'})
            stream = conn.getresponse()
            if stream.status != 200:
                raise RuntimeError('HTTP '+str(stream.status)+'; no retry; expense unknown')
            terminal = None
            # Streaming keeps the connection active; no inference or chunk deadline.
            for line in stream:
                if not line.startswith(b'data:'): continue
                data = line[5:].strip()
                if data == b'[DONE]': continue
                event = json.loads(data)
                if event.get('type') in ('response.completed','response.failed','response.incomplete'):
                    terminal = event['response']
            if terminal is None: raise RuntimeError('Missing terminal response; no retry')
            terminal['_transport'] = {'http_status':stream.status,
                'provider_request_id':stream.getheader('x-request-id')}
            return terminal
        finally:
            conn.close()


class ResponsesSession:
    def __init__(self, output, budget, send, run_id):
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=False)
        self.budget, self.send, self.run_id = budget, send, run_id
        self.count, self.stopped = 0, False

    def call(self, payload):
        if self.stopped or self.count >= MAX_CALLS: raise ValueError('Batch stopped; no continuation')
        if (payload.get('model') != MODEL or payload.get('reasoning') != {'effort':EFFORT}
                or payload.get('store') is not False or payload.get('stream') is not True
                or type(payload.get('max_output_tokens')) is not int
                or not 1 <= payload['max_output_tokens'] <= MAX_TOKENS):
            raise ValueError('Require Astra/xhigh, store:false, stream:true, bounded output')
        body = encoded(payload)
        if len(body) > MAX_BODY: raise ValueError('Request exceeds 2 MB; no paid request sent')
        meta = dict(run_id=self.run_id,call_index=self.count+1,model=MODEL,effort=EFFORT,
            provider=PROVIDER,max_output_tokens=payload['max_output_tokens'],input_bytes=len(body),
            request_sha256=hashlib.sha256(body).hexdigest())
        receipt = dict(meta, started_at_unix=time.time(),state='reserved',cost_cny=None,
                       private_reasoning_exported=False)
        reservation = self.budget.reserve(meta)  # Must complete before any credentials/network use.
        self.count += 1
        folder = self.output/f'{self.count:02d}'; folder.mkdir(exist_ok=False)
        save(folder/'receipt.json',receipt)
        try:
            response = self.send(payload)
            receipt.update(response_id=response.get('id'),usage=response.get('usage'),
                returned_model=response.get('model'),returned_reasoning=response.get('reasoning'),
                state=response.get('status','unknown'),transport=response.get('_transport',{}))
            receipt.update(response.get('_transport',{}))
            save(folder/'public_output.json',public_response(response))
            if (response.get('status') != 'completed' or response.get('model') != MODEL
                    or response.get('reasoning',{}).get('effort') != EFFORT):
                raise RuntimeError('Incomplete response or model/effort mismatch; no retry')
            return response
        except BaseException as error:
            self.stopped = True
            if receipt['state'] == 'reserved': receipt['state'] = 'unknown_no_retry'
            receipt['error_type'] = type(error).__name__  # Never echo raw provider/credential errors.
            raise
        finally:
            receipt['finished_at_unix'] = time.time()
            receipt.update(started_at=receipt['started_at_unix'],finished_at=receipt['finished_at_unix'],
                           reasoning_effort=EFFORT)
            save(folder/'receipt.json',receipt)
            try:
                self.budget.settle(reservation,receipt)
            except BaseException:
                self.stopped = True
                raise


class Gate:
    """Public tool boundary; paths and observations are selected by the host."""
    def __init__(self, host):
        self.host, self.root = host, host.rollout_root.resolve()
        self.issued, self.serial, self.concluded = set(), 0, False
        self.schemas = {}
        for tool in host.tool_specs():
            if tool['name'] not in ('scalebfm_act','four_point_translate','four_point_rotate',
                    'image_pixel_to_world_plane','four_point_place_local_point','experience_read'): continue
            schema = copy.deepcopy(tool['inputSchema'])
            for key in ('output_dir','observation_path'):
                schema['properties'].pop(key,None)
                if key in schema.get('required',[]): schema['required'].remove(key)
            self.schemas[tool['name']] = (schema,tool['description'])
        strings = lambda names: {'type':'object','additionalProperties':False,
            'properties':{k:{'type':'string'} for k in names},'required':list(names)}
        self.schemas['read_public_evidence'] = (strings(('path',)),
            'Read an exact previously issued public JSON/JSONL/PNG evidence path; no arbitrary filesystem access. Large motion JSON returns 20 labeled samples.')
        self.schemas['conclude'] = (strings(('reason','next_hypothesis','revised_skill','lesson')),
            'Record public self-diagnosis. Safe in_progress stalls keep this episode open: test next_hypothesis using returned observation/next_call. Only native termination, safety/system fault or physical budget allows conclusion and a local skill revision.')
        for schema,_ in self.schemas.values():
            schema['properties']['public_decision'] = strings(DECISION_KEYS)
            schema.setdefault('required',[]).append('public_decision')

    def specs(self):
        return [dict(type='function',name=name,description=description,parameters=schema,strict=False)
                for name,(schema,description) in self.schemas.items()]

    def register(self, value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in ('path','observation_path','proprioception_path') and isinstance(item,str):
                    path = Path(item).resolve()
                    if not path.is_relative_to(self.root): raise ValueError('Public path escaped rollout')
                    if path.is_file(): self.issued.add(path)
                elif key not in ('next_call',): self.register(item)
        elif isinstance(value,list):
            for item in value: self.register(item)

    def read_public(self, value):
        path = Path(value).resolve()
        if path not in self.issued or not path.is_relative_to(self.root) or path.suffix not in ('.json','.jsonl','.png'):
            raise ValueError('Only issued public evidence is readable')
        if path.suffix == '.png': return {'images':[{'path':str(path)}]}
        if path.stat().st_size > 20_000_000: raise ValueError('Evidence exceeds bounded read size')
        text = path.read_text()
        result = json.loads(text) if path.suffix=='.json' else [json.loads(s) for s in text.splitlines()[-60:]]
        if isinstance(result,dict) and 'samples' in result and len(result['samples'])>20:
            count = len(result['samples'])
            indices = sorted({round(i*(count-1)/19) for i in range(20)})
            result.update(samples=[result['samples'][i] for i in indices],
                total_samples=count,returned_sample_indices=indices,
                sampling_notice='20 evenly spaced samples; full 50Hz trace stays at the issued path.')
        if len(encoded(result))>200_000: raise ValueError('Public evidence result exceeds 200 KB')
        return result

    def content(self, packet):
        if not isinstance(packet,dict): packet = {'public_evidence':packet}
        packet = copy.deepcopy(packet); packet.pop('next_call',None)
        self.register(packet)
        items = [{'type':'input_text','text':json.dumps(packet,ensure_ascii=False,allow_nan=False)}]
        for descriptor in packet.get('images',packet.get('observation',{}).get('images',[])):
            path = Path(descriptor['path']).resolve()
            if path not in self.issued or path.suffix!='.png': raise ValueError('Unissued public image')
            items.append({'type':'input_image','image_url':
                'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()})
        return items

    def dispatch(self, name, arguments):
        if name not in self.schemas or self.concluded: raise ValueError('Tool unavailable')
        encoded(arguments)  # Reject NaN/Infinity before the host sees an action.
        schema = self.schemas[name][0]
        if (not isinstance(arguments,dict) or set(arguments)-set(schema['properties'])
                or not set(schema['required']) <= set(arguments)):
            raise ValueError('Invalid public tool arguments')
        args = dict(arguments); summary = args.pop('public_decision')
        if (not isinstance(summary,dict) or set(summary)!=set(DECISION_KEYS)
                or any(not isinstance(v,str) or not v.strip() or len(v)>2000 for v in summary.values())):
            raise ValueError('Concise public evidence summary required')
        self.serial += 1
        record = dict(tool=name,arguments=args,public_decision=summary)
        save(self.root/f'public_decision_{self.serial:04d}.json',record)
        if name == 'read_public_evidence': return self.read_public(args['path'])
        if name == 'conclude':
            if any(not isinstance(v,str) for v in args.values()) or not args['reason'].strip() or not args['next_hypothesis'].strip():
                raise ValueError('A reason and changed hypothesis are required')
            if self.host.backend.active: raise ValueError('Cannot conclude during an unfinished physical action')
            native = self.host.harness.evaluator.outcome(self.host.backend)
            terminal = (native in ('success','failure') or self.host.backend.reason
                or self.host.runtime_error or self.host.initialization_error
                or self.host.stop_reason == 'episode_step_budget')
            if not terminal:
                packet = dict(concluded=False,rollout_finished=False,native_outcome=native,
                    stop_reason=self.host.stop_reason,reason=args['reason'],
                    next_hypothesis=args['next_hypothesis'],actions_so_far=self.host.actions,
                    observation_path=str(self.host.harness.latest_path),next_call=self.host.next_call(),
                    skill_update_deferred=bool(args['revised_skill']),
                    continuation='Stall recorded. Test next_hypothesis in this episode; no unchanged retry or idle hold. Skill revision requires a real terminal condition.')
                self.register(packet)
                packet['observation'] = self.read_public(packet['observation_path'])
                with (self.root/'policy_stall.jsonl').open('a') as stream:
                    stream.write(json.dumps(packet,ensure_ascii=False)+'\n')
                return packet
            self.host.finished = True
            self.host.stop_reason = self.host.stop_reason or (
                'native_'+native if native in ('success','failure') else
                self.host.backend.reason or 'control_transaction_error')
            evidence = self.root/f'public_decision_{self.serial:04d}.json'
            if args['revised_skill']:
                revised = args['revised_skill']+'\n'+INSTRUCTIONS
                if len(revised)>6250 or len(revised.split())>831:
                    raise ValueError('Revised skill plus runtime exceeds global cap')
                self.host.dispatch('skill_update',dict(markdown=args['revised_skill'],lesson=args['lesson'],
                    evidence_paths=[str(evidence)],transfer_scope='task_specific',change_summary=args['next_hypothesis']))
            self.concluded = True
            return dict(concluded=True,rollout_finished=True,native_outcome=native,
                stop_reason=self.host.stop_reason,self_diagnosis=args['reason'],
                next_hypothesis=args['next_hypothesis'])
        if name != 'experience_read':
            args.update(observation_path=str(self.host.harness.latest_path),
                        output_dir=str(self.root/f'api_action_{self.serial:04d}'))
        packet = self.host.dispatch(name,args)
        self.register(packet)
        return packet


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name,Path(path).resolve())
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def bound_image_history(history):
    """Retain the latest two image-bearing observations; keep all public action text."""
    visual = [item for item in history if isinstance(item.get('content'),list)
              and any(c.get('type')=='input_image' for c in item['content'])]
    for item in visual[:-2]:
        item['content'] = [c for c in item['content'] if c.get('type')!='input_image']
        item['content'].append({'type':'input_text',
            'text':'Earlier RGB omitted from this request to bound payload; original images remain in public evidence.'})


def terminal_kind(native, reason, infrastructure_error, diagnosed, calls, *, stop_reason=None):
    if native == 'success': return 'host_audited_success'
    if reason == 'diagnostic_stability_stop': return 'safety_stop'
    if infrastructure_error: return 'infrastructure_error'
    if native == 'failure': return 'physical_failure'
    if stop_reason == 'episode_step_budget': return 'budget_limited_incomplete'
    if diagnosed: return 'agent_stopped_incomplete'
    if calls == MAX_CALLS: return 'budget_limited_incomplete'
    return 'adapter_stopped_incomplete'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='api-ground-001',choices=['api-ground-001'])
    parser.add_argument('--episode',required=True)
    parser.add_argument('--authorization',type=Path,required=True)
    parser.add_argument('--budget-hook',type=Path,default=ROOT.parent/'empirical_hook.py')
    parser.add_argument('--backend',type=Path,default=ROOT.parent/'original_backend.py')
    args = parser.parse_args()
    if not args.episode or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.episode):
        raise ValueError('Episode must be a simple lowercase identifier')
    auth = json.loads(args.authorization.read_text())
    expected = dict(run_id=args.run_id,provider=PROVIDER,model=MODEL,effort=EFFORT,
                    new_simulation_images_approved=True,max_calls=MAX_CALLS)
    if any(auth.get(k)!=v for k,v in expected.items()): raise ValueError('Explicit new-image authorization is missing')
    os.environ.setdefault('MUJOCO_GL','egl')
    for key in ('XDG_CACHE_HOME','MPLCONFIGDIR','TORCH_HOME','CUDA_CACHE_PATH',
                '__GL_SHADER_DISK_CACHE_PATH','MESA_SHADER_CACHE_DIR'):
        os.environ[key] = str(ROOT/'cache'/key.lower())
        Path(os.environ[key]).mkdir(parents=True,exist_ok=True)
    os.environ['TMPDIR'] = str(ROOT/'tmp'); Path(os.environ['TMPDIR']).mkdir(exist_ok=True)
    sys.path[:0] = [str(FROZEN),str(SOURCE),'/home/galbot/lizekai/Loco_manip/locomanip/src']
    from rsi.episode_video import EpisodeVideo
    from rsi.skill_learning import SkillMemory
    from tools.learn_grasp_skill import LearningHost, finger_geometry
    from ground_task import GroundEvaluator
    backend_module = load_module(args.backend,'authorized_backend')
    budget = load_module(args.budget_hook,'authorized_budget')
    campaign = ROOT/'campaign'; campaign.mkdir(exist_ok=True)
    import fcntl
    lock = (campaign/'writer.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output = campaign/args.episode; output.mkdir(exist_ok=False)
    updates = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        RSI/'ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md',RSI/'ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md')}
    skill = campaign/'SKILL.md'
    if not skill.exists(): skill.write_bytes((ROOT/'loco-manip-direct/SKILL.md').read_bytes())
    memory = SkillMemory(campaign/'memory',skill)
    instructions = skill.read_text()+'\n'+INSTRUCTIONS
    if len(instructions)>6250 or len(instructions.split())>831: raise ValueError('Main skill/harness size cap exceeded')
    task = json.loads((FROZEN/'task_specification.json').read_text())
    task['initial_semantics'] = 'Original table restored. Cube starts on the floor; determine geometry from current calibrated RGB.'
    task['human_feedback'] = 'First move into a range where grasping is possible without further walking, then bend. This is human-proposed planning feedback, not a demonstrated trajectory or verified physical skill.'
    host = LearningHost(output,memory,args.episode,0,task=task['goal'],
        backend_factory=backend_module.create_backend,evaluator_factory=lambda:GroundEvaluator(output/'host_audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='Astra/xhigh API | human planning feedback'),
        support_plane_z_m=None,geometry_provider=finger_geometry,max_episode_steps=9000)
    result = dict(episode_id=args.episode,run_id=args.run_id,backend='MuJoCo',
        human_feedback_used=True,human_demonstration_used=False,independent_physical_reset=False,
        simulation_pauses_during_planning=True,learning_not_frozen_eval=True,overall_success=False,
        user_update_hashes=updates,human_question_eligible=False)
    save(output/'provenance.json',dict(result,source=str(FROZEN),backend_path=str(args.backend),
        backend_sha256=hashlib.sha256(args.backend.read_bytes()).hexdigest(),
        actor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    (output/'SKILL.md').write_text(skill.read_text())
    session = None
    try:
        packet = host.dispatch('loco_start',{'task':host.task,'output_dir':str(host.rollout_root/'episode')})
        if host.initialization_error: raise RuntimeError('Backend initialization failed; no API request')
        save(output/'reset_provenance.json',host.backend.reset_provenance)
        result['independent_physical_reset'] = True
        gate = Gate(host)
        experience = memory.read(); experience.pop('skill',None)
        history = [{'role':'developer','content':instructions},
            {'role':'user','content':[{'type':'input_text','text':json.dumps(dict(task=task,
                self_experience=experience,calls_available=MAX_CALLS))}]+gate.content(packet)}]
        session = ResponsesSession(output/'api_calls',budget,HTTPSResponses(),args.run_id)
        while session.count < MAX_CALLS and not gate.concluded:
            bound_image_history(history)
            choice = ({'type':'function','name':'scalebfm_act'} if session.count==0 else
                {'type':'function','name':'conclude'} if host.finished else 'required')
            payload = dict(model=MODEL,reasoning={'effort':EFFORT},store=False,stream=True,
                max_output_tokens=MAX_TOKENS,parallel_tool_calls=False,tool_choice=choice,
                tools=gate.specs(),include=['reasoning.encrypted_content'],input=history)
            response = session.call(payload)
            calls = [item for item in response.get('output',[]) if item.get('type')=='function_call']
            if len(calls)!=1: raise ValueError('Exactly one actor tool call required; no retry')
            call = calls[0]
            if session.count==1 and call['name']!='scalebfm_act': raise ValueError('First compatible API call must choose an action')
            packet = gate.dispatch(call['name'],json.loads(call['arguments']))
            if isinstance(packet,dict):
                if 'next_call' in packet:
                    packet['next_call'] = {'tool':'conclude' if host.finished else 'scalebfm_act'}
                packet['api_calls_remaining'] = MAX_CALLS-session.count
            # Private reasoning is carried in memory for stateless continuity, never written/exported.
            history.extend(response['output'])
            history.append({'type':'function_call_output','call_id':call['call_id'],'output':json.dumps(packet)})
            images = gate.content(packet)[1:]
            if images:
                history.append({'role':'user','content':[
                    {'type':'input_text','text':'Public RGB associated with the preceding tool result.'}]+images})
        result.update(stop_reason=host.stop_reason or 'api_batch_call_limit',
            self_diagnosis_complete=gate.concluded,skill_updated=host.skill_updated,
            review_pending=not gate.concluded)
    except BaseException as error:
        result.update(stop_reason='stopped_no_retry',error_type=type(error).__name__,review_pending=True)
        raise
    finally:
        try:
            host.close()
        finally:
            if host.harness:
                native = host.harness.evaluator.outcome(host.backend)
                audit = host.harness.evaluator.audit
                if audit:
                    result['overall_success'] = audit.result()['overall_success']
                host.harness.evaluator.close()
            else:
                native = 'not_started'
            count = session.count if session else 0
            reason = getattr(host.backend,'reason',None)
            kind = terminal_kind(native,reason,bool(result.get('error_type') or host.runtime_error
                or host.initialization_error),result.get('self_diagnosis_complete'),count,
                stop_reason=host.stop_reason)
            result.update(actions=host.actions,api_calls=count,
                video=str(output/'video/episode.mp4'),native_outcome=native,
                backend_stop_reason=reason,physical_failure=kind=='physical_failure',
                terminal_kind=kind,episode_terminal_kind=kind)
            if host.backend:
                result['stability_public_status'] = {k:v for k,v in host.backend.status().items()
                    if not k.startswith('_')}
            save(output/'result.json',result)
            print(json.dumps(result),flush=True)


if __name__ == '__main__': main()
