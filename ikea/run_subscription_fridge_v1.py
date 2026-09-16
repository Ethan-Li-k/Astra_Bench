"""Future independent fridge episode; activation requires an audited apple completion."""
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
from policy_support_fridge_v1 import Host,TASK,RUNTIME,FROZEN,save,now
from fridge_backend import create_backend,SCENE
from fridge_evaluator import FridgeEvaluator
from rsi.codex_app_server import CodexPolicyAdapter
from rsi.episode_video import EpisodeVideo
from rsi.stdio_transport import StdioAppServer
from rsi.skill_learning import SkillMemory,validate_policy_instructions
from rsi.ikea_hand_geometry import HandGeometryProvider
from fridge_physical_guard_v1 import physical_preflight

TURN_PROMPT=('Continue this IKEA physical attempt. Read workspace.json and current public observation; '
    'loco_start already ran once. Read/select relevant public experiences before actions. '
    'Persist current problem, goal, mistakes and measured progress using the authorized experience_select journal if NOTES is read-only. Follow next_call. '
    'A completed model turn leaves in_progress physics open: continue the same reset and current ACK. '
    'Never replay uncertain actions. After rollout_finished submit evidence-backed skill_update. ')

class SubscriptionHost(Host):
    def progress(self,phase):
        super().progress(phase)
        web=json.loads((ROOT/'web-progress.json').read_text())
        executed=[p.parent.parent.name for p in (ROOT/'campaign').glob('*/rollout/history.jsonl')
            if any(json.loads(s)['tool']=='scalebfm_act' for s in p.read_text().splitlines())]
        web.update(backend='MuJoCo source-aligned refrigerator hinged doors',
            variant='usd-aligned-fridge-hinged-no-gasket-v1',episode=self.episode_id,
            policy_route='codex-account-2/run.sh subscription gpt-6-astra/xhigh',
            human_feedback_used=False,actor_running=phase!='episode_ended_review_pending',
            attempts=len(executed),registered_episodes=sum(1 for p in (ROOT/'campaign').glob('*/reset-provenance.json')))
        web['tasks']['fridge']['physical_attempts']=sum(n.startswith('fridge-') for n in executed)
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

def admitted_configuration(root=ROOT):
    """Read-only gate before acquiring a writer, creating output, or starting physics."""
    ready=json.loads((root/'fridge-subscription-v1-READY.json').read_text())
    if ready.get('ready') is not True:raise RuntimeError('Subscription candidate not ready')
    episode=ready['prerequisite_apple_episode']
    if Path(episode).name!=episode or not episode.startswith('apple-'):
        raise RuntimeError('Local apple episode required')
    prerequisite=root/'campaign'/episode
    if (json.loads((prerequisite/'public-review.json').read_text()).get('audited_success') is not True
        or json.loads((prerequisite/'independent-review.json').read_text()).get('audited_task_success') is not True):
        raise RuntimeError('Audited apple completion required before refrigerator task')
    for rel,digest in ready['source_sha256'].items():
        if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Preflight source drift: '+rel)
    return ready

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--episode',default='fridge-0001');a=parser.parse_args()
    if Path(a.episode).name!=a.episode or not a.episode.startswith('fridge-'):
        raise RuntimeError('Unique local refrigerator episode required')
    ready=admitted_configuration()
    launcher=ROOT.parent/'codex-account-2/run.sh'
    if not os.access(launcher,os.X_OK):raise RuntimeError('Second-account launcher unavailable; no fallback')
    campaign=ROOT/'campaign';lock=(campaign/'writer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output=campaign/a.episode;output.mkdir(exist_ok=False)
    updates={}
    for name in ('PARALLEL_SKILLS','HUMAN_FEEDBACK','IKEA_OWNER','NO_TRUNCATION_SHARED_SKILLS'):
        path=ROOT.parent/f'ref/USER_UPDATE_20260916_{name}.md';path.read_text();updates[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    for rel,digest in json.loads((FROZEN/'manifest.json').read_text()).items():
        if hashlib.sha256((FROZEN/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Frozen runtime drift')
    skill=ROOT/'skills/fridge-open-v1/SKILL.md'
    save(output/'length-check.json',validate_policy_instructions(skill.read_text(),RUNTIME+TURN_PROMPT))
    shutil.copy2(skill,output/'SKILL.md')
    memory=SkillMemory(campaign/'fridge-subscription-memory-v1',skill);memory.runtime_instructions=RUNTIME+TURN_PROMPT
    snapshot=output/'host-source-snapshot';snapshot.mkdir()
    source_files=[Path(__file__),ROOT/'policy_support_fridge_v1.py',ROOT/'fridge_physical_guard_v1.py']
    hashes={}
    for path in source_files:shutil.copy2(path,snapshot/path.name);hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    save(snapshot/'manifest.json',dict(captured_at=now(),files=hashes))
    public=output/'rollout/experience';public.mkdir(parents=True);sources={}
    for source_id,path in [('ikea-door-0002-public',campaign/'api-memory/versions/0001.md'),
        ('simple-door-0014-public',campaign/'door-0002/rollout/experience/simple-door-0014.md')]:
        target=public/path.name;shutil.copy2(path,target)
        sources[source_id]=dict(path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            scope='Conditional public evidence; robot/hand/layout compatibility must be rechecked. No target replay.')
    host=SubscriptionHost(output,memory,a.episode,0,task=TASK,backend_factory=create_backend,
        evaluator_factory=lambda:FridgeEvaluator(output/'host-audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='IKEA refrigerator | Astra/xhigh subscription | derived no gasket'),
        support_plane_z_m=None,geometry_provider=HandGeometryProvider(output/'rollout/episode'),max_episode_steps=12000,require_selection=True)
    host.skill_sources=sources
    agent=output/'agent';agent.mkdir();(agent/'scratch').mkdir();shutil.copy2(skill,agent/'SKILL.md')
    save(output/'provenance.json',dict(episode=a.episode,backend='MuJoCo',scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        runtime_manifest=str(FROZEN/'manifest.json'),model='gpt-6-astra',effort='xhigh',route=str(launcher),
        user_update_hashes=updates,human_feedback_used=False,human_demonstration_used=False,human_feedback_sources=[],completion_contract=FridgeEvaluator.contract,
        original_usd=False,simulation_paused_during_reasoning=True,prerequisite_apple_episode=ready['prerequisite_apple_episode'],
        scope='Source geometry with derived door hinges/mass/collision; no added handle or gasket.',
        policy_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    transport=None;adapter=None;error=None;complete_turns=0;started=time.monotonic()
    try:
        packet=host.dispatch('loco_start',dict(task=TASK,output_dir=str(host.rollout_root/'episode')))
        if host.initialization_error:raise RuntimeError('Physical initialization failed; no model turn')
        save(output/'reset-provenance.json',host.backend.reset_provenance)
        save(agent/'workspace.json',dict(task=TASK,python=sys.executable,skill=str(skill),notes=str(agent/'NOTES.md'),
            public_evidence_root=str(host.rollout_root),initial_packet=packet,skill_sources=sources,
            completion_contract=FridgeEvaluator.contract,max_episode_steps=12000,human_feedback_used=False))
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
        audited_success=False,human_feedback_used=False,video=str(output/'video/episode.mp4'),automatic_retry=False)
    save(output/'result.json',result)
    if host.capture:
        manifest=json.loads((ROOT/'video-manifest.json').read_text());manifest['videos'].append(dict(path=result['video'],complete=True,
            kind='policy_success_pending_audit' if outcome=='success' else 'policy_failure' if kind in ('physical_failure','safety') else 'policy_incomplete',
            task='fridge',episode=a.episode,backend='MuJoCo',sim_s=result['sim_s']))
        save(ROOT/'video-manifest.json',manifest)
    host.progress('episode_ended_review_pending');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
