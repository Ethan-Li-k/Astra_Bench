"""One independent frozen IKEA attempt via the authorized second account."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent
FROZEN=ROOT/'runtime-v1'
sys.path.insert(0,str(FROZEN))
from door_backend import create_backend,DoorEvaluator,SCENE
from rsi.codex_app_server import CodexPolicyAdapter
from rsi.episode_video import EpisodeVideo
from rsi.stdio_transport import StdioAppServer
from rsi.skill_learning import SkillMemory,validate_policy_instructions
from tools.learn_grasp_skill import LearningHost,finger_geometry

RUNTIME='\nRuntime: gpt-6-astra/xhigh only. Use registered physical services; normal tools only for public evidence, calculations, images and NOTES. Do not inspect runtime, host audit, source geometry, other processes or arbitrary files. Keep the same episode/thread after a completed model turn while physics remains in_progress. Await full inference without a deadline; never replay uncertain actions. On usageLimitExceeded or ambiguous transport failure preserve progress and stop automatic retries. After rollout_finished revise the local skill. Combined skill and this runtime contract must remain <=831 words,6250 characters,5357 non-whitespace.\n'
TASK='Open the visible brown bedroom door by safe hand contact, at least 30 degrees from its closed reset, hold it open at least one simulated second, and remain standing. This is a derived MuJoCo IKEA no-latch variant; no handle unlocking is modeled. Use RGB and robot proprioception, not hidden object state. Continue useful attempts until the host terminates; physical budget 240 simulated seconds, with unlimited model reasoning wait.'

def save(p,d):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

class Host(LearningHost):
    def progress(self,phase):
        t=float(self.backend.data.time)-self.episode_start_sim_s if self.backend else 0.
        row=dict(at=now(),phase=phase,episode=self.episode_id,backend='MuJoCo',actions=self.actions,
            sim_s=t,independent_reset=self.backend is not None,physics_paused=True,finished=self.finished)
        save(ROOT/'actor-progress.json',row)
        web=json.loads((ROOT/'web-progress.json').read_text());web.update(phase=phase,execution_kind='policy',
            task_instance='Door_West brown bedroom door',policy_state=phase,attempts=int(self.backend is not None),
            actions=self.actions,sim_s=t,next_step='等待完整推理并执行下一安全动作；本回合自然终态后审查。')
        if phase=='physical_action_completed':web['last_actual_progress_at']=row['at']
        save(ROOT/'web-progress.json',web)
    def dispatch(self,name,args):
        packet=super().dispatch(name,args)
        self.progress('physical_action_completed' if name=='scalebfm_act' else 'inference_waiting')
        return packet

def main():
    args=argparse.ArgumentParser();args.add_argument('--episode',required=True);a=args.parse_args()
    campaign=ROOT/'campaign';campaign.mkdir(exist_ok=True)
    lock=(campaign/'writer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    output=campaign/a.episode;output.mkdir(exist_ok=False)
    updates={}
    for name in ['PARALLEL_SKILLS','HUMAN_FEEDBACK','IKEA_OWNER','NO_TRUNCATION_SHARED_SKILLS']:
        path=ROOT.parent/f'ref/USER_UPDATE_20260916_{name}.md';path.read_text();updates[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    for rel,sha in json.loads((FROZEN/'manifest.json').read_text()).items():
        if hashlib.sha256((FROZEN/rel).read_bytes()).hexdigest()!=sha:raise RuntimeError('Frozen source drift: '+rel)
    skill=ROOT/'skills/loco-manip-direct/SKILL.md'
    memory=SkillMemory(campaign/'memory',skill)
    memory.runtime_instructions=RUNTIME
    size=validate_policy_instructions(skill.read_text(),RUNTIME)
    save(output/'length-check.json',size)
    (output/'SKILL.md').write_bytes(skill.read_bytes())
    host=Host(output,memory,a.episode,0,task=TASK,backend_factory=create_backend,
        evaluator_factory=lambda:DoorEvaluator(output/'host-audit'),
        image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='IKEA no-latch | Astra/xhigh Direct'),
        support_plane_z_m=None,geometry_provider=finger_geometry,max_episode_steps=12000,require_selection=True)
    sources={f'simple-door-{n}':dict(path=str(skill.parent/f'context/simple-door-{n}.md'),
        mechanism='SIMPLE corrected-frame public door experience; different scene and hand geometry; conditional transfer only') for n in ['0012','0013','0014']}
    host.skill_sources=sources
    agent=output/'agent';agent.mkdir();(agent/'scratch').mkdir()
    launcher=ROOT.parent/'codex-account-2/run.sh'
    if not os.access(launcher,os.X_OK):raise RuntimeError('Second-account launcher unavailable; no fallback')
    transport=None;error=None;adapter=None;started=time.monotonic();complete_turns=0
    save(output/'provenance.json',dict(backend='MuJoCo',scene=str(SCENE),scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        runtime_manifest=str(FROZEN/'manifest.json'),model='gpt-6-astra',effort='xhigh',route=str(launcher),
        user_update_hashes=updates,human_feedback_used=False,human_demonstration_used=False,
        completion_contract=DoorEvaluator.contract,original_usd=False,simulation_paused_during_reasoning=True,
        policy_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    try:
        packet=host.dispatch('loco_start',dict(task=TASK,output_dir=str(host.rollout_root/'episode')))
        if host.initialization_error:raise RuntimeError('Physical initialization failed; no model request')
        save(output/'reset-provenance.json',host.backend.reset_provenance)
        save(agent/'workspace.json',dict(task=TASK,python=sys.executable,skill=str(skill),
            notes=str(agent/'NOTES.md'),public_evidence_root=str(host.rollout_root),initial_packet=packet,
            skill_sources=sources,completion_contract=DoorEvaluator.contract,max_episode_steps=12000))
        transport=StdioAppServer([str(launcher),'app-server','--stdio'],output/'app-server')
        adapter=CodexPolicyAdapter(transport,host,agent,developer_instructions=skill.read_text()+RUNTIME,normal_tools=True,timeout=None)
        adapter.connect()
        save(output/'model-route.json',dict(thread=adapter.thread_id,model=adapter.model,effort=adapter.effort,
            launcher=str(launcher),inference_deadline=None))
        while not host.skill_updated:
            host.progress('inference_waiting')
            turn=adapter.run_turn('Continue this independent IKEA physical attempt. Read workspace.json and initial_packet; the host has already called loco_start. Read public experience selectively and select sources before acting. Follow next_call: '+json.dumps(host.next_call())+'. Physical in_progress survives natural model turn completion. After rollout_finished submit skill_update.')
            complete_turns+=1;save(output/f'turn-{complete_turns:03d}.json',turn)
    except BaseException as e:
        error=dict(type=type(e).__name__,message=str(e));save(output/'system-error.json',error)
        print(json.dumps(error),flush=True)
    finally:
        host.close()
        if host.harness:host.harness.evaluator.close()
        if transport:transport.close()
    outcome=host.harness.evaluator.outcome(host.backend) if host.harness else 'not_started'
    kind=('system' if error else 'success_pending_audit' if outcome=='success' else 'safety' if host.backend and host.backend.reason else 'truncated' if host.stop_reason=='episode_step_budget' else 'physical_failure' if outcome=='failure' else 'incomplete')
    result=dict(episode=a.episode,backend='MuJoCo',outcome=outcome,terminal_kind=kind,stop_reason=host.stop_reason,
        actions=host.actions,sim_s=float(host.backend.data.time)-host.episode_start_sim_s if host.backend else 0.,
        complete_model_turns=complete_turns,skill_updated=host.skill_updated,error=error,wall_s=time.monotonic()-started,
        audited_success=False,video=str(output/'video/episode.mp4'))
    save(output/'result.json',result)
    manifest=json.loads((ROOT/'video-manifest.json').read_text())
    if host.capture:
        manifest['videos'].append(dict(path=result['video'],complete=True,kind='policy_incomplete' if kind in ('system','truncated','incomplete') else 'policy_success_pending_audit' if outcome=='success' else 'policy_failure',
            task='brown_bedroom_door',episode=a.episode,backend='MuJoCo',sim_s=result['sim_s']))
        save(ROOT/'video-manifest.json',manifest)
    host.progress('episode_ended_review_pending')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
