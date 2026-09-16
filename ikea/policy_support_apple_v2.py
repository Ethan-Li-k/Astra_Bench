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
FROZEN=ROOT/'runtime-apple-v2'
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
            sim_s=t,independent_reset=self.backend is not None,physics_paused=True,finished=self.finished)
        save(ROOT/'actor-progress.json',row)
        web=json.loads((ROOT/'web-progress.json').read_text());web.update(phase=phase,execution_kind='policy',
            task_instance='Original tabletop apple',policy_state=phase,attempts=sum(1 for p in (ROOT/'campaign').glob('*/reset-provenance.json')),
            actions=self.actions,sim_s=t,next_step='等待完整推理并执行下一安全动作；本回合自然终态后审查。')
        if phase=='physical_action_completed':web['last_actual_progress_at']=row['at']
        save(ROOT/'web-progress.json',web)
    def dispatch(self,name,args):
        packet=super().dispatch(name,args)
        self.progress('physical_action_completed' if name=='scalebfm_act' else 'inference_waiting')
        return packet

