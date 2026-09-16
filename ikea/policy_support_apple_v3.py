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
FROZEN=ROOT/'runtime-apple-v3'
sys.path.insert(0,str(FROZEN))
from apple_backend import create_backend,AppleEvaluator,SCENE
from rsi.codex_app_server import CodexPolicyAdapter
from rsi.episode_video import EpisodeVideo
from rsi.stdio_transport import StdioAppServer
from rsi.skill_learning import SkillMemory,validate_policy_instructions
from tools.learn_grasp_skill import LearningHost,finger_geometry

RUNTIME='\nRuntime: gpt-6-astra/xhigh only. Use registered physical services; normal tools only for public evidence, calculations, images and NOTES. Do not inspect runtime, host audit, source geometry, other processes or arbitrary files. Keep the same episode/thread after a completed model turn while physics remains in_progress. Await full inference without a deadline; never replay uncertain actions. On usageLimitExceeded or ambiguous transport failure preserve progress and stop automatic retries. After rollout_finished revise the local skill. Combined skill and this runtime contract must remain <=831 words,6250 characters,5357 non-whitespace.\n'
TASK='Grasp the visible tabletop apple with either DEX3 hand. Lift it at least 8cm from its settled initial height and retain opposing-finger support, clear of external support, for at least one simulated second while remaining standing. Robot reset is0.25m closer than apple-0001; no approach-from-the-old-start credit. This uses the original IKEA apple geometry/pose in a derived MuJoCo convex-collision variant with assumed mass, not Isaac. Use only current RGB and named robot state. Continue useful attempts until host termination; physical budget 240 simulated seconds; unlimited model reasoning wait.'

def save(p,d):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

class Host(LearningHost):
    def progress(self,phase):
        t=float(self.backend.data.time)-self.episode_start_sim_s if self.backend else 0.
        row=dict(at=now(),phase=phase,episode=self.episode_id,backend='MuJoCo',actions=self.actions,
            sim_s=t,independent_reset=self.backend is not None,physics_paused=phase!='action_executing',finished=self.finished)
        save(ROOT/'actor-progress.json',row)
        web=json.loads((ROOT/'web-progress.json').read_text())
        executed=[]
        for p in (ROOT/'campaign').glob('*/rollout/history.jsonl'):
            history=[json.loads(line) for line in p.read_text().splitlines()]
            if any(r.get('tool')=='scalebfm_act' and r.get('execution') for r in history):
                executed.append(p.parent.parent.name)
        ended=phase=='episode_ended_review_pending'
        state='ended' if ended else 'action_executing' if phase=='action_executing' else 'inference_waiting'
        result=ROOT/'campaign'/self.episode_id/'result.json'
        terminal=json.loads(result.read_text()).get('terminal_kind') if ended and result.exists() else None
        web.update(schema_version=1,updated_at=row['at'],backend='MuJoCo',phase=phase,state=state,
            variant='source-aligned-apple-convex-close-robot-v2',episode=self.episode_id,execution_kind='policy',
            task_instance='Original tabletop apple',policy_state=phase,attempts=len(executed),physical_attempts=len(executed),
            registered_episodes=sum(1 for p in (ROOT/'campaign').glob('*/reset-provenance.json')),
            actions=self.actions,sim_s=t,simulated_seconds=t,metric_snapshot_at=row['at'],
            metric_snapshot=dict(episode=self.episode_id,actions=self.actions,simulated_seconds=t),
            terminal_kind=terminal,actor_running=not ended,human_feedback_used=True,needs_human=False,
            original_usd_joints=None,policy_route='codex-account-2/run.sh subscription gpt-6-astra/xhigh',
            live_evidence=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),observed_at=row['at'],state='ended' if ended else 'running'),
            next_step='完整等待策略；物理终态后独立审计。')
        web['tasks']['apple']['physical_attempts']=sum(n.startswith('apple-') for n in executed)
        if phase in ('physical_action_completed','physical_action_partial'):
            web.update(last_actual_progress_at=row['at'],last_progress_at=row['at'],progress_basis=phase)
        save(ROOT/'web-progress.json',web)
    def dispatch(self,name,args):
        before=float(self.backend.data.time) if self.backend else None
        if name=='scalebfm_act':self.progress('action_executing')
        try:
            return super().dispatch(name,args)
        finally:
            advanced=before is not None and self.backend is not None and float(self.backend.data.time)>before
            phase='physical_action_partial' if sys.exc_info()[0] is not None else 'physical_action_completed'
            self.progress(phase if advanced else 'inference_waiting')
