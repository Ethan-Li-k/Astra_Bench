"""Paired timing diagnostics, no GPT, no demonstration or task-success credit."""
import argparse
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
import traceback

import mujoco
import numpy as np
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose
from rsi.reference_sequence import ReferenceSequence
from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import simple_video


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--locomotion', action='store_true',
                        help='Separate feasibility probe with alternating steps and measured full-body start; not a single-factor timing comparison')
    parser.add_argument('--pelvis-reference', action='store_true',
                        help='Diagnostic only: enable trained VR-5 mask and explicit robot pelvis support transfer')
    parser.add_argument('--swing-height', type=float, default=.06,
                        help='Locomotion probe only: change swing height, leaving timing and other coordinates fixed')
    parser.add_argument('--production-interface', action='store_true',
                        help='Execute through actual bounded continuous-chunk API, with no monkeypatch')
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    if args.pelvis_reference and not args.locomotion:
        parser.error('--pelvis-reference requires --locomotion')
    if not 0 < args.swing_height <= .22: parser.error('Diagnostic swing height must be in (0, .22]')
    if args.production_interface and (not args.locomotion or args.pelvis_reference):
        parser.error('Production interface probe requires UMI-4 locomotion mode')
    args.output.mkdir(parents=True, exist_ok=False)
    summary = []
    for coordinated in ((True,) if args.locomotion else (False, True)):
        for timing in (('continuous',) if args.locomotion else ('wait_each', 'continuous')):
            name = ('coordinated' if coordinated else 'foot_only')+'-'+timing
            folder = args.output/name; folder.mkdir()
            b = video = None
            row = {'case':name, 'gpt_calls':0, 'task_success_credit':False,
                   'actor_access':False, 'seed':args.seed, 'timing':timing,
                   'production_interface':args.production_interface}
            try:
                b = create_closed_door_backend(seed=args.seed, pd_profile='checkpoint', push_open=True)
                row['initial_qpos_qvel_sha256'] = hashlib.sha256(
                    b.data.qpos.tobytes()+b.data.qvel.tobytes()).hexdigest()
                video = simple_video(b, folder/'video', label='Reference timing diagnostic | no GPT | not a task attempt')
                initial = b.observe()
                base = FourPointPose.from_mapping(initial['four_point_reference_world'])
                measured = FourPointPose.from_mapping(initial['four_point_world'])
                poses = [base.copy()]
                shift = base.copy()
                if coordinated: shift.positions[:2, 1] -= .03
                poses.append(shift)
                raised = shift.copy(); raised.positions[2] = measured.positions[2]+[.015, 0, .06]
                poses.append(raised)
                landed = shift.copy(); landed.positions[2] = measured.positions[2]+[.03, 0, 0]
                poses.append(landed)
                end = landed.copy(); end.positions[:2] = base.positions[:2]+[.015, 0, 0]
                poses.append(end)
                if args.locomotion:
                    poses = [measured.copy() for _ in range(5)]
                    for i, shift_x in enumerate((0., .03, .06, .12, .18)):
                        poses[i].positions[:2, 0] += shift_x
                    poses[1].positions[2] += [.06, 0, args.swing_height]
                    for i in (2, 3, 4): poses[i].positions[2, 0] += .12
                    poses[3].positions[3] += [.12, 0, args.swing_height]
                    poses[4].positions[3, 0] += .24
                    row['scope'] = 'Synthetic controller feasibility probe only; different amplitude/start/path, not causal ablation or actor demonstration'
                if args.pelvis_reference:
                    pelvis_start = b.data.xpos[b.adapter.body_ids[0]].copy()
                    pelvis_quat = b.data.xquat[b.adapter.body_ids[0]].copy()
                    pelvis_offsets = np.array([[0, 0, 0], [.03, -.08, 0], [.06, -.08, 0],
                                               [.12, .08, 0], [.18, 0, 0]])
                    for pose, delta in zip(poses, pelvis_offsets):
                        pose.positions[:2, 1] += delta[1]
                    b.adapter.mode[0, 0] = 1.
                    b.adapter.mode_mapping = np.concatenate([
                        *[np.repeat(b.adapter.mode[0], d) for d in (3,3,6,6)],
                        np.ones(1,dtype=np.float32)])[None].astype(np.float32)
                    row['diagnostic_mode'] = 'VR-5; full pelvis-frame anchor retained per checkpoint interface'
                    row['pelvis_offsets_m'] = pelvis_offsets.tolist()
                limit = .3 if args.locomotion else .08
                b.translation_limit_m_by_link = {n:limit for n in FOUR_POINT_NAMES}
                row['diagnostic_translation_limit_m'] = limit
                row['knots'] = [p.to_mapping() for p in poses]
                row['segment_duration_s'] = .5
                row['initial_measured'] = measured.to_mapping()
                position_names = FOUR_POINT_NAMES[:3] if coordinated else (FOUR_POINT_NAMES[2],)
                if args.locomotion: position_names = FOUR_POINT_NAMES
                # Only active reference components change, matching the standard path.
                if not coordinated:
                    poses[-1].positions[:2] = base.positions[:2]
                    row['knots'] = [p.to_mapping() for p in poses]
                start = float(b.data.time)
                records = []
                plane=set(np.flatnonzero(b.model.geom_type==mujoco.mjtGeom.mjGEOM_PLANE))
                feet=[]
                for bid in b.adapter.body_ids[b.four[2:]]:
                    descendants={int(bid)}
                    for i in range(b.model.nbody):
                        if int(b.model.body_parentid[i]) in descendants: descendants.add(i)
                    feet.append(set(np.flatnonzero(np.isin(b.model.geom_bodyid,list(descendants)))))
                detached=[0,0];longest=[0,0]
                def tick():
                    b.tick(); video.record_tick('diagnostic_only')
                    for side,geoms in enumerate(feet):
                        contact=any(((c.geom1 in geoms and c.geom2 in plane) or
                                     (c.geom2 in geoms and c.geom1 in plane)) and c.dist<=.0001
                                    for c in b.data.contact)
                        detached[side]=0 if contact else detached[side]+1
                        longest[side]=max(longest[side],detached[side])
                    records.append({'sim_s':float(b.data.time),
                        'four_position':b.data.xpos[b.adapter.body_ids[b.four]].tolist(),
                        'reference':b.reference_pose_at(b.data.time).to_mapping()})
                if timing == 'continuous':
                    obs = b.observe()
                    if args.production_interface:
                        b.continuous_chunks_enabled=True
                        waypoints=[{'target':p,'duration_s':.5,
                                    'active':{'position':list(FOUR_POINT_NAMES),'orientation':[]},
                                    'grippers':{'left':0.,'right':0.}} for p in poses[1:]]
                        b.move_four_point_sequence(obs['observation_id'],name,waypoints)
                        b.set_grippers(0.,0.,duration=2.)
                    else:
                        b.move_four_points(obs['observation_id'], name, poses[-1].to_mapping(), 2.,
                                           position_names=position_names, orientation_names=())
                    sequence = ReferenceSequence(start+np.arange(5)*.5, poses)
                    if args.pelvis_reference:
                        pelvis_poses = [FourPointPose(np.tile(pelvis_start+d,(4,1)),
                                                     np.tile(pelvis_quat,(4,1))) for d in pelvis_offsets]
                        pelvis_sequence = ReferenceSequence(start+np.arange(5)*.5,pelvis_poses)
                    original = b.adapter.infer
                    def infer(data, motion, index):
                        pos, quat = sequence.sample(float(data.time)+np.arange(34)*.02)
                        motion.body_pos_w[:, b.four] = pos
                        motion.body_quat_w[:, b.four] = quat
                        if args.pelvis_reference:
                            pp, pq = pelvis_sequence.sample(float(data.time)+np.arange(34)*.02)
                            motion.body_pos_w[:,0] = pp[:,0]
                            motion.body_quat_w[:,0] = pq[:,0]
                        return original(data, motion, index)
                    if not args.production_interface:
                        b.adapter.infer = infer
                        b.reference_pose_at = sequence.pose_at
                    while b.active and not b.reason: tick()
                else:
                    for index, pose in enumerate(poses[1:]):
                        obs = b.observe()
                        b.move_four_points(obs['observation_id'], f'{name}-{index}', pose.to_mapping(), .5,
                                           position_names=position_names, orientation_names=())
                        while b.active and not b.reason: tick()
                        if b.reason: break
                points = np.array([r['four_position'] for r in records])
                row.update(stop_reason=b.reason, sim_s=float(b.data.time)-start,
                    max_foot_height_gain_m=(points[:,2:,2]-measured.positions[2:,2]).max(axis=0).tolist(),
                    max_no_plane_contact_s=(np.array(longest)*.02).tolist(),
                    swing_height_m=args.swing_height if args.locomotion else None,
                    final_four_delta_m=(points[-1]-measured.positions).tolist(),
                    max_pelvis_note='Full named robot states in video/robot_trace.jsonl',
                    commands=[{k:v for k,v in r.items() if not k.startswith('_')} for r in b.commands.values()])
                (folder/'reference_trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            except Exception as exc:
                row['error'] = f'{type(exc).__name__}: {exc}'
                traceback.print_exc()
            finally:
                if video: video.close()
                if b: b.close()
            (folder/'result.json').write_text(json.dumps(row, indent=2))
            brief = {k:v for k,v in row.items() if k not in ('knots','initial_measured','commands')}
            summary.append(brief)
            (args.output/'summary.json').write_text(json.dumps(summary, indent=2))
            print(json.dumps(brief), flush=True)


if __name__ == '__main__': main()
