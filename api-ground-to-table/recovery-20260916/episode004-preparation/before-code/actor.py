"""Pinned Responses actor. Importing this module is offline and credential-free."""
import argparse
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from history_bound import PublicHistory

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
    path=Path(path)
    temporary=path.with_name(path.name+'.atomic-tmp')
    with temporary.open('wb') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode())
        stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def continue_completed_turn(response, history, gate, evidence_ref):
    if response.get('status')!='completed':raise ValueError('Only completed turns may continue')
    if any(x.get('type')=='function_call' for x in response.get('output',[])):return False
    host=gate.host
    if host.finished or host.backend.active:raise ValueError('Cannot continue terminal or active physics')
    path=Path(host.harness.latest_path)
    packet={'observation_path':str(path),'observation':json.loads(path.read_text()),
        'rollout_finished':False,'native_outcome':'in_progress','no_physical_action_this_turn':True,
        'next_call':{'tool':'scalebfm_act'},
        'continuation_note':'The preceding model turn completed without a tool. The same reset/robot observation remains current; no action occurred. Replan a useful safe test, then call a tool. Repeated text is not progress.'}
    history.append_completed_turn(response['output'],gate.content(packet),evidence_ref)
    return True


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
    def __init__(self, output, budget, send, run_id, *, max_calls=MAX_CALLS):
        if type(max_calls) is not int or max_calls not in (6, 120):
            raise ValueError('Unregistered call allowance')
        if max_calls == 120 and run_id not in ('api-ground-002','api-ground-003'):
            raise ValueError('120 calls require an explicitly registered run')
        self.max_calls = max_calls
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=False)
        self.budget, self.send, self.run_id = budget, send, run_id
        self.count, self.stopped = 0, False

    def call(self, payload):
        if self.stopped or self.count >= self.max_calls: raise ValueError('Batch stopped; no continuation')
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
    def __init__(self, host, *, physical_guard=False):
        self.host, self.root = host, host.rollout_root.resolve()
        self.physical_guard = physical_guard
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
                if len(revised)>6250 or len(revised.split())>831 or len(''.join(revised.split()))>5357:
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
        if name == 'scalebfm_act' and self.physical_guard:
            boundary = physical_preflight(self.host, args['response'])
            save(self.root/f'physical_preflight_{self.serial:04d}.json', boundary)
            if not boundary['accepted']:
                self.host.finished = True
                self.host.stop_reason = 'episode_step_budget'
                return dict(boundary, rollout_finished=True, no_execution=True,
                    physics_advanced=False, stop_reason='episode_step_budget',
                    native_outcome=self.host.harness.evaluator.outcome(self.host.backend),
                    observation_path=str(self.host.harness.latest_path),
                    observation=self.read_current_observation(),
                    next_call={'tool': 'conclude'})
        packet = self.host.dispatch(name,args)
        self.register(packet)
        return packet

    def read_current_observation(self):
        path = str(self.host.harness.latest_path)
        self.register({'observation_path': path})
        return self.read_public(path)


def physical_preflight(host, response):
    """Match frozen harness execute() loop ceiling, including final arrival wait.

    Each tick has five 4ms substeps. Use the loop ceiling (duration+2.1s),
    not the earlier controller timeout (elapsed > duration+2s).
    """
    if host.finished or host.backend.active:
        raise ValueError('Physical action unavailable')
    trajectory = response.get('trajectory')
    if not isinstance(trajectory, list) or not 1 <= len(trajectory) <= 5:
        raise ValueError('Invalid physical trajectory')
    durations = [float(row['duration_s']) for row in trajectory]
    if any(not math.isfinite(d) or not .5 <= d <= 3 for d in durations):
        raise ValueError('Invalid physical duration')
    continuous = host.backend.continuous_chunks_enabled and len(durations) > 1
    if continuous:
        duration = math.fsum(durations)
        if duration > 3+1e-9:
            raise ValueError('Continuous duration exceeds contract')
        durations = [min(3., duration)]
    maximum_ticks = sum(int((duration+2.1)/.02) for duration in durations)
    elapsed = (float(host.backend.data.time)-host.episode_start_sim_s)/.02
    used = round(elapsed)
    if used < 0 or abs(elapsed-used) > 1e-4:
        raise ValueError('Physics elapsed time no longer matches 20ms tick contract')
    if (host.max_episode_steps != 9000 or host.backend.physics_substeps != 5
            or not math.isclose(float(host.backend.model.opt.timestep), .004, abs_tol=1e-12)):
        raise ValueError('Frozen physical timing contract mismatch')
    remaining = max(0, host.max_episode_steps-used)
    return dict(accepted=maximum_ticks <= remaining, step_id=used, remaining_steps=remaining,
        maximum_action_steps=maximum_ticks, maximum_action_s=maximum_ticks*.02,
        max_episode_steps=9000, arrival_wait_included=True,
        bound_basis='Frozen execute loop int((duration+2.1)/.02); 5x.004s per tick')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name,Path(path).resolve())
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def terminal_kind(native, reason, infrastructure_error, diagnosed, calls, *, stop_reason=None, max_calls=MAX_CALLS):
    if native == 'success': return 'host_audited_success'
    if reason == 'diagnostic_stability_stop': return 'safety_stop'
    if infrastructure_error: return 'infrastructure_error'
    if native == 'failure': return 'physical_failure'
    if stop_reason in ('episode_step_budget', 'shared_budget_boundary'): return 'budget_limited_incomplete'
    if diagnosed: return 'agent_stopped_incomplete'
    if calls == max_calls: return 'budget_limited_incomplete'
    return 'adapter_stopped_incomplete'


def validate_authorization(path, run_id, episode, budget):
    expected_file, expected_episode, count = {
        'api-ground-001': ('authorization.json', 'episode-0001', 6),
        'api-ground-002': ('authorization-002.json', 'episode-0002', 120),
        'api-ground-003': ('authorization-003.json', 'episode-0003', 120),
    }[run_id]
    if path.resolve() != ROOT/expected_file or episode != expected_episode:
        raise ValueError('Authorization/run/episode mismatch')
    auth = json.loads(path.read_text())
    expected = dict(run_id=run_id, provider=PROVIDER, model=MODEL, effort=EFFORT,
                    new_simulation_images_approved=True, max_calls=count)
    if any(auth.get(k) != v for k, v in expected.items()):
        raise ValueError('Explicit batch authorization is missing')
    batch_path = budget.route(run_id)/'batch.json'
    batch_ref = budget.reference(batch_path)
    batch = budget.budget.reviewed_batch(batch_ref)
    if batch['max_calls'] != count or batch['batch_id'] != run_id:
        raise ValueError('Batch allowance mismatch')
    if run_id in ('api-ground-002','api-ground-003'):
        if auth.get('batch') != batch_ref or auth.get('approval') != batch['approval']:
            raise ValueError('Authorization approval/batch hash mismatch')
        skill_path = budget.budget.evidence(auth['skill'])
        if auth['skill'] != batch['skill']:
            raise ValueError('Approved episode skill mismatch')
    else:
        skill_path = ROOT/'loco-manip-direct/SKILL.md'
    return auth, count, skill_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='api-ground-001',choices=['api-ground-001','api-ground-002','api-ground-003'])
    parser.add_argument('--episode',required=True)
    parser.add_argument('--authorization',type=Path,required=True)
    parser.add_argument('--budget-hook',type=Path,default=ROOT.parent/'empirical_hook.py')
    parser.add_argument('--backend',type=Path,default=ROOT.parent/'original_backend.py')
    args = parser.parse_args()
    if not args.episode or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.episode):
        raise ValueError('Episode must be a simple lowercase identifier')
    expected_hook=(ROOT.parent/'recovery-20260916/recovery_budget.py' if args.run_id=='api-ground-003' else ROOT.parent/'empirical_hook.py')
    if (args.budget_hook.resolve() != expected_hook
            or args.backend.resolve() != ROOT.parent/'original_backend.py'):
        raise ValueError('Only registered budget hook and original-table backend are allowed')
    if not os.access(RSI/'codex-account-2/run.sh', os.X_OK):
        raise ValueError('Auxiliary launcher unavailable; no fallback')
    budget = load_module(args.budget_hook,'authorized_budget')
    auth, max_calls, skill_source = validate_authorization(args.authorization,args.run_id,args.episode,budget)
    if args.run_id=='api-ground-003':budget.preflight()
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
    campaign = ROOT/'campaign'; campaign.mkdir(exist_ok=True)
    import fcntl
    lock = (campaign/'writer.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output = campaign/args.episode; output.mkdir(exist_ok=False)
    updates = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        RSI/'ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md',RSI/'ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md',
        RSI/'ref/USER_UPDATE_20260916_NO_TRUNCATION_SHARED_SKILLS.md')}
    # Pin the approved seed in this episode; never silently reuse campaign's old seed.
    skill = output/'local-skill/SKILL.md'; skill.parent.mkdir()
    skill.write_bytes(skill_source.read_bytes())
    memory = SkillMemory(output/'memory',skill)
    instructions = skill.read_text()+'\n'+INSTRUCTIONS
    if len(instructions)>6250 or len(instructions.split())>831 or len(''.join(instructions.split()))>5357: raise ValueError('Main skill/harness size cap exceeded')
    task = json.loads((FROZEN/'task_specification.json').read_text())
    task['initial_semantics'] = 'Original table restored. Cube starts on the floor; determine geometry from current calibrated RGB.'
    task['human_feedback'] = 'First move into a range where grasping is possible without further walking, then bend. This is human-proposed planning feedback, not a demonstrated trajectory or verified physical skill.'
    if args.run_id=='api-ground-003':
        source=ROOT.parent/'recovery-20260916/public-transfer.json'
        task['public_prior_experience']=json.loads(source.read_text())
        save(output/'public-transfer.json',task['public_prior_experience'])
    host = LearningHost(output,memory,args.episode,0,task=task['goal'],
        backend_factory=backend_module.create_backend,evaluator_factory=lambda:GroundEvaluator(output/'host_audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='Astra/xhigh API | human planning feedback'),
        support_plane_z_m=None,geometry_provider=finger_geometry,max_episode_steps=9000)
    result = dict(episode_id=args.episode,run_id=args.run_id,backend='MuJoCo',
        human_feedback_used=True,human_demonstration_used=False,independent_physical_reset=False,
        simulation_pauses_during_planning=True,learning_not_frozen_eval=True,overall_success=False,
        user_update_hashes=updates,human_question_eligible=False,max_calls=max_calls)
    save(output/'provenance.json',dict(result,source=str(FROZEN),backend_path=str(args.backend),
        backend_sha256=hashlib.sha256(args.backend.read_bytes()).hexdigest(),
        actor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        skill_source=str(skill_source),skill_sha256=hashlib.sha256(skill.read_bytes()).hexdigest(),
        authorization_path=str(args.authorization),authorization_sha256=hashlib.sha256(args.authorization.read_bytes()).hexdigest()))
    (output/'SKILL.md').write_text(skill.read_text())
    session = None
    try:
        packet = host.dispatch('loco_start',{'task':host.task,'output_dir':str(host.rollout_root/'episode')})
        if host.initialization_error: raise RuntimeError('Backend initialization failed; no API request')
        save(output/'reset_provenance.json',host.backend.reset_provenance)
        result['independent_physical_reset'] = True
        gate = Gate(host, physical_guard=True)
        experience = memory.read(); experience.pop('skill',None)
        history = PublicHistory(instructions, dict(task=task,
            self_experience=experience,calls_available=max_calls), gate.content(packet))
        session = ResponsesSession(output/'api_calls',budget,HTTPSResponses(),args.run_id,max_calls=max_calls)
        while session.count < max_calls and not gate.concluded and not host.finished:
            choice = ({'type':'function','name':'scalebfm_act'} if session.count==0 else
                {'type':'function','name':'conclude'} if host.finished else 'required')
            payload = history.payload(dict(model=MODEL,reasoning={'effort':EFFORT},store=False,stream=True,
                max_output_tokens=MAX_TOKENS,parallel_tool_calls=False,tool_choice=choice,
                tools=gate.specs(),include=['reasoning.encrypted_content']),MAX_BODY)
            save(ROOT/'auxiliary-progress.json',dict(run_id=args.run_id,episode=args.episode,
                state='inference_waiting_no_deadline',api_calls_completed=session.count,
                actions=host.actions,physical_s=float(host.backend.data.time)-host.episode_start_sim_s,
                updated_at_unix=time.time(),physics_paused=True,backend='MuJoCo',
                owner_thread=os.environ.get('CODEX_THREAD_ID'),recovery_owner_thread=os.environ.get('CODEX_THREAD_ID'),
                recovery_state='new_independent_attempt',last_physical_update_at_unix=(Path(host.harness.latest_path).stat().st_mtime),
                inference_in_flight=True))
            response = session.call(payload)
            public_output=output/'api_calls'/f'{session.count:02d}'/'public_output.json'
            natural_ref={'path':str(public_output),'sha256':hashlib.sha256(public_output.read_bytes()).hexdigest()}
            if continue_completed_turn(response,history,gate,natural_ref):
                save(output/f'completed_no_tool_{session.count:04d}.json',dict(response_status='completed',
                    same_episode=True,no_action=True,api_calls=session.count,next_call='scalebfm_act'))
                save(output/'public_history_index.json',history.index)
                continue
            calls = [item for item in response.get('output',[]) if item.get('type')=='function_call']
            if len(calls)!=1: raise ValueError('Exactly one actor tool call required; no retry')
            call = calls[0]
            if session.count==1 and call['name']!='scalebfm_act': raise ValueError('First compatible API call must choose an action')
            save(ROOT/'auxiliary-progress.json',dict(run_id=args.run_id,episode=args.episode,
                state='action_executing' if call['name']=='scalebfm_act' else 'tool_processing',api_calls_completed=session.count,actions=host.actions,
                physical_s=float(host.backend.data.time)-host.episode_start_sim_s,updated_at_unix=time.time(),
                last_physical_update_at_unix=Path(host.harness.latest_path).stat().st_mtime,
                physics_paused=False,backend='MuJoCo',owner_thread=os.environ.get('CODEX_THREAD_ID')))
            packet = gate.dispatch(call['name'],json.loads(call['arguments']))
            if not isinstance(packet,dict): packet = {'public_evidence':packet}
            if isinstance(packet,dict):
                if 'next_call' in packet:
                    packet['next_call'] = {'tool':'conclude' if host.finished else 'scalebfm_act'}
                packet['api_calls_remaining'] = max_calls-session.count
            evidence_path = host.rollout_root/f'public_tool_{session.count:04d}.json'
            decision_path = host.rollout_root/f'public_decision_{gate.serial:04d}.json'
            packet['decision_evidence'] = {'path':str(decision_path)}
            save(evidence_path,packet)
            gate.register({'path':str(evidence_path)})
            evidence_ref = {'path':str(evidence_path),
                'sha256':hashlib.sha256(evidence_path.read_bytes()).hexdigest()}
            history.append(response['output'],call,packet,gate.content(packet),evidence_ref)
            save(output/'public_history_index.json',history.index)
        result.update(stop_reason=host.stop_reason or 'api_batch_call_limit',
            self_diagnosis_complete=gate.concluded,skill_updated=host.skill_updated,
            review_pending=not gate.concluded)
    except BaseException as error:
        boundary = isinstance(error,budget.budget.BudgetError)
        if boundary: host.stop_reason = 'shared_budget_boundary'
        result.update(stop_reason=host.stop_reason if boundary else 'stopped_no_retry',
                      error_type=type(error).__name__,review_pending=True,budget_boundary=boundary)
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
            kind = terminal_kind(native,reason,bool((result.get('error_type') and not result.get('budget_boundary')) or host.runtime_error
                or host.initialization_error),result.get('self_diagnosis_complete'),count,
                stop_reason=host.stop_reason,max_calls=max_calls)
            result.update(actions=host.actions,api_calls=count,
                video=str(output/'video/episode.mp4'),native_outcome=native,
                backend_stop_reason=reason,physical_failure=kind=='physical_failure',
                terminal_kind=kind,episode_terminal_kind=kind)
            if host.backend:result['physical_s']=float(host.backend.data.time)-host.episode_start_sim_s
            if host.backend:
                result['stability_public_status'] = {k:v for k,v in host.backend.status().items()
                    if not k.startswith('_')}
            save(output/'result.json',result)
            save(ROOT/'auxiliary-progress.json',dict(run_id=args.run_id,episode=args.episode,
                state='ended',terminal_kind=kind,api_calls=count,actions=host.actions,
                updated_at_unix=time.time(),result_path=str(output/'result.json')))
            print(json.dumps(result),flush=True)


if __name__ == '__main__': main()
