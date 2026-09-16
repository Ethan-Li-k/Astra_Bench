"""Host-only FK/torque audit of saved references; no physics or model calls."""
import argparse
import json
import random
from pathlib import Path
import mujoco
import numpy as np
from rsi.simple_environment import make_simple_env, DOOR_ENV
from rsi.simple_recording import restore_named_render_state
from rsi.scalebfm import METADATA


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    random.seed(0); np.random.seed(0)
    env = make_simple_env(DOOR_ENV)
    try:
        env.reset(seed=0)
        runtime = env.unwrapped; model = runtime.mjModel
        names = json.loads(METADATA.read_text())['joint_names']
        qadr = [model.joint(n).qposadr[0] for n in names]
        aidx = [model.actuator(n).id for n in names]
        feet = [model.body(s+'_ankle_roll_link').id for s in ('left', 'right')]
        actual, target = mujoco.MjData(model), mujoco.MjData(model)
        results = []
        for trace in sorted(args.probe_root.glob('*/video/robot_trace.jsonl')):
            rows = []
            for line in trace.read_text().splitlines():
                r = json.loads(line); state = r['host_render_state']
                restore_named_render_state(model, actual, state)
                target.qpos[:] = actual.qpos
                q = np.array(state['control_chain']['commanded_joint_target29_rad'])
                target.qpos[qadr] = q
                mujoco.mj_forward(model, target)
                rows.append({'sim_s':r['sim_s'],
                    'actual_ankle_z_m':actual.xpos[feet, 2].tolist(),
                    'target_fk_ankle_z_m_fixed_measured_base':target.xpos[feet, 2].tolist(),
                    'target_fk_minus_actual_ankle_z_m':(target.xpos[feet,2]-actual.xpos[feet,2]).tolist(),
                    'leg_q_target_minus_actual_rad':(q[:12]-actual.qpos[qadr][:12]).tolist(),
                    'reference_ankle_z_m':[r['reference'][s+'_ankle_roll_link']['position_world_m'][2]
                                             for s in ('left','right')]})
            dest = args.output/(trace.parents[1].name+'.jsonl')
            dest.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            # Restrict inference to ticks with an explicitly raised left-foot reference.
            raised = [r for r in rows if r['reference_ankle_z_m'][0] > .065]
            results.append({'case':trace.parents[1].name,'samples':len(rows),'raised_reference_samples':len(raised),
                'raised_target_fk_left_z_min_max_m':([min(r['target_fk_ankle_z_m_fixed_measured_base'][0] for r in raised),
                    max(r['target_fk_ankle_z_m_fixed_measured_base'][0] for r in raised)] if raised else None),
                'raised_target_minus_actual_left_z_min_max_m':([min(r['target_fk_minus_actual_ankle_z_m'][0] for r in raised),
                    max(r['target_fk_minus_actual_ankle_z_m'][0] for r in raised)] if raised else None)})
        # Check native PD indexing using named coordinates/actuators at fixed state.
        robot = runtime.task.robot
        body_names = [model.joint(int(i)).name for i in robot.body_joint_index]
        before = runtime.mjData.qpos.copy()
        runtime.mjData.qvel[:] = 0.
        native_q = np.array([runtime.mjData.joint(n).qpos[0] for n in body_names])
        from simple.core.action import ActionCmd
        robot.apply_action(ActionCmd('decoupled_wbc', target_q=native_q+.01,
                                    left_hand_q=None, right_hand_q=None))
        expected = np.array(runtime.sonic_config['MOTOR_KP'])*.01
        observed = np.array([runtime.mjData.actuator(n).ctrl[0] for n in body_names])
        mismatch = float(np.max(np.abs(observed-expected)))
        report = {'actor_access':False,'gpt_calls':0,'physics_action_calls':0,'task_success_credit':False,
            'fk_caveat':'Kinematic target at measured base, not a commanded base trajectory or feasibility proof.',
            'native_pd_named_torque_max_error_nm':mismatch,
            'native_pd_qpos_unchanged':bool(np.array_equal(before,runtime.mjData.qpos)),
            'body_names':body_names, 'cases':results}
        (args.output/'summary.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report),flush=True)
    finally: env.close()


if __name__ == '__main__': main()
