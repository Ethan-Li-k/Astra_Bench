"""One native SIMPLE manipulation episode using Astra/xhigh and task-local memory."""
import argparse
import datetime
from functools import partial
import hashlib
import json
from pathlib import Path

from rsi.evaluator import SimpleNativeEvaluator
from rsi.simple_placement import SimplePlacementEvaluator, PLACEMENT_CONTRACT
from rsi.simple_environment import create_native_task_backend, DOOR_ENV
from rsi.simple_recording import simple_video
from rsi.simple_hand_geometry import HandGeometryProvider
from rsi.reference_sequence import CONTINUOUS_CONTRACT
from rsi.skill_learning import SkillMemory, usage_exhausted
from rsi.skill_transfer import prepare_hybrid_skill
from rsi.skill_release import (ReleasedSkillMemory, runtime_instructions, execution_profile,
    verify_release, verify_load_configuration, select_sources, digest)
from tools.learn_grasp_skill import LearningHost, ROOT, run_episode
from tools.learn_door_skill import PYTHON
from tools.audit_simple_campaigns import episode_status, memory_success_review


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-id',required=True)
    p.add_argument('--task-spec',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,help='Explicit reset seed, e.g. resume an initialization failure after repair')
    p.add_argument('--continuous-chunks',action='store_true',
                   help='Enable the validated bounded UMI-4 multi-knot interface; supplies no gait')
    p.add_argument('--verified-placement',action='store_true',
                   help='Explicit box-placement completion gate; native rewards remain recorded unchanged')
    p.add_argument('--door-frame-override',action='store_true',
                   help='Reviewed CloseDoor frame collision repair; native layout and reward preserved')
    p.add_argument('--human-feedback',type=Path,action='append',default=[],
                   help='Explicit user semantic feedback JSON, frozen into this episode and counted separately')
    p.add_argument('--skill-release', type=Path, required=True,
                   help='Central immutable release; never a local actor proposal')
    p.add_argument('--release-sha256', required=True)
    p.add_argument('--phase', choices=('learning','stability','evaluation'), default='learning')
    p.add_argument('--evaluation-steps', type=int)
    p.add_argument('--candidate-registration', type=Path,
                   help='Required pre-registration of complete inputs/reset order for stability/evaluation')
    args=p.parse_args()
    profile=execution_profile(args.phase,args.evaluation_steps)
    # Memory isolation is implemented here; full freeze admission remains explicit.
    # Until the supervisor supplies and verifies complete native asset/control pins,
    # no stability/evaluation may silently use this learning-only integration.
    if args.phase != 'learning':
        raise ValueError('Full stability/evaluation registration integration remains pending; no implicit admission')
    if args.door_frame_override and args.env_id != DOOR_ENV:
        raise ValueError('Native frame repair is scoped to CloseDoor')
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
    audit=json.loads((ROOT/'artifacts/R018/audit_summary.json').read_text())
    if audit['audited_native_successes']<10:raise RuntimeError('Grasp gate incomplete')
    inventory=json.loads((ROOT/'artifacts/R019/task-inventory.json').read_text())
    entry=next(e for e in inventory['entries'] if e['id']==args.env_id)
    if not entry['native_sonic']:raise ValueError('This runner requires a native Sonic task')
    specification=json.loads(args.task_spec.read_text())
    if args.door_frame_override:
        specification['completion_contract']={
            'id':'native-close-door-exact-frame-v1', 'scope':DOOR_ENV,
            'native_reward_unchanged':True,
            'collision_revision':'asset003-exact-frame-four-boxes-v1',
            'note':'Original close-door task layout and reward; corrected fixed-frame collision representation. Not the unmodified native benchmark or the push-open task.'}
    if args.verified_placement:
        if args.env_id != PLACEMENT_CONTRACT['scope']:
            raise ValueError('Verified placement is scoped to the reviewed box task')
        specification['completion_contract']=PLACEMENT_CONTRACT
        specification['completion']=[
            'Native contact alone no longer ends this explicitly strengthened task variant. '
            'Acquire and retain an unsupported lift, then transport, release and observe '
            'stable support in/on the intended container. Native reward is recorded unchanged.',
            'Only host-verified completion, safety/system termination or physical budget ends '
            'the rollout. Final placement geometry still receives independent supervisor audit. '
            'Stop when rollout_finished and complete skill_update.']
    if (specification['env_id']!=args.env_id or not specification['phase_guidance']
            or not specification['completion']):
        raise ValueError('Task specification must match environment and explain phases/completion')
    if args.human_feedback:
        sources=[]
        for path in args.human_feedback:
            raw=path.read_bytes();feedback=json.loads(raw)
            if not all(feedback.get(k) for k in ('case_id','user_original_words','agent_operational_rule','scope')):
                raise ValueError('Human feedback requires original words, scoped rule and source case')
            sources.append({'path':str(path.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),
                            'feedback':feedback})
        specification['human_feedback']={'used':True,'demonstration_used':False,
            'adopted_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':sources,
            'evidence_status':'Human-proposed semantic/planning rule; physical success remains to be verified.'}
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
    completed={p.parent.name:json.loads(p.read_text()) for p in root.glob('episode-*/result.json')}
    # A native contact/height trigger may fail the requested task semantics.
    # Preserve raw outcomes, but only completed host reviews earn task credit.
    successes=sum(episode_status(root/name)['audited_task_success'] for name in completed)
    number=max([int(p.name.split('-')[-1]) for p in root.glob('episode-*')],default=0)+1
    eid=f'episode-{number:04d}'
    seed=number if args.seed is None else args.seed
    runtime=runtime_instructions(ROOT/'tools/learn_grasp_skill.py',ROOT/'rsi/codex_app_server.py')
    release=verify_release(args.skill_release,args.release_sha256,args.env_id,runtime)
    bindings={'task_spec_sha256':digest(args.task_spec),
              'continuous_chunks':args.continuous_chunks,
              'verified_placement':args.verified_placement,
              'door_frame_override':args.door_frame_override,
              'human_feedback_sha256':sorted(digest(p) for p in args.human_feedback)}
    verify_load_configuration(release,args.env_id,bindings)
    for relative, expected in release['runtime_code_hashes'].items():
        if digest(ROOT/relative) != expected:
            raise ValueError('Unreviewed runtime/control code: '+relative)
    task_release=release['tasks'][args.env_id]
    memory=ReleasedSkillMemory(args.skill_release,args.release_sha256,args.env_id,
                               root/'skill-proposals'/eid,runtime)
    index=json.loads((args.skill_release/'public/atomic-index.json').read_text())
    selected=select_sources(index,args.env_id,task_release['source_phases'],
                            index['control_contract'],bool(args.human_feedback))
    sources={row['id']:{'path':str((args.skill_release/'public'/row['path']).resolve()),
              'sha256':digest(args.skill_release/'public'/row['path']),
              'scope':'published_conditional_public_source',
              'applicability':row['preconditions'],'when_not_to_use':row['when_not_to_use']}
             for row in selected}
    evidence=[str((args.skill_release/'public'/item['path']).resolve())
              for row in selected for item in row['public_evidence'] if 'path' in item]
    # Receipt is admission only. run_episode/result and independent audit prove actual use.
    receipt={'release_sha256':args.release_sha256,'env_id':args.env_id,'episode':eid,
             'seed':seed,'bindings':bindings,'execution_profile':profile,
             'skill_sha256':digest(memory.skill),'selected_source_ids':list(sources),
             'actor_started':False,'source_read_set':'published immutable files only'}
    (root/'release-load-receipts').mkdir(exist_ok=True)
    with (root/'release-load-receipts'/f'{eid}.json').open('x') as stream:
        json.dump(receipt,stream,indent=2)
    specification['execution_profile']=profile
    specification['known_interface_limits'] += (' Learning-horizon-v1 overrides historical cumulative-budget text: checkpoints do not terminate; single-action limits, native terminal, safety, user pause and unrecoverable errors remain binding.')
    task=(specification['instruction']+' Use only RGB, named robot state, camera calibration and allowed self-experience. '
        'No human demonstration or privileged object state. The host reports the native SIMPLE outcome. '
        'Continue until rollout_finished, then submit a proposal to the isolated skill sink. Learning-horizon-v1 has no cumulative step/time/turn cutoff; '
        'simulation pauses during reasoning and complete inference is awaited. '
        'Body PD uses the checkpoint profile; verify current responses before reusing experience.')
    if args.human_feedback:
        task+=' This episode also uses explicitly supplied human semantic/planning feedback. Read task_specification.human_feedback before acting; it is not an action demonstration and this run is counted separately from autonomous Direct.'
    if args.verified_placement:
        task+=' This run explicitly strengthens task completion beyond the recorded native contact trigger. Read completion_contract; raw native success is not sufficient.'
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
        backend=create_native_task_backend(args.env_id,seed=seed,
                                          door_frame_override=args.door_frame_override)
        if profile['id']=='learning-horizon-v1' and getattr(backend.env.spec,'max_episode_steps',None) is not None:
            raise ValueError('Native TimeLimit needs an explicitly reviewed extension; do not ignore truncation')
        backend.scene_setup['execution_profile']=profile
        backend.scene_setup['central_skill_release']={'sha256':args.release_sha256,'release_id':release['release_id']}
        backend.scene_setup['human_feedback_used']=bool(args.human_feedback)
        backend.scene_setup['human_demonstration_used']=False
        if args.door_frame_override:
            backend.scene_setup['completion_contract']=specification['completion_contract']
        if args.verified_placement:
            backend.scene_setup['completion_contract']=PLACEMENT_CONTRACT
        if args.human_feedback:
            backend.scene_setup['human_feedback_provenance']=specification['human_feedback']
        backend.continuous_chunks_enabled=args.continuous_chunks
        backend.scene_setup['continuous_chunk_contract']=(
            CONTINUOUS_CONTRACT if args.continuous_chunks else None)
        return backend
    video_label=('Astra/xhigh | human semantic feedback | no motion demonstration'
                 if args.human_feedback else 'Astra/xhigh Direct | SIMPLE | no demonstration')
    if args.verified_placement:
        video_label+=' | verified placement variant'
    if args.door_frame_override:
        video_label+=' | native closing objective, repaired frame collision'
    factory=partial(LearningHost,task=task,
        backend_factory=backend_factory,
        evaluator_factory=SimplePlacementEvaluator if args.verified_placement else SimpleNativeEvaluator,
        image_capture_factory=lambda b:simple_video(b,root/eid/'video',label=video_label),
        geometry_provider=HandGeometryProvider(root/eid/'rollout/episode'),
        support_plane_z_m=None,max_episode_steps=profile['max_episode_steps'],
        execution_profile=profile,require_selection=True)
    result=run_episode(root/eid,memory,eid,successes,host_factory=factory,python=PYTHON,
        required_successes=1,task_specification=specification,skill_sources=sources,
        transfer_sources=[*[s['path'] for s in sources.values()],*evidence])
    completed[eid]=result
    (root/'progress.json').write_text(json.dumps({'task':args.env_id,'required_successes':1,
        'successes':sum(episode_status(root/name)['audited_task_success'] for name in completed),
        'successes_basis':'independently host-audited task success; newest episode review may be pending',
        'complete_host_successes':sum(r['success'] for r in completed.values()),
        'completion_contracts':{name:episode_status(root/name)['completion_contract'] for name in completed},
        'episodes':completed},indent=2))
    print(json.dumps(result),flush=True)
    if usage_exhausted(result):raise SystemExit('Subscription usage exhausted; no automatic retry.')


if __name__=='__main__':main()
