"""One authorized Astra/xhigh SIMPLE push-open episode per invocation."""
import argparse
from functools import partial
import json
from pathlib import Path

from rsi.evaluator import DoorPushEvaluator
from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import simple_video
from rsi.simple_hand_geometry import HandGeometryProvider
from rsi.reference_sequence import CONTINUOUS_CONTRACT
from rsi.skill_learning import SkillMemory, usage_exhausted
from rsi.skill_transfer import prepare_hybrid_skill
from tools.learn_grasp_skill import LearningHost, ROOT, run_episode

PYTHON = '/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/.venv/bin/python'
TASK = ('Visually locate the closed door, approach as needed, and use either hand to '
        'PUSH it OPEN away from yourself, at least 30 degrees relative to its starting '
        'position. Keep it open for at least one simulated second and remain standing. '
        'This is the SIMPLE door asset003 push-open variant; do not perform the original '
        'close-door instruction. Do not pull the handle. Use only RGB, named robot '
        'state, camera calibration and your own allowed public experience. No human '
        'demonstration or privileged object/hinge/contact state is available. The host '
        'verifies hand contact, opening, dwell and standing. Continue until the host '
        'reports rollout_finished, then revise the skill from this episode. '
        'Physical budget: 240 seconds. Full model reasoning is awaited.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pd-profile', choices=('native','checkpoint'), default='checkpoint')
    parser.add_argument('--continuous-chunks', action='store_true',
                        help='Enable validated bounded multi-knot UMI-4 interface, without supplying a gait')
    parser.add_argument('--door-frame-override', action='store_true',
                        help='Use validated exact asset003 frame collision decomposition')
    args = parser.parse_args(); root = args.output.resolve(); root.mkdir(parents=True, exist_ok=True)
    grasp = json.loads((ROOT/'artifacts/R018/audit_summary.json').read_text())
    if grasp['audited_native_successes'] < 10:
        raise RuntimeError('Ten audited independent grasp successes required before SIMPLE')
    sources=prepare_hybrid_skill(root,ROOT/'skills/loco-manip-simple/SKILL.md')
    specification=json.loads((ROOT/'ref/tasks/simple-push-door.json').read_text())
    specification['robot_geometry_contract'] = (
        'finger_geometry contains distal bounds and hand_collision_model: a robot-only '
        'JSON sidecar of body-local wrist/palm/proximal/distal collision surfaces, with '
        'current body_poses_world refreshed in each observation. Read selected body '
        'geometry using Python; do not dump the large sidecar. Mesh vertices already '
        'include geom-to-body transforms. Geometry is not contact truth or calibrated TCP.')
    memory = SkillMemory(root/'memory', ROOT/'skills/loco-manip-simple/SKILL.md')
    completed = {p.parent.name:json.loads(p.read_text()) for p in root.glob('episode-*/result.json')}
    successes = sum(r['success'] for r in completed.values())
    number = max([int(p.name.split('-')[-1]) for p in root.glob('episode-*')], default=0)+1
    episode_id = f'episode-{number:04d}'
    task = TASK+f' This episode uses the {args.pd_profile} body PD profile; controller configuration may differ from earlier public experience, so revalidate measured response.'
    if args.continuous_chunks:
        specification['continuous_chunk_contract'] = CONTINUOUS_CONTRACT
        specification['known_interface_limits'] = (
            'model_38000 UMI-4 at 50Hz; SIMPLE physics at 200Hz with checkpoint PD. '
            'Single waypoints retain observed named limits. Multi-waypoint actions follow '
            'continuous_chunk_contract: all knots are validated before execution, future '
            'samples cross knots, no intermediate wait for arrival. Use fresh visual/proprio '
            'evidence to assess actual motion; interface availability is not a walking skill.')
        task += ' A new bounded continuous-chunk interface is enabled; read the task specification and initial observation contract before planning. Prior one-waypoint limits do not describe multi-waypoint chunks.'
    if args.door_frame_override:
        specification['environment_revision'] = {
            'id': 'asset003-exact-frame-four-boxes-v1',
            'description': 'Fixed-frame collision representation corrected to match its original visible shape. Visual geometry, moving-door physics, task goal and control interface unchanged. Revalidate prior contact-specific hypotheses after reset; no successful action is supplied.'}
    def backend_factory():
        backend = create_closed_door_backend(seed=number, push_open=True, pd_profile=args.pd_profile,
                                            door_frame_override=args.door_frame_override)
        backend.continuous_chunks_enabled = args.continuous_chunks
        backend.scene_setup['continuous_chunk_contract'] = (CONTINUOUS_CONTRACT if args.continuous_chunks else None)
        return backend
    host_factory = partial(LearningHost, task=task,
        backend_factory=backend_factory,
        evaluator_factory=DoorPushEvaluator,
        image_capture_factory=lambda b:simple_video(b, root/episode_id/'video', door_audit=True),
        geometry_provider=HandGeometryProvider(root/episode_id/'rollout/episode'),
        support_plane_z_m=None, max_episode_steps=12000,
        require_selection=True)
    old = ROOT/'artifacts/R018/campaign'
    result = run_episode(root/episode_id, memory, episode_id, successes,
        host_factory=host_factory, python=PYTHON, required_successes=10,
        task_specification=specification, skill_sources=sources,
        transfer_sources=[old/'memory/versions/0014.md', old/'memory/experience.jsonl',
                          old/'episode-0437/rollout', old/'episode-0438/rollout',
                          *[s['path'] for s in sources.values()]])
    completed[episode_id] = result
    (root/'progress.json').write_text(json.dumps({'task':'push_door',
        'successes':sum(r['success'] for r in completed.values()),
        'required_successes':10, 'episodes':completed}, indent=2))
    print(json.dumps(result), flush=True)
    if usage_exhausted(result):
        raise SystemExit('Subscription usage exhausted; no retry, paid API or fallback.')


if __name__ == '__main__': main()
