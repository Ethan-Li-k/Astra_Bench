"""One isolated learning episode, fully await second-account Astra/xhigh."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from ground_task import ROOT,create_backend,GroundEvaluator
from rsi.episode_video import EpisodeVideo
from rsi.skill_learning import SkillMemory,usage_exhausted
from tools.learn_grasp_skill import LearningHost,run_episode,finger_geometry

TASK=json.loads((ROOT/'task_specification.json').read_text())

def status_update(**values):
    path=ROOT/'status.json';s=json.loads(path.read_text());s.update(values)
    p=path.with_suffix('.tmp');p.write_text(json.dumps(s,indent=2,ensure_ascii=False));p.replace(path)

class GroundHost(LearningHost):
    def __init__(self,output,memory,episode_id,successes):
        super().__init__(output,memory,episode_id,successes,task=TASK['goal'],
            backend_factory=create_backend,evaluator_factory=lambda:GroundEvaluator(output/'host_audit'),
            image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='Astra/xhigh account 2 | GROUND TO TABLE',
                extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist(),
                                        'ctrl':sim.data.ctrl.tolist()}),
            support_plane_z_m=None,geometry_provider=finger_geometry,max_episode_steps=9000,
            require_selection=True)

    def dispatch(self,name,arguments):
        result=super().dispatch(name,arguments)
        if name=='scalebfm_act':
            route_path=self.output/'account_route_verified.json'
            route=json.loads(route_path.read_text())
            if route['first_physical_action'] is None:
                route['first_physical_action']={'command_id':self.backend.status().get('command_id'),
                    'status':self.backend.status().get('status'),'sim_s':float(self.backend.data.time)}
                route_path.write_text(json.dumps(route,indent=2))
        if self.harness:
            audit=self.harness.evaluator.audit.result()
            status_update(current_episode=self.episode_id,actions_in_current_episode=self.actions,
                physics_sim_s=float(self.backend.data.time)-self.episode_start_sim_s,
                phase_results=audit['phase_results'],overall_success=audit['overall_success'],
                phase='learning_episode' if not self.finished else 'awaiting_complete_model_review',
                latest_video=str(self.output/'video/episode.mp4'),
                latest_audit=str(self.output/'host_audit/evaluation.json'),
                model_wait='Simulation paused while Astra/xhigh reasons; no inference deadline',
                updated_at_unix=time.time())
        return result

    def close(self):
        super().close()
        if self.harness:self.harness.evaluator.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--episode',required=True);args=p.parse_args()
    # Mandatory user-update read before every new round, never actor input.
    update=Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_bytes()
    root=ROOT/'campaign';root.mkdir(exist_ok=True)
    (root/(args.episode+'-user-update.sha256')).write_text(hashlib.sha256(update).hexdigest()+'\n')
    if (root/'quota_pause.json').exists():raise RuntimeError('usageLimitExceeded pause present; no retry')
    preflight=json.loads((ROOT/'artifacts/preflight-02/layout_collision_audit.json').read_text())
    assert not preflight['new_layout_penetrations']
    memory=SkillMemory(root/'memory',ROOT/'skills/loco-manip-direct/SKILL.md')
    sources={}
    for key,path in [('shared_core',ROOT/'provenance/originals/skills/loco-manip-core/SKILL.md'),
                     ('own_tabletop_grasp_skill',ROOT/'provenance/originals/skills/loco-manip-direct/SKILL.md'),
                     ('task_skill',memory.skill)]:
        sources[key]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    sources['tabletop_438_public']={'path':'/home/galbot/lizekai/RSI/artifacts/R018/campaign/episode-0438/rollout',
        'boundary':'Only public rollout observations/actions; no host audits. Old tabletop success cannot count here.'}
    with (ROOT/'DECISIONS.md').open('a') as f:
        f.write(f'\n## {args.episode}：视觉策略独立重置\n当前问题：站立预检通过，移动及地面拾取未验证。\n总目标：地面红块经真实移动、抓持、运输后放桌稳定释放。\n不可重犯的错误：不重复无依据脚点平移，不把开发诊断喂给 actor，不截断推理、不跨账号。\n决定：按当前短技能运行一轮自主视觉探索，完整等待复盘；随后以公开原因和独立审计选择下一实验。\n')
    status_update(phase='starting_learning_episode',setting_manifest=str(ROOT/'setting_manifest.json'),
                  current_episode=args.episode,blocker=None,next_step='Await real actor actions and complete evidence-backed review')
    result=run_episode(root/args.episode,memory,args.episode,0,host_factory=GroundHost,
                      required_successes=1,transfer_sources=[v['path'] for v in sources.values()],
                      task_specification=TASK,skill_sources=sources)
    evalpath=root/args.episode/'host_audit/evaluation.json'
    audit=json.loads(evalpath.read_text()) if evalpath.exists() else None
    result.update(backend='MuJoCo',phase_results=audit['phase_results'] if audit else {},
                  overall_success=bool(audit and audit['overall_success']),
                  simulation_pauses_during_planning=True,learning_not_frozen_eval=True)
    (root/args.episode/'result.json').write_text(json.dumps(result,indent=2))
    s=json.loads((ROOT/'status.json').read_text());attempts=s['attempts']+[result]
    exhausted=usage_exhausted(result)
    if exhausted:(root/'quota_pause.json').write_text(json.dumps(result,indent=2))
    status_update(attempts=attempts,phase='quota_paused' if exhausted else 'episode_complete_awaiting_supervisor_iteration',
                  blocker='usageLimitExceeded' if exhausted else result.get('error'),
                  next_step='Stop automatic retries and preserve progress' if exhausted else 'Supervisor review failure evidence and select changed hypothesis',
                  overall_success=result['overall_success'])
    print(json.dumps({'event':'ground_episode_complete',**result}),flush=True)

if __name__=='__main__':main()
