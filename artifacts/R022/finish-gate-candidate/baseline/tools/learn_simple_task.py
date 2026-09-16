"""One native SIMPLE manipulation episode using Astra/xhigh and task-local memory."""
import argparse
from functools import partial
import json
from pathlib import Path

from rsi.evaluator import SimpleNativeEvaluator
from rsi.simple_environment import create_native_task_backend
from rsi.simple_recording import simple_video
from rsi.simple_hand_geometry import HandGeometryProvider
from rsi.reference_sequence import CONTINUOUS_CONTRACT
from rsi.skill_learning import SkillMemory, usage_exhausted
from rsi.skill_transfer import prepare_hybrid_skill
from tools.learn_grasp_skill import LearningHost, ROOT, run_episode
from tools.learn_door_skill import PYTHON


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-id',required=True)
    p.add_argument('--task-spec',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,help='Explicit reset seed, e.g. resume an initialization failure after repair')
    p.add_argument('--continuous-chunks',action='store_true',
                   help='Enable the validated bounded UMI-4 multi-knot interface; supplies no gait')
    args=p.parse_args();root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
    audit=json.loads((ROOT/'artifacts/R018/audit_summary.json').read_text())
    if audit['audited_native_successes']<10:raise RuntimeError('Grasp gate incomplete')
    inventory=json.loads((ROOT/'artifacts/R019/task-inventory.json').read_text())
    entry=next(e for e in inventory['entries'] if e['id']==args.env_id)
    if not entry['native_sonic']:raise ValueError('This runner requires a native Sonic task')
    specification=json.loads(args.task_spec.read_text())
    if (specification['env_id']!=args.env_id or not specification['phase_guidance']
            or not specification['completion']):
        raise ValueError('Task specification must match environment and explain phases/completion')
    specification['robot_geometry_contract'] = (
        'Each observation includes robot-only distal finger mesh bounds and link origins '
        'in the corresponding wrist frame, computed from robot geometry and joint state. '
        'These are bounding ranges, not contact points, object information or a calibrated TCP. '
        'Do not reuse the prior cube scene capsule parameters for these native mesh fingers. '
        'finger_geometry.hand_collision_model also links a robot-only JSON sidecar with '
        'body-local convex collision surfaces for wrist/palm, proximal and distal links, '
        'plus current body_poses_world in each observation. Load selected bodies with Python '
        'instead of printing the large file. Mesh vertices already include geom-to-body '
        'transforms; combine them with the named current body pose. This is geometry, '
        'not observed contact, pressure, object pose or a calibrated grasp centre.')
    skill=root/'SKILL.md'
    sources=prepare_hybrid_skill(root,skill)
    memory=SkillMemory(root/'memory',skill)
    completed={p.parent.name:json.loads(p.read_text()) for p in root.glob('episode-*/result.json')}
    successes=sum(r['success'] for r in completed.values())
    number=max([int(p.name.split('-')[-1]) for p in root.glob('episode-*')],default=0)+1
    eid=f'episode-{number:04d}'
    seed=number if args.seed is None else args.seed
    task=(specification['instruction']+' Use only RGB, named robot state, camera calibration and allowed self-experience. '
        'No human demonstration or privileged object state. The host reports the native SIMPLE outcome. '
        'Continue until rollout_finished, then revise the skill. Physical budget 240 seconds; '
        'simulation pauses during reasoning and complete inference is awaited. '
        'Body PD uses the checkpoint profile; verify current responses before reusing experience.')
    if args.continuous_chunks:
        specification['continuous_chunk_contract']=CONTINUOUS_CONTRACT
        specification['known_interface_limits']=(
            'model_38000 UMI-4 at 50Hz; SIMPLE physics at 200Hz with checkpoint PD. '
            'Single-waypoint bounds remain in the observation. Multi-waypoint actions '
            'follow continuous_chunk_contract; future frames cross knots without '
            'intermediate arrival waits. Revalidate any experience against actual '
            'robot motion and RGB. Availability does not establish walking ability. '
            'Gripper fractions are not aperture/force readings. Physics pauses during reasoning.')
        specification['viewpoint_guidance']=(
            'When visibility or reach blocks progress, assess a bounded coordinated '
            'repositioning hypothesis using current RGB and public robot motion feedback. '
            'A failed isolated vertical foot target does not settle all coordinated '
            'timing/amplitude hypotheses. Check segment motion, support drift and the '
            'resulting view; final target arrival alone is not evidence of a step. '
            'No gait or successful task trajectory is supplied.')
        task+=' Bounded continuous chunks are enabled; read the current contract before planning.'
    def backend_factory():
        backend=create_native_task_backend(args.env_id,seed=seed)
        backend.continuous_chunks_enabled=args.continuous_chunks
        backend.scene_setup['continuous_chunk_contract']=(
            CONTINUOUS_CONTRACT if args.continuous_chunks else None)
        return backend
    factory=partial(LearningHost,task=task,
        backend_factory=backend_factory,
        evaluator_factory=SimpleNativeEvaluator,
        image_capture_factory=lambda b:simple_video(b,root/eid/'video'),
        geometry_provider=HandGeometryProvider(root/eid/'rollout/episode'),
        support_plane_z_m=None,max_episode_steps=12000,require_selection=True)
    old=ROOT/'artifacts/R018/campaign'
    result=run_episode(root/eid,memory,eid,successes,host_factory=factory,python=PYTHON,
        required_successes=1,task_specification=specification,skill_sources=sources,
        transfer_sources=[old/'memory/versions/0014.md',
            old/'memory/experience.jsonl',old/'episode-0437/rollout',old/'episode-0438/rollout',
            *[s['path'] for s in sources.values()]])
    completed[eid]=result
    (root/'progress.json').write_text(json.dumps({'task':args.env_id,'required_successes':1,
        'successes':sum(r['success'] for r in completed.values()),'episodes':completed},indent=2))
    print(json.dumps(result),flush=True)
    if usage_exhausted(result):raise SystemExit('Subscription usage exhausted; no automatic retry.')


if __name__=='__main__':main()
