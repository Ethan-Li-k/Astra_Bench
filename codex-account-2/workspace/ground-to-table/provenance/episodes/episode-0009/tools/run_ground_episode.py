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
CONTINUOUS_ENABLED=False

def status_update(**values):
    path=ROOT/'status.json';s=json.loads(path.read_text());s.update(values)
    p=path.with_suffix('.tmp');p.write_text(json.dumps(s,indent=2,ensure_ascii=False));p.replace(path)

class GroundHost(LearningHost):
    def __init__(self,output,memory,episode_id,successes):
        super().__init__(output,memory,episode_id,successes,task=TASK['goal'],
            backend_factory=lambda:create_backend(continuous=CONTINUOUS_ENABLED),evaluator_factory=lambda:GroundEvaluator(output/'host_audit'),
            image_capture_factory=lambda b:EpisodeVideo(b,output/'video',label='Astra/xhigh account 2 | GROUND TO TABLE',
                extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist(),
                    'ctrl':sim.data.ctrl.tolist(),
                    'joint_names':sim.adapter.metadata['joint_names'],
                    'normalized_action':sim.adapter.action_history[0,-1].tolist(),
                    'joint_target_before_wrist_pi':(sim.adapter._default_qpos_p+sim.adapter.action_history[0,-1]*sim.adapter._action_scale_p).tolist(),
                    'wrist_pi_torque_nm':sim.wrist_pi_tau.tolist()}),
            support_plane_z_m=None,geometry_provider=finger_geometry,max_episode_steps=9000,
            require_selection=True)

    def dispatch(self,name,arguments):
        result=super().dispatch(name,arguments)
        if name=='loco_start' and self.backend:
            (self.output/'reset_provenance.json').write_text(json.dumps(self.backend.reset_provenance,indent=2))
        if name=='scalebfm_act' and self.actions>0:
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
    global CONTINUOUS_ENABLED
    p=argparse.ArgumentParser();p.add_argument('--episode',required=True)
    p.add_argument('--continuous',action='store_true');args=p.parse_args()
    CONTINUOUS_ENABLED=args.continuous
    if CONTINUOUS_ENABLED:
        from rsi.reference_sequence import CONTINUOUS_CONTRACT
        validation=json.loads((ROOT/'artifacts/continuous-original-g1-01/result.json').read_text())
        if validation['stop_reason'] is not None or validation['audit']['invalid']:
            raise RuntimeError('Local continuous interface validation failed')
        feedback=json.loads((ROOT/'artifacts/public-motion-feedback-03/result.json').read_text())
        if feedback['max_qpos_delta'] >= 1e-9 or not feedback['only_head_and_right_wrist'] or not feedback['control_feedback_present_and_aligned'] or not feedback['robot_com_present']:
            raise RuntimeError('Public motion feedback purity validation failed')
        atomic=json.loads((ROOT/'artifacts/continuous-atomic-01/result.json').read_text())
        if atomic['stopped'] or atomic['pending_reference'] or atomic['duration_s']!=3.:
            raise RuntimeError('Exact3s transaction validation failed')
        TASK['control_interface_version']='ground-UMI4-continuous-v2.4-robot-com'
        TASK['infrastructure_update']='The prior episode0005 accepted reference then rejected gripper duration near3s, leaving a pending command. This host defect is repaired: total duration is summed without subtracting absolute timestamps, all gripper parameters validate before commit, and exceptional partial commits end with a nonretryable review receipt. Actual3s physical boundary validation passed. The last proposed bilateral candidate in episode0005 was never physically executed; do not record it as a motion failure. Current reset is independent; use your own prior public evidence only.'
        TASK['continuous_chunk_contract']=CONTINUOUS_CONTRACT
        TASK['interface_update']='The live continuous reference contract is newly available. Earlier single-waypoint limits remain for a one-waypoint action; they do not limit explicitly enabled continuous chunks. Reconsider the next hypothesis using this changed capability. Generate your own references from current RGB and proprioception; no gait trajectory or hidden diagnostic state is supplied.'
        TASK['motion_feedback']='Continuous actions return motion_evidence: a 50Hz named robot/pelvis/ankle pose trace and calibrated head/right-wrist RGB at waypoint times. Foot geometry now includes exact robot-only capsule endpoints/radii in ankle frames. robot_control_feedback logs this action\'s actual six future four-point world input frames, named model joint targets and additive WristPI torque, aligned to the preceding 20ms physical interval. This is own command feedback, not contact sensing or a demonstration. The full measured pelvis quaternion anchors the adapter transform. Use trace timestamps and command IDs; the first sample belongs to the preceding held command. Pose/FK estimates are not contact truth.'
        TASK['motion_feedback']+=' robot_com_model is a new robot-only center-of-mass estimate from the original known inertial model and measured root/joint FK; it excludes objects/carried loads. Use it with foot geometry and motion trends instead of assuming pelvis location alone determines balance. A static COM projection is not proof of dynamic stability.'
    TASK['mandatory_user_update']='Read and hashed by supervisor before this round; do not search supervisor-only files.'
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
    previous=ROOT/'campaign/episode-0005/rollout'
    if previous.is_dir():
        sources['own_ground_0005_public']={'path':str(previous),
            'boundary':'Own previous public RGB/proprioception, actions, notes and failure receipts. No host audit or app-server/internal files.'}
    completed=sorted((ROOT/'campaign').glob('episode-*/result.json'))
    if completed:
        last=completed[-1].parent
        sources['own_latest_ground_public']={'path':str(last/'rollout'),
            'boundary':'Most recent own completed physical episode public experience. Revalidate current reset; no host audit or internal files.'}
    posture=ROOT/'campaign/memory/posture_phenomenon.json'
    if posture.exists():
        sources['own_posture_response']={'path':str(posture),
            'boundary':'Mechanism index derived only from own public failed episode0001. Not a verified floor-reaching skill; listed source public observations/actions may be read.'}
    balance=ROOT/'campaign/memory/balance_episode-0007.json'
    if balance.exists():
        sources['own_public_balance_0007']={'path':str(balance),
            'boundary':'Robot-only inertial/FK estimates reconstructed from own public robot observations, with four-point reconstruction error0. No host truth; geometric ankle midpoint is not measured support.'}
    with (ROOT/'DECISIONS.md').open('a') as f:
        f.write(f'\n## {args.episode}：视觉策略独立重置\n当前问题：历史独立行走已有证据；当前重置仍需重新执行，地面拾取未达成。\n总目标：地面红块经真实移动、抓持、运输后放桌稳定释放。\n不可重犯的错误：不重复无依据脚点平移，不把开发诊断喂给 actor，不截断推理、不跨账号。\n决定：按当前短技能运行一轮自主视觉探索，完整等待复盘；随后以公开原因和独立审计选择下一实验。\n')
    status_update(phase='starting_learning_episode',setting_manifest=str(ROOT/'setting_manifest.json'),
                  current_episode=args.episode,blocker=None,next_step='Await real actor actions and complete evidence-backed review')
    # Save the exact implementation before a new process imports it. The source
    # archive is supervisor-only, separate from the actor's public evidence.
    implementation=ROOT/'provenance/episodes'/args.episode
    implementation.mkdir(parents=True,exist_ok=False)
    runtime_sources=[ROOT/'ground_task.py',ROOT/'task_specification.json',ROOT/'tools/run_ground_episode.py',ROOT/'tools/learn_grasp_skill.py']+list((ROOT/'rsi').glob('*.py'))
    for source in runtime_sources:
        target=implementation/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
    manifest=json.loads((ROOT/'setting_manifest.json').read_text())
    manifest['control_interface_version']=TASK.get('control_interface_version','ground-single-waypoint-v1')
    manifest['continuous_chunks_enabled']=CONTINUOUS_ENABLED
    manifest['public_observation_extensions']=TASK.get('motion_feedback')
    if CONTINUOUS_ENABLED:
        manifest['continuous_chunk_contract']=TASK['continuous_chunk_contract']
        manifest['continuous_validation_scope']='Original G1: stable interface execution, no verified foot unloading; no imported gait or task success claim.'
    if 'implementation_hashes' in manifest:
        manifest['base_snapshot_hashes']=manifest.pop('implementation_hashes')
    manifest['episode_runtime_hashes']={str(source):hashlib.sha256(source.read_bytes()).hexdigest() for source in runtime_sources}
    (implementation/'setting_manifest.json').write_text(json.dumps(manifest,indent=2))
    status_update(setting_manifest=str(implementation/'setting_manifest.json'))
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
