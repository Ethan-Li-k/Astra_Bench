"""Paired UMI-4 HOLD diagnostic for Jacobian-transpose wrist compensation."""
import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from locomanip.utils.hand_force_comp import HandForceCompensation
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose
from rsi.live import LiveSim


KP_TASK = 2000.0
KD_TASK = 30.0
MAX_FORCE = 20.0


def run(hand_comp, right_x=False, ticks=500):
    sim = LiveSim(table_offset_x=.1)
    names = sim.adapter.metadata['joint_names']
    nonroot_dof = np.array([sim.model.joint(name).dofadr[0] - 6 for name in names])
    if not np.array_equal(nonroot_dof, sim.adapter._policy_dof_adr - 6):
        raise RuntimeError('Named policy/non-root DOF mapping mismatch')
    arm = np.array([i for i, name in enumerate(names)
                    if any(part in name for part in ('shoulder', 'elbow', 'wrist'))])
    wrist_bodies = [sim.model.body(name).id for name in FOUR_POINT_NAMES[:2]]
    comp = HandForceCompensation(sim.model, KP_TASK, KD_TASK, MAX_FORCE)
    original_step = mujoco.mj_step
    substep_q, extra_rows, raw_force_norms, torque_clips = [], [], [], []

    def instrumented_step(model, data):
        extra29 = np.zeros(len(names))
        force_norm = np.zeros(2)
        if hand_comp:
            ref = sim.reference_pose_at(data.time).positions
            extra = comp.compute(model, data, ref[0], ref[1])
            extra29 = extra[nonroot_dof]
            data.ctrl[sim.act] = np.clip(
                data.ctrl[sim.act] + extra29, sim.limits[:, 0], sim.limits[:, 1])
            for side, (body_id, ref_pos) in enumerate(zip(wrist_bodies, ref[:2])):
                jacp = np.zeros((3, model.nv))
                mujoco.mj_jacBody(model, data, jacp, None, body_id)
                raw_force = KP_TASK*(ref_pos-data.xpos[body_id]) - KD_TASK*(jacp@data.qvel)
                force_norm[side] = np.linalg.norm(raw_force)
        extra_rows.append(extra29)
        raw_force_norms.append(force_norm)
        original_step(model, data)
        substep_q.append(data.qpos[sim.adapter._policy_qpos_adr].copy())
        torque_clips.append(np.logical_or(
            data.actuator_force[sim.act] <= sim.limits[:, 0] + 1e-7,
            data.actuator_force[sim.act] >= sim.limits[:, 1] - 1e-7))

    q, target, wrist_pos, error = [], [], [], []
    command_anchor = None
    mujoco.mj_step = instrumented_step
    try:
        for _ in range(ticks):
            if right_x and len(q) == 250:
                obs = sim.observe()
                command_anchor = np.asarray(obs['four_point_world']['right_wrist_yaw_link']['position'])
                goal = FourPointPose.from_mapping(obs['four_point_world']).translated(
                    [.02, 0., 0.], names=('right_wrist_yaw_link',))
                sim.move_four_points(obs['observation_id'], 'right-x-20mm',
                                     goal.to_mapping(), duration=2.)
            sim.tick()
            actual = sim.data.xpos[sim.adapter.body_ids[sim.four]].copy()
            ref = sim.reference_pose_at(sim.data.time).positions
            q.append(sim.data.qpos[sim.adapter._policy_qpos_adr].copy())
            target.append(sim.adapter._default_qpos_p
                          + sim.adapter.action_history[0, -1]*sim.adapter._action_scale_p)
            wrist_pos.append(actual[:2])
            error.append(np.linalg.norm(actual-ref, axis=1))
            if sim.reason:
                break
    finally:
        mujoco.mj_step = original_step

    q, target, wrist_pos, error = map(np.asarray, (q, target, wrist_pos, error))
    substep_q = np.asarray(substep_q)
    extra_rows = np.asarray(extra_rows)
    raw_force_norms = np.asarray(raw_force_norms)
    torque_clips = np.asarray(torque_clips)
    tail_ticks = min(250, len(q))
    tail_substeps = min(tail_ticks*sim.physics_substeps, len(substep_q))
    tail = slice(len(q)-tail_ticks, None)
    sub_tail = slice(len(substep_q)-tail_substeps, None)
    wrist_delta = np.linalg.norm(np.diff(wrist_pos[tail], axis=0), axis=2)
    result = {
        'enabled': hand_comp, 'ticks': len(q), 'sim_s': float(sim.data.time),
        'stop_reason': sim.reason,
        'tail_mean_error_m': dict(zip(FOUR_POINT_NAMES, error[tail].mean(axis=0).tolist())),
        'tail_max_error_m': dict(zip(FOUR_POINT_NAMES, error[tail].max(axis=0).tolist())),
        'tail_arm_q_step_rms_deg_20ms': float(np.rad2deg(
            np.sqrt(np.mean(np.diff(q[tail, arm], axis=0)**2)))),
        'tail_arm_q_step_rms_deg_physics': float(np.rad2deg(
            np.sqrt(np.mean(np.diff(substep_q[sub_tail][:, arm], axis=0)**2)))),
        'tail_arm_target_step_rms_deg_20ms': float(np.rad2deg(
            np.sqrt(np.mean(np.diff(target[tail, arm], axis=0)**2)))),
        'tail_wrist_step_p95_mm_20ms': dict(zip(FOUR_POINT_NAMES[:2],
            (1000*np.percentile(wrist_delta, 95, axis=0)).tolist())),
        'tail_wrist_range_xyz_mm': dict(zip(FOUR_POINT_NAMES[:2],
            (1000*np.ptp(wrist_pos[tail], axis=0)).tolist())),
        'cartesian_force_saturation_fraction_by_wrist': dict(zip(FOUR_POINT_NAMES[:2],
            np.mean(raw_force_norms > MAX_FORCE, axis=0).tolist())),
        'max_abs_extra_torque_nm': float(np.max(np.abs(extra_rows[:, arm]))),
        'torque_limit_fraction_arm': float(np.mean(torque_clips[:, arm])),
    }
    if right_x:
        result['command_status'] = sim.status()
        result['command_anchor_right_wrist_m'] = command_anchor.tolist()
        result['final_right_wrist_delta_from_anchor_m'] = (
            wrist_pos[-1, 1]-command_anchor).tolist()
    arrays = {'q29_rad': q, 'q_target_rad': target, 'wrist_world_m': wrist_pos,
              'four_point_error_m': error, 'substep_q29_rad': substep_q,
              'extra_torque29_nm': extra_rows, 'raw_cartesian_force_norm_n': raw_force_norms,
              'torque_clipped': torque_clips}
    return result, arrays


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--right-x', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    sources = [Path(__file__), Path(__file__).parents[1]/'rsi/live.py',
               Path(__file__).parents[1]/'rsi/scalebfm.py',
               Path('/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/utils/hand_force_comp.py')]
    source_dir = args.output/'sources'
    source_dir.mkdir()
    for source in sources:
        (source_dir/source.name).write_bytes(source.read_bytes())
    cases, arrays = {}, {}
    for label, enabled in (('no_comp', False), ('hand_comp', True)):
        cases[label], case_arrays = run(enabled, args.right_x)
        arrays.update({f'{label}_{key}': value for key, value in case_arrays.items()})
    np.savez(args.output/'trace.npz', **arrays)
    result = {
        'scope': ('paired 10 s UMI-4 right-wrist +20 mm X from fresh robot observation'
                  if args.right_x else 'paired 10 s UMI-4 HOLD')
                 + '; table shifted 0.1 m; no actor, object truth, or grasp',
        'llm_calls': 0,
        'hand_comp': {'kp_task_n_per_m': KP_TASK, 'kd_task_ns_per_m': KD_TASK,
                      'max_force_n': MAX_FORCE, 'gravity_comp': False,
                      'source': 'Loco_manip play_motion_track.py'},
        'sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        'cases': cases,
    }
    (args.output/'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
