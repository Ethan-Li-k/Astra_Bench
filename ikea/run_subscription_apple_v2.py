"""One fresh subscription episode after recorded API429; no API retry or old action replay."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parent
from policy_support_apple_v2 import Host,TASK,RUNTIME,FROZEN,save,now
from apple_backend import create_backend,AppleEvaluator,SCENE
from rsi.codex_app_server import CodexPolicyAdapter
from rsi.episode_video import EpisodeVideo
from rsi.stdio_transport import StdioAppServer
from rsi.skill_learning import SkillMemory,validate_policy_instructions
from rsi.ikea_hand_geometry import HandGeometryProvider
sys.path.insert(0,str(ROOT/'api-apple-v2'))
from transport_gate import physical_preflight

TURN_PROMPT=('Continue this IKEA physical attempt. Read workspace.json and current public observation; '
    'loco_start already ran once. Read/select relevant public experiences before actions. '
    'Keep current problem, goal, mistakes and measured progress in NOTES. Follow next_call. '
    'A completed model turn leaves in_progress physics open: continue the same reset and current ACK. '
    'Never replay uncertain actions. After rollout_finished submit evidence-backed skill_update. ')

class SubscriptionHost(Host):
    def progress(self,phase):
        super().progress(phase)
        web=json.loads((ROOT/'web-progress.json').read_text())
        executed=[p.parent.parent.name for p in (ROOT/'campaign').glob('*/rollout/history.jsonl')
            if any(json.loads(s)['tool']=='scalebfm_act' for s in p.read_text().splitlines())]
        web.update(backend='MuJoCo source-aligned apple convex collision',
            variant='source-aligned-apple-convex-close-robot-v2',episode=self.episode_id,
            policy_route='codex-account-2/run.sh subscription gpt-6-astra/xhigh',
            human_feedback_used=True,actor_running=phase!='episode_ended_review_pending',
            attempts=len(executed),registered_episodes=sum(1 for p in (ROOT/'campaign').glob('*/reset-provenance.json')))
        web['tasks']['apple']['physical_attempts']=sum(n.startswith('apple-') for n in executed)
        save(ROOT/'web-progress.json',web)

    def dispatch(self,name,args):
        if name=='scalebfm_act' and not self.finished:
            check=physical_preflight(self,args['response'])
            if not check['accepted']:
                self.finished=True;self.stop_reason='episode_step_budget'
                packet=dict(check,rollout_finished=True,no_execution=True,physics_advanced=False,
                    stop_reason=self.stop_reason,native_outcome=self.harness.evaluator.outcome(self.backend),
                    observation_path=str(self.harness.latest_path),
                    observation=json.loads(self.harness.latest_path.read_text()),next_call=self.next_call())
                save(self.rollout_root/'physical-budget-stop.json',packet)
                return packet
        return super().dispatch(name,args)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--episode',default='apple-0002');a=parser.parse_args()
    ready=json.loads((ROOT/'subscription-apple-v2-READY.json').read_text())
    if ready.get('ready') is not True:raise RuntimeError('Subscription candidate not ready')
    for rel,digest in ready['source_sha256'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Preflight source drift: '+rel)
    launcher=ROOT.parent/'codex-account-2/run.sh'
    if not os.access(launcher,os.X_OK):raise RuntimeError('Second-account launcher unavailable; no fallback')
    campaign=ROOT/'campaign';lock=(campaign/'writer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output=campaign/a.episode;output.mkdir(exist_ok=False)
    updates={}
    for name in ('PARALLEL_SKILLS','HUMAN_FEEDBACK','IKEA_OWNER','NO_TRUNCATION_SHARED_SKILLS'):
        path=ROOT.parent/f'ref/USER_UPDATE_20260916_{name}.md';path.read_text();updates[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    for rel,digest in json.loads((FROZEN/'manifest.json').read_text()).items():
        if hashlib.sha256((FROZEN/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Frozen runtime drift')
    skill=ROOT/'skills/apple-grasp-v2/SKILL.md'
    save(output/'length-check.json',validate_policy_instructions(skill.read_text(),RUNTIME+TURN_PROMPT))
    shutil.copy2(skill,output/'SKILL.md')
    memory=SkillMemory(campaign/'apple-subscription-memory-v2',skill);memory.runtime_instructions=RUNTIME+TURN_PROMPT
    snapshot=output/'host-source-snapshot';snapshot.mkdir()
    source_files=[Path(__file__),ROOT/'policy_support_apple_v2.py',ROOT/'api-apple-v2/transport_gate.py',ROOT/'api-apple-v2/history_bound.py']
    hashes={}
    for path in source_files:shutil.copy2(path,snapshot/path.name);hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    save(snapshot/'manifest.json',dict(captured_at=now(),files=hashes))
    public=output/'rollout/experience';public.mkdir(parents=True);sources={}
    for source_id,path in [('r018-0438-public',ROOT/'downstream-reference/r018-episode-0438-public.json'),
        ('simple-bendpick-0006-public',ROOT/'downstream-reference/simple-bendpick-episode-0006-public.json'),
        ('ikea-door-0002-public',campaign/'api-memory/versions/0001.md'),
        ('apple-0001-public-counterexamples',ROOT/'experience-candidates/apple-0001-public-failure-v1.json'),
        ('apple-0001-ankle-hold-candidate',ROOT/'experience-candidates/apple-0001-ankle-hold-v1.json'),
        ('human-H001-004-side-grasp',ROOT/'downstream-reference/H001-user-feedback-004.json')]:
        target=public/path.name;shutil.copy2(path,target)
        sources[source_id]=dict(path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            scope='Conditional public evidence; robot/hand/layout compatibility must be rechecked. No target replay.')
    host=SubscriptionHost(output,memory,a.episode,0,task=TASK,backend_factory=create_backend,
        evaluator_factory=lambda:AppleEvaluator(output/'host-audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='IKEA apple | Astra/xhigh subscription | H001-004'),
        support_plane_z_m=None,geometry_provider=HandGeometryProvider(output/'rollout/episode'),max_episode_steps=12000,require_selection=True)
    host.skill_sources=sources
    agent=output/'agent';agent.mkdir();(agent/'scratch').mkdir();shutil.copy2(skill,agent/'SKILL.md')
    feedback=ROOT/'downstream-reference/H001-user-feedback-004.json'
    save(output/'provenance.json',dict(episode=a.episode,backend='MuJoCo',scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        runtime_manifest=str(FROZEN/'manifest.json'),model='gpt-6-astra',effort='xhigh',route=str(launcher),
        user_update_hashes=updates,human_feedback_used=True,human_demonstration_used=False,human_feedback_source='H001-user-feedback-004',
        human_feedback_sha256=hashlib.sha256(feedback.read_bytes()).hexdigest(),completion_contract=AppleEvaluator.contract,
        original_usd=False,simulation_paused_during_reasoning=True,previous_episode='apple-0001',
        previous_termination='HTTP429 system interruption; remote request/fees unknown, no retry',
        same_previous_reset=False,reset_change='Robot0.25m closer; original apple/table/scene retained',
        policy_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    transport=None;adapter=None;error=None;complete_turns=0;started=time.monotonic()
    try:
        packet=host.dispatch('loco_start',dict(task=TASK,output_dir=str(host.rollout_root/'episode')))
        if host.initialization_error:raise RuntimeError('Physical initialization failed; no model turn')
        save(output/'reset-provenance.json',host.backend.reset_provenance)
        save(agent/'workspace.json',dict(task=TASK,python=sys.executable,skill=str(skill),notes=str(agent/'NOTES.md'),
            public_evidence_root=str(host.rollout_root),initial_packet=packet,skill_sources=sources,
            completion_contract=AppleEvaluator.contract,max_episode_steps=12000,human_feedback_used=True))
        transport=StdioAppServer([str(launcher),'app-server','--stdio'],output/'app-server')
        adapter=CodexPolicyAdapter(transport,host,agent,developer_instructions=skill.read_text()+RUNTIME,
            normal_tools=True,timeout=None)
        adapter.connect();save(output/'model-route.json',dict(thread=adapter.thread_id,model=adapter.model,
            effort=adapter.effort,launcher=str(launcher),inference_deadline=None))
        while not host.skill_updated:
            host.progress('inference_waiting')
            prompt=TURN_PROMPT+' Current next_call: '+json.dumps(host.next_call())
            if host.harness:prompt+=' Latest public observation: '+str(host.harness.latest_path)
            turn=adapter.run_turn(prompt)
            complete_turns+=1;save(output/f'turn-{complete_turns:03d}.json',turn)
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc));save(output/'system-error.json',error)
        print(json.dumps(error),flush=True)
    finally:
        host.close()
        if host.harness:host.harness.evaluator.close()
        if transport:transport.close()
    outcome=host.harness.evaluator.outcome(host.backend) if host.harness else 'not_started'
    exhausted=error and 'usageLimitExceeded' in str(error)
    kind=('usage_limit' if exhausted else 'system' if error else 'success_pending_audit' if outcome=='success' else
        'safety' if host.backend and host.backend.reason else 'physical_budget' if host.stop_reason=='episode_step_budget' else
        'physical_failure' if outcome=='failure' else 'incomplete')
    result=dict(episode=a.episode,backend='MuJoCo',outcome=outcome,terminal_kind=kind,stop_reason=host.stop_reason,
        actions=host.actions,sim_s=float(host.backend.data.time)-host.episode_start_sim_s if host.backend else 0.,
        complete_model_turns=complete_turns,skill_updated=host.skill_updated,error=error,wall_s=time.monotonic()-started,
        audited_success=False,human_feedback_used=True,video=str(output/'video/episode.mp4'),automatic_retry=False)
    save(output/'result.json',result)
    if host.capture:
        manifest=json.loads((ROOT/'video-manifest.json').read_text());manifest['videos'].append(dict(path=result['video'],complete=True,
            kind='policy_success_pending_audit' if outcome=='success' else 'policy_failure' if kind in ('physical_failure','safety') else 'policy_incomplete',
            task='tabletop_apple',episode=a.episode,backend='MuJoCo',sim_s=result['sim_s']))
        save(ROOT/'video-manifest.json',manifest)
    host.progress('episode_ended_review_pending');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
