"""Bounded stationary diagnostic: record targets, actual motion and contacts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import mujoco
import numpy as np
from rsi.live import LiveSim


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--table-offset-x', type=float, default=0.)
    parser.add_argument('--physics-substeps', type=int, choices=(1, 2), default=1)
    parser.add_argument('--reference', choices=('initial', 'settled'), default='initial')
    parser.add_argument('--arm-target', choices=('raw', 'hold', 'smooth', 'rate'), default='raw')
    parser.add_argument('--move', action='store_true')
    parser.add_argument('--pd-mode', choices=('explicit', 'implicit'), default='explicit')
    parser.add_argument('--joint-friction', type=float, choices=(0., .1), default=0.)
    parser.add_argument('--payload-comp', action='store_true')
    parser.add_argument('--reference-servo', action='store_true')
    args = parser.parse_args()
    if args.table_offset_x not in (0., .1):
        parser.error('Diagnostic comparison only: 0 or 0.1 m')
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), Path(__file__).parents[1] / 'rsi/live.py',
               Path(__file__).parents[1] / 'rsi/scalebfm.py',
               Path(__file__).parents[1] / 'rsi/reference_servo.py']
    (args.output / 'sources').mkdir()
    for source in sources:
        (args.output / 'sources' / source.name).write_bytes(source.read_bytes())
    (args.output / 'manifest.json').write_text(json.dumps({
        'scope': '20s stationary diagnostic; no actor or grasp', 'llm_calls': 0,
        'table_offset_x_m': args.table_offset_x,
        'reference': args.reference,
        'arm_target': args.arm_target,
        'arm_filter_tau_s': .08 if args.arm_target == 'smooth' else 0.,
        'arm_rate_rad_s': .5 if args.arm_target == 'rate' else None,
        'move': args.move,
        'pd_mode': args.pd_mode,
        'policy_joint_frictionloss_nm': args.joint_friction,
        'payload_comp': args.payload_comp,
        'reference_servo': args.reference_servo,
        'physics_dt_s': .004 / args.physics_substeps, 'controller_dt_s': .02,
        'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2))
    import rsi.live as live
    original_scene = live.tabletop_model
    def shifted_scene(offset_x=0.):
        model = original_scene(offset_x)
        for i in range(model.ngeom):
            name = model.geom(i).name
            if name == 'diagnostic_table' or name.startswith('table_leg_'):
                model.geom_pos[i, 0] += args.table_offset_x
        model.qpos0[model.joint('diagnostic_cube_free').qposadr[0]] += args.table_offset_x
        return model
    live.tabletop_model = shifted_scene
    try:
        s = LiveSim(reference_servo=args.reference_servo)
    finally:
        live.tabletop_model = original_scene
    names = s.adapter.metadata['joint_names']
    # 0.1 Nm is the mirrored ScaleBridge deployment XML value, not a fitted gain.
    s.model.dof_frictionloss[s.adapter._policy_dof_adr] = args.joint_friction
    arm = np.array([i for i, name in enumerate(names) if any(x in name for x in ('shoulder', 'elbow', 'wrist'))])
    raw_targets = []
    compensation = np.zeros(29)
    comp_rows = []
    wrist_indices = [s.adapter.metadata['selected_body_names'].index(n) for n in ('left_wrist_yaw_link', 'right_wrist_yaw_link')]
    correction = np.zeros((2, 3))
    correction_rows = []
    if args.payload_comp:
        baseline = mujoco.MjModel.from_xml_path('artifacts/R004/reference_scene.xml')
        baseline_data = mujoco.MjData(baseline)
        current_static = mujoco.MjData(s.model)
        base_q = np.array([baseline.joint(n).qposadr[0] for n in names])
        base_v = np.array([baseline.joint(n).dofadr[0] for n in names])
        # Semantic root mapping: both assets' free joint belongs to pelvis.
        base_root = baseline.body_jntadr[baseline.body('pelvis').id]
        current_root = s.model.body_jntadr[s.model.body('pelvis').id]
        base_root_q = baseline.jnt_qposadr[base_root]
        current_root_q = s.model.jnt_qposadr[current_root]
    original_infer = s.adapter.infer
    held = None
    previous_target = s.data.qpos[s.adapter._policy_qpos_adr].copy()
    def diagnostic_infer(*call_args):
        nonlocal held, previous_target
        correction_rows.append(s.servo.correction.copy() if s.servo else correction.copy())
        target = original_infer(*call_args)
        raw_targets.append(target.copy())
        if args.payload_comp:
            current_static.qpos[:] = s.data.qpos
            baseline_data.qpos[base_q] = s.data.qpos[s.adapter._policy_qpos_adr]
            baseline_data.qpos[base_root_q:base_root_q+7] = s.data.qpos[current_root_q:current_root_q+7]
            mujoco.mj_forward(s.model, current_static)
            mujoco.mj_forward(baseline, baseline_data)
            compensation[arm] = (current_static.qfrc_bias[s.adapter._policy_dof_adr] - baseline_data.qfrc_bias[base_v])[arm]
        comp_rows.append(compensation.copy())
        if args.arm_target == 'hold' and len(raw_targets) > 250:
            if held is None:
                held = np.mean(raw_targets[200:250], axis=0)
            target[arm] = held[arm]
        if args.arm_target == 'smooth':
            target[arm] = previous_target[arm] + .2*(target[arm]-previous_target[arm])
        if args.arm_target == 'rate':
            target[arm] = previous_target[arm] + np.clip(target[arm]-previous_target[arm], -.01, .01)
        previous_target = target.copy()
        if args.arm_target != 'raw':
            # History must describe the target actually sent to PD.
            s.adapter.action_history[0, -1] = (target-s.adapter._default_qpos_p)/s.adapter._action_scale_p
        return target
    s.adapter.infer = diagnostic_infer
    rows = []
    poses, body_rows, errors = [], [], []
    contacts = Counter()
    clips = np.zeros(29, dtype=int)
    start = time.monotonic()
    original_step = mujoco.mj_step
    s.model.opt.timestep = .004 / args.physics_substeps
    if args.pd_mode == 'implicit':
        s.model.actuator_gainprm[s.act, 0] = s.kp
        s.model.actuator_biastype[s.act] = mujoco.mjtBias.mjBIAS_AFFINE
        s.model.actuator_biasprm[s.act, 1] = -s.kp
        s.model.actuator_biasprm[s.act, 2] = -s.kd

    def instrumented_step(model, data):
        for substep in range(args.physics_substeps):
            if substep:
                # Preserve PD feedback at each physics step, with the same target.
                target = s.adapter._default_qpos_p + s.adapter.action_history[0, -1] * s.adapter._action_scale_p
                torque = s.kp*(target-data.qpos[s.adapter._policy_qpos_adr]) - s.kd*data.qvel[s.adapter._policy_dof_adr]
                data.ctrl[s.act] = np.clip(torque, s.limits[:, 0], s.limits[:, 1])
                ft = 20*(s.closed*s.grip-data.qpos[s.fq])-data.qvel[s.fv]
                data.ctrl[s.fa] = np.clip(ft, s.fl[:, 0], s.fl[:, 1])
            if args.pd_mode == 'implicit':
                data.ctrl[s.act] = s.adapter._default_qpos_p + s.adapter.action_history[0, -1]*s.adapter._action_scale_p
            elif args.payload_comp:
                data.ctrl[s.act] = np.clip(data.ctrl[s.act]+compensation, s.limits[:, 0], s.limits[:, 1])
            original_step(model, data)
            clips[:] += np.abs(data.actuator_force[s.act]) >= s.limits[:, 1]-1e-7
            for c in data.contact:
                pair = tuple(sorted((model.geom(c.geom1).name, model.geom(c.geom2).name)))
                contacts[pair] += 1

    mujoco.mj_step = instrumented_step
    try:
        for tick in range(1000):
            if args.move and tick == 500:
                observation = s.observe()
                s.move_wrist(observation['observation_id'], 'right-x-2cm', [.02, 0, 0], duration=2.)
            if args.reference == 'settled' and tick == 250:
                # One frozen, kinematically consistent robot-only reference.
                # Average qpos over seconds 4..5, then FK; never chase current state.
                ref = mujoco.MjData(s.model)
                ref.qpos[:] = np.mean(poses[-50:], axis=0)
                ref.qpos[3:7] /= np.linalg.norm(ref.qpos[3:7])
                mujoco.mj_forward(s.model, ref)
                s.pos0 = ref.xpos[s.adapter.body_ids].copy()
                s.quat0 = ref.xquat[s.adapter.body_ids].copy()
                s.start = s.goal = s.reference = s.pos0[s.wrist].copy()
                s.t0 = float(s.data.time)
            poses.append(s.data.qpos.copy())
            s.tick()
            target = s.adapter._default_qpos_p + s.adapter.action_history[0, -1] * s.adapter._action_scale_p
            rows.append(np.r_[s.data.time, s.data.qpos[s.adapter._policy_qpos_adr], target])
            actual = s.data.xpos[s.adapter.body_ids]
            body_rows.append(actual.copy())
            rot_dot = np.sum(s.data.xquat[s.adapter.body_ids]*s.quat0, axis=1)
            desired_positions = s.pos0.copy()
            desired_positions[s.wrist] = s.reference
            errors.append(np.r_[np.linalg.norm(actual-desired_positions, axis=1),
                                np.rad2deg(2*np.arccos(np.clip(abs(rot_dot), 0, 1)))])
            if s.reason:
                break
    finally:
        mujoco.mj_step = original_step
    rows = np.asarray(rows)
    np.savez(args.output / 'trajectory.npz', sim_s=rows[:, 0], q=rows[:, 1:30], target=rows[:, 30:],
             joint_names=names, raw_targets=raw_targets, gravity_compensation_nm=comp_rows,
             wrist_reference_correction_m=correction_rows,
             body_pos=body_rows, body_errors=errors, body_names=s.adapter.metadata['selected_body_names'])
    result = {'reason': s.reason, 'sim_s': float(s.data.time), 'wall_s': time.monotonic()-start,
              'motion_status': s.status(),
              'contacts_substep_counts': [{'pair': pair, 'count': count} for pair, count in contacts.items()],
              'torque_limit_substep_counts': dict(zip(names, clips.tolist())), 'joints': {}}
    stationary = rows[rows[:, 0] >= 10]
    selected = rows[:, 0] >= 10
    result['body_tracking'] = {name: {'mean_position_error_m': float(np.mean(np.asarray(errors)[selected, i])),
        'mean_rotation_error_deg': float(np.mean(np.asarray(errors)[selected, i+14])),
        'position_range_xyz_m': np.ptp(np.asarray(body_rows)[selected, i], axis=0).tolist()}
        for i, name in enumerate(s.adapter.metadata['selected_body_names'])}
    for i, name in enumerate(names):
        metrics = {}
        for label, col in [('actual', i+1), ('target', i+30)]:
            x = stationary[:, col]
            power = abs(np.fft.rfft(x-x.mean()))**2
            freq = np.fft.rfftfreq(len(x), .02)
            band = freq >= 2
            metrics[label] = {'range_deg': float(np.rad2deg(np.ptp(x))),
                'step_rms_deg': float(np.rad2deg(np.sqrt(np.mean(np.diff(x)**2)))),
                'peak_above_2hz': float(freq[band][np.argmax(power[band])])}
        result['joints'][name] = metrics
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('reason', 'sim_s', 'wall_s', 'contacts_substep_counts')}))


if __name__ == '__main__':
    main()
