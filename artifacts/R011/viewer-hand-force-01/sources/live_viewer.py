"""Interactive simulation diagnostics with explicit human action provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Queue
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--scripted', action='store_true')
    parser.add_argument('--reference-servo', action='store_true')
    parser.add_argument('--hand-force-comp', action='store_true')
    parser.add_argument('--diagnostic-continuous-latent', action='store_true')
    parser.add_argument('--table-offset-x', type=float, choices=(0., .1), default=0.)
    parser.add_argument('--seconds', type=float, default=900)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1800:
        parser.error('Bounded sessions: 1..1800 seconds')
    if sum((args.diagnostic_continuous_latent, args.reference_servo,
            args.hand_force_comp)) > 1:
        parser.error('Do not combine unvalidated diagnostic interventions')
    os.environ.setdefault('MUJOCO_GL', 'egl' if args.headless else 'glfw')
    import mujoco
    import mujoco.viewer
    import numpy as np
    from PIL import Image
    from rsi.live import LiveSim
    from rsi.scalebfm import MODEL_SHA256, METADATA
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), Path(__file__).parents[1] / 'rsi/live.py',
               Path(__file__).parents[1] / 'rsi/scalebfm.py',
               Path(__file__).parents[1] / 'rsi/reference_servo.py', METADATA]
    if args.hand_force_comp:
        sources.append(Path('/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/utils/hand_force_comp.py'))
    if args.diagnostic_continuous_latent:
        sources += [Path(__file__).parents[1] / 'rsi/diagnostic_latent.py',
            Path('/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/runtime/scripts/exp8ap/scalebfm_eager.py'),
            Path('/home/galbot/lizekai/Loco_manip/locomanip/src/locomanip/bfm/two_stage.py')]
    (args.output / 'sources').mkdir()
    for source in sources:
        (args.output / 'sources' / source.name).write_bytes(source.read_bytes())
    manifest = {'runtime': 'MUJOCO_PHYSICS_MODEL38000_UMI4', 'model_sha256': MODEL_SHA256,
                'actor': 'scripted_interface_test' if args.scripted else 'human_keyboard',
                'llm_calls': 0, 'p0_evaluation': False, 'started_unix_s': time.time(),
                'reference_servo': args.reference_servo,
                'hand_force_comp': args.hand_force_comp,
                'hand_force_comp_config': ({'kp_task': 2000., 'kd_task': 30., 'max_force': 20.}
                                           if args.hand_force_comp else None),
                'table_offset_x_m': args.table_offset_x,
                'backend': ('DIAGNOSTIC_OFF_GRID_CONTINUOUS_LATENT'
                            if args.diagnostic_continuous_latent else
                            'ORIGINAL_ONNX_PLUS_JT_HAND_COMP'
                            if args.hand_force_comp else 'ORIGINAL_ONNX'),
                'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    try:
        sim = LiveSim(reference_servo=args.reference_servo,
                      hand_force_comp=args.hand_force_comp,
                      table_offset_x=args.table_offset_x)
        backend = None
        if args.diagnostic_continuous_latent:
            from rsi.diagnostic_latent import DiagnosticLatentPolicy
            backend = DiagnosticLatentPolicy(sim.adapter, 'continuous')
            sim.adapter._run_policy = backend
    except Exception as exc:
        (args.output / 'summary.json').write_text(json.dumps({
            'reason': 'startup_failure', 'error': str(exc), 'llm_calls': 0}))
        raise
    queue = Queue()
    viewer = None
    if not args.headless:
        viewer = mujoco.viewer.launch_passive(sim.model, sim.data, key_callback=queue.put)
        with viewer.lock():
            viewer.cam.lookat[:] = [.20, -.15, .70]
            viewer.cam.distance = 1.8
            viewer.cam.azimuth = 140
            viewer.cam.elevation = -20
    print('READY: W/S=world +/-X, A/D=world +/-Y, I/K=world +/-Z (1cm); C=half-close, O=open, X=cancel, ESC=close window. Human diagnostic, not autonomous grasp.', flush=True)
    print('BACKEND:', manifest['backend'], '; original checkpoint unchanged; grasp not evaluated.', flush=True)
    renderer = mujoco.Renderer(sim.model, height=240, width=320)
    cameras = [sim.model.camera(i).name for i in range(sim.model.ncam)
               if sim.model.camera(i).name in ('head_cam', 'right_wrist_cam')]
    rows = 0
    start = time.monotonic()
    next_tick = start
    frame = 0
    tick = 0
    scripted = {50: ord('W'), 70: ord('X'), 100: ord('C'), 160: ord('O')}
    moves = {ord('W'): [.01, 0, 0], ord('S'): [-.01, 0, 0],
             ord('A'): [0, .01, 0], ord('D'): [0, -.01, 0],
             ord('I'): [0, 0, .01], ord('K'): [0, 0, -.01]}
    reason = 'time_limit'
    try:
        with (args.output / 'events.jsonl').open('x') as events, (args.output / 'robot_ticks.jsonl').open('x') as states:
            def event(kind, **kwargs):
                events.write(json.dumps({'kind': kind, 'sim_s': float(sim.data.time), 'wall_elapsed_s': time.monotonic()-start, **kwargs})+'\n')
                events.flush()
            while time.monotonic() - start < args.seconds:
                if viewer is not None and not viewer.is_running():
                    reason = 'window_closed'
                    break
                if args.scripted and tick in scripted:
                    queue.put(scripted[tick])
                try:
                    while True:
                        key = queue.get_nowait()
                        event('raw_key', key=key)
                        try:
                            if key in moves:
                                obs = sim.observe()
                                result = sim.move_wrist(obs['observation_id'], f'cmd_{rows:06d}', moves[key])
                                rows += 1
                            elif key == ord('X'):
                                result = sim.cancel()
                            elif key in (ord('C'), ord('O')):
                                result = sim.set_gripper(.5 if key == ord('C') else 0.)
                            else:
                                continue
                            event('command', key=chr(key), result=result)
                        except ValueError as exc:
                            event('rejected', key=key, reason=str(exc))
                except Empty:
                    pass
                sim.tick()
                tick += 1
                states.write(json.dumps({'sim_s': float(sim.data.time),
                    'control_tick': tick,
                    'wall_elapsed_s': time.monotonic()-start,
                    'deadline_lag_s': max(0., time.monotonic()-next_tick),
                    'q29': sim.data.qpos[sim.adapter._policy_qpos_adr].tolist(),
                    'dq29': sim.data.qvel[sim.adapter._policy_dof_adr].tolist(),
                    'proprio_history': sim.adapter.policy_history.tolist(),
                    'action_history': sim.adapter.action_history.tolist(),
                    'wrist_actual_m': sim.data.xpos[sim.adapter.body_ids[sim.wrist]].tolist(),
                    'wrist_reference_m': sim.reference.tolist(),
                    'left_wrist_actual_m': sim.data.xpos[sim.adapter.body_ids[sim.wrists[0]]].tolist(),
                    'wrist_reference_correction_m': sim.servo.correction.tolist() if sim.servo else None,
                    'pelvis_height_m': float(sim.data.qpos[2]),
                    'finger_q': sim.data.qpos[sim.fq].tolist(), 'finger_closure_request': sim.grip,
                    'status': sim.status(), 'stop_reason': sim.reason})+'\n')
                states.flush()
                if tick % 50 == 0:
                    obs = sim.observe()
                    obs['images'] = []
                    for camera in cameras:
                        before = time.monotonic()
                        renderer.update_scene(sim.data, camera=camera)
                        rgb = renderer.render()
                        name = f'{frame:05d}_{camera}.png'
                        Image.fromarray(rgb).save(args.output / name)
                        obs['images'].append({'path': name, 'camera': camera,
                            'sim_exposure_s': float(sim.data.time), 'render_started_monotonic_s': before,
                            'render_finished_monotonic_s': time.monotonic()})
                    with (args.output / f'{frame:05d}_observation.json').open('x') as f:
                        json.dump(obs, f)
                    event('observation_saved', frame=frame)
                    frame += 1
                if viewer is not None:
                    viewer.sync()
                if sim.reason:
                    reason = sim.reason
                    event('stability_stop', reason=reason)
                    break
                next_tick += .02
                time.sleep(max(0., next_tick-time.monotonic()))
    except KeyboardInterrupt:
        reason = 'interrupted'
    except Exception:
        reason = 'runtime_error'
        raise
    finally:
        renderer.close()
        if viewer is not None:
            viewer.close()
        result = {'reason': reason, 'sim_s': float(sim.data.time),
                  'wall_s': time.monotonic()-start, 'saved_observations': frame,
                  'last_motion': sim.status(), 'llm_calls': 0,
                  'backend': manifest['backend'],
                  'diagnostic_raw_onnx_parity_max_error': backend.parity_error if backend else None,
                  'scope': manifest['actor'], 'grasp_success': 'not_evaluated'}
        (args.output / 'summary.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
