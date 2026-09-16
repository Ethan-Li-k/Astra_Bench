"""Native SIMPLE standing diagnostic, with no GPT calls or task-success credit."""
import argparse
import json
from pathlib import Path
import traceback

import mujoco
import numpy as np
from rsi.simple_environment import create_closed_door_backend, create_native_task_backend
from rsi.simple_recording import simple_video


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--push-open', action='store_true')
    parser.add_argument('--env-id', help='Probe a native SIMPLE task without door-specific reset')
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    result = {'gpt_calls': 0, 'task_success_credit': False, 'physics_steps': 0}
    backend = video = None
    try:
        backend = (create_native_task_backend(args.env_id, seed=args.seed, settle_ticks=0) if args.env_id
                   else create_closed_door_backend(seed=args.seed, settle_ticks=0, push_open=args.push_open))
        result['scene_setup'] = backend.scene_setup
        video = simple_video(backend, args.output/'video', label='ScaleBFM standing diagnostic | no GPT calls')
        (args.output/'initial_observation').mkdir()
        video(args.output/'initial_observation')
        model, data = backend.model, backend.data
        start_time = float(data.time)
        articulation = [model.joint(i).name for i in range(model.njnt)
                        if model.joint(i).name.startswith('articulate_joint_')]
        def angles(): return {n:float(data.joint(n).qpos[0]) for n in articulation}
        initial_angles = angles()
        records = []
        for tick in range(350):
            before = float(data.time); backend.tick(); after = float(data.time)
            np.testing.assert_allclose(after-before, .02, atol=1e-10)
            records.append({'sim_s': after, 'pelvis_z': float(data.body('pelvis').xpos[2]),
                'articulation_q': angles(), 'native_task_success': backend._native_task_success,
                'max_abs_qvel': float(np.max(np.abs(data.qvel)))})
            video.record_tick('diagnostic_only')
            result['physics_steps'] = tick+1
            if backend.reason:
                break
        (args.output/'observation').mkdir()
        video(args.output/'observation')
        velocity = np.zeros(6)
        mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_BODY,
                                model.body('pelvis').id, velocity, 1)
        gyro = model.sensor('gyro_pelvis'); address = int(gyro.adr[0])
        result.update(status='passed' if backend.reason is None else 'standing_failed',
            stop_reason=backend.reason, sim_s=float(data.time)-start_time,
            elastic_band_enabled=backend.env.sonic_config['ENABLE_ELASTIC_BAND'],
            physics_dt=float(model.opt.timestep),
            native_action_calls=backend.physics_action_calls,
            pelvis_gyro_error=float(np.max(np.abs(data.sensordata[address:address+3]-velocity[:3]))),
            initial_articulation_angles=initial_angles, final_articulation_angles=angles(),
            native_success_without_actor=any(r['native_task_success'] for r in records),
            cameras=[model.camera(i).name for i in range(model.ncam)],
            records=records)
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
        traceback.print_exc()
    finally:
        if video is not None: video.close()
        if backend is not None: backend.close()
        (args.output/'result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({k:v for k,v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    main()
