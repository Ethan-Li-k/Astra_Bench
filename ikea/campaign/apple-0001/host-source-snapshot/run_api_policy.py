"""New independent IKEA API episode; no resume/replay of old remote requests."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from policy_support_apple_v1 import Host,TASK,RUNTIME,save,now,FROZEN
from apple_backend import create_backend,AppleEvaluator,SCENE
from rsi.episode_video import EpisodeVideo
from rsi.skill_learning import SkillMemory,validate_policy_instructions
from rsi.ikea_hand_geometry import HandGeometryProvider
from transport_gate import ResponsesSession,HTTPSResponses,Gate,MAX_TOKENS,MAX_BODY,MODEL,EFFORT,PROVIDER
from history_bound import PublicHistory
from budget_hook import RegisteredBudget,reference

API_CONTRACT=RUNTIME+' API tools have public_decision fields for brief observations/hypothesis/evidence/uncertainty/expected/next_test. Use experience_select before acting. read_public_evidence reads issued public files only. conclude records a stall while in_progress; only after a real terminal condition include revised_skill and lesson. No arbitrary file or host-state tool is available. Full responses are awaited; no automatic retries.\n'
RUN='api-ikea-apple-001'

class APIHost(Host):
    def progress(self,phase):
        super().progress(phase)
        web=json.loads((ROOT/'web-progress.json').read_text())
        web['registered_episodes']=sum(1 for p in (ROOT/'campaign').glob('*/reset-provenance.json'))
        if self.backend and not (self.output/'reset-provenance.json').exists():web['registered_episodes']+=1
        executed = [p.parent.parent.name for p in (ROOT/'campaign').glob('*/rollout/history.jsonl')
                    if any(json.loads(line)['tool']=='scalebfm_act' for line in p.read_text().splitlines())]
        web['attempts']=len(executed)
        web['backend']='MuJoCo source-aligned apple convex collision'
        web['policy_route']='authorized API llm-gateway.galbot.com'
        web['variant']='source-aligned-apple-convex-0.18kg-v1'
        web['tasks']['apple']['physical_attempts']=sum(name.startswith('apple-') for name in executed)
        web['actor_running']=phase!='episode_ended_review_pending'
        save(ROOT/'web-progress.json',web)

def register(output,skill):
    terms=json.loads((ROOT/'budget-coordination/batch-terms.example.json').read_text());terms.pop('example_only')
    terms.update(batch_id=RUN,purpose='Fresh independent IKEA original tabletop apple grasp; no old request replay',
        episode=output.name,episode_output=str(output),scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        skill_sha256=hashlib.sha256(skill.read_bytes()).hexdigest(),
        entrypoint_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        public_information='Only current RGB, named robot state/calibration, tools and public local skill/experience; no host audit.')
    path=output/'batch-terms.json';save(path,terms)
    cmd=[sys.executable,str(ROOT/'budget-coordination/register_batch.py'),'--terms',str(path),'--name',RUN,
        '--retain-legacy',str(ROOT.parent/'artifacts/R021/api-ground-001/batch.json'),
        '--retain-legacy',str(ROOT.parent/'artifacts/R021/api-ground-002/batch.json')]
    r=subprocess.run(cmd,text=True,capture_output=True)
    (output/'registration.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('New batch registration failed; no API request')
    return ROOT/'budget-coordination/approvals'/RUN/'registration.json'

def main():
    p=argparse.ArgumentParser();p.add_argument('--episode',default='apple-0001');args=p.parse_args()
    campaign=ROOT/'campaign';campaign.mkdir(exist_ok=True)
    lock=(campaign/'writer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output=campaign/args.episode;output.mkdir(exist_ok=False)
    # Read current per-episode constraints; this does not query provider quota or pricing.
    updates={}
    for name in ('PARALLEL_SKILLS','HUMAN_FEEDBACK','IKEA_OWNER','NO_TRUNCATION_SHARED_SKILLS'):
        path=ROOT.parent/f'ref/USER_UPDATE_20260916_{name}.md';path.read_text();updates[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    for rel,sha in json.loads((FROZEN/'manifest.json').read_text()).items():
        if hashlib.sha256((FROZEN/rel).read_bytes()).hexdigest()!=sha:raise RuntimeError('Frozen source drift')
    source=ROOT/'skills/apple-grasp-v1/SKILL.md';skill=output/'SKILL.md';skill.write_bytes(source.read_bytes())
    size=validate_policy_instructions(skill.read_text(),API_CONTRACT);save(output/'length-check.json',size)
    snapshot=output/'host-source-snapshot';snapshot.mkdir()
    source_files=[Path(__file__),*(Path(__file__).parent/n for n in ('transport_gate.py','history_bound.py','budget_hook.py')),ROOT/'policy_support_apple_v1.py']
    hashes={}
    for path in source_files:
        shutil.copy2(path,snapshot/path.name);hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    save(snapshot/'manifest.json',dict(captured_at=now(),capture='before registration and physical initialization',files=hashes))
    registration=register(output,skill);budget=RegisteredBudget(registration)
    memory=SkillMemory(campaign/'apple-api-memory',source);memory.runtime_instructions=API_CONTRACT
    # Retain independent account episode experience in the public evidence index; never host audit.
    public=output/'rollout/experience';public.mkdir(parents=True)
    sources={}
    copies=[]
    for source_id,path in [
        ('r018-0438-public',ROOT/'downstream-reference/r018-episode-0438-public.json'),
        ('simple-bendpick-0006-public',ROOT/'downstream-reference/simple-bendpick-episode-0006-public.json'),
        ('ikea-door-0002-public',campaign/'api-memory/versions/0001.md')]:
        target=public/path.name
        shutil.copy2(path,target)
        sources[source_id]=dict(path=str(target),scope='Conditional public evidence only; verify robot, hand and task compatibility; no coordinates or success transfer.')
    prior=None
    host=APIHost(output,memory,args.episode,0,task=TASK,backend_factory=create_backend,
        evaluator_factory=lambda:AppleEvaluator(output/'host-audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='IKEA apple grasp | Astra/xhigh API Direct'),
        support_plane_z_m=None,geometry_provider=HandGeometryProvider(output/'rollout/episode'),max_episode_steps=12000,require_selection=True)
    host.skill_sources=sources
    save(output/'provenance.json',dict(run_id=RUN,episode=args.episode,model=MODEL,effort=EFFORT,provider=PROVIDER,
        scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),runtime_manifest=str(FROZEN/'manifest.json'),
        registration=str(registration),user_update_hashes=updates,human_feedback_used=False,human_demonstration_used=False,
        original_usd=False,completion_contract=AppleEvaluator.contract,simulation_paused_during_reasoning=True))
    session=None;gate=None;error=None;started=time.monotonic()
    try:
        packet=host.dispatch('loco_start',dict(task=TASK,output_dir=str(host.rollout_root/'episode')))
        if host.initialization_error:raise RuntimeError('Physical initialization failed; no API request')
        save(output/'reset-provenance.json',host.backend.reset_provenance)
        gate=Gate(host,physical_guard=True);gate.register(sources)
        if prior and prior.exists():gate.register(copies)
        workspace=host.rollout_root/'workspace.json'
        save(workspace,dict(task=TASK,skill_sources=sources,initial_observation_path=str(host.harness.latest_path),
            public_evidence_root=str(host.rollout_root),completion_contract=AppleEvaluator.contract,
            note='API public-evidence tools replace native shell; initial images and state are already attached.'))
        packet['workspace']={'path':str(workspace)}
        history=PublicHistory(skill.read_text()+API_CONTRACT,dict(task=TASK,skill_sources=sources,
            self_experience=memory.read(),calls_available=120),gate.content(packet))
        session=ResponsesSession(output/'api-calls',budget,HTTPSResponses(),RUN,max_calls=120)
        # Natural model responses continue this same simulation. Only the explicitly registered call budget bounds dispatches.
        while session.count<session.max_calls and not gate.concluded:
            host.progress('inference_waiting')
            choice=({'type':'function','name':'experience_select'} if not host.selection_recorded else
                {'type':'function','name':'conclude'} if host.finished else 'required')
            payload=history.payload(dict(model=MODEL,reasoning={'effort':EFFORT},store=False,stream=True,
                max_output_tokens=MAX_TOKENS,parallel_tool_calls=False,tool_choice=choice,tools=gate.specs(),
                include=['reasoning.encrypted_content']),MAX_BODY)
            response=session.call(payload)
            calls=[i for i in response.get('output',[]) if i.get('type')=='function_call']
            if len(calls)!=1:raise RuntimeError('Exactly one completed actor tool exchange required; no automatic retry')
            call=calls[0]
            try:packet=gate.dispatch(call['name'],json.loads(call['arguments']))
            except ValueError as exc:
                # Only proven pre-admission validation is correctable; host marks partial physical errors itself.
                if host.execution_error or (host.backend and host.backend.active):raise
                packet=dict(error_type='validation_rejected',error=str(exc),no_execution=True,
                    observation_path=str(host.harness.latest_path),next_call=host.next_call())
            if not isinstance(packet,dict):packet=dict(public_evidence=packet)
            packet['api_calls_remaining']=session.max_calls-session.count
            evidence=host.rollout_root/f'public_tool_{session.count:04d}.json';save(evidence,packet)
            gate.register({'path':str(evidence)})
            history.append(response['output'],call,packet,gate.content(packet),
                dict(path=str(evidence),sha256=hashlib.sha256(evidence.read_bytes()).hexdigest()))
            save(output/'public-history-index.json',history.index)
        if not host.finished:host.stop_reason='registered_api_call_budget'
    except BaseException as e:
        error=dict(type=type(e).__name__,message=str(e));save(output/'system-error.json',error)
        if isinstance(e,budget.budget.BudgetError):host.stop_reason='shared_budget_boundary'
        print(json.dumps(error),flush=True)
    finally:
        host.close()
        if host.harness:host.harness.evaluator.close()
    outcome=host.harness.evaluator.outcome(host.backend) if host.harness else 'not_started'
    kind=('budget' if host.stop_reason in ('registered_api_call_budget','shared_budget_boundary','episode_step_budget') else
          'system' if error else 'success_pending_audit' if outcome=='success' else 'safety' if host.backend and host.backend.reason else
          'physical_failure' if outcome=='failure' else 'incomplete')
    result=dict(episode=args.episode,run_id=RUN,backend='MuJoCo',outcome=outcome,terminal_kind=kind,
        stop_reason=host.stop_reason,actions=host.actions,sim_s=float(host.backend.data.time)-host.episode_start_sim_s if host.backend else 0.,
        api_calls=session.count if session else 0,skill_updated=host.skill_updated,error=error,wall_s=time.monotonic()-started,
        audited_success=False,video=str(output/'video/episode.mp4'),unknown_api_fees_retained=True)
    save(output/'result.json',result)
    if host.capture:
        manifest=json.loads((ROOT/'video-manifest.json').read_text());manifest['videos'].append(dict(path=result['video'],
            complete=True,kind='policy_success_pending_audit' if outcome=='success' else 'policy_failure' if kind in ('physical_failure','safety') else 'policy_incomplete',
            task='tabletop_apple',episode=args.episode,backend='MuJoCo',sim_s=result['sim_s']))
        save(ROOT/'video-manifest.json',manifest)
    host.progress('episode_ended_review_pending');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
