"""Paired 3 s UMI-4/VR-5-mask closed-loop HOLD diagnostic."""
import argparse
import json
from pathlib import Path

import numpy as np

from locomanip.bfm.scaletrack import BODY_NAMES
from rsi.four_point import FOUR_POINT_NAMES
from rsi.live import LiveSim


def set_mode(adapter, names):
    adapter.mode[:] = 0
    for name in names:
        adapter.mode[0, BODY_NAMES.index(name)] = 1
    adapter.mode_mapping = np.concatenate(
        [np.repeat(adapter.mode[0], width) for width in (3, 3, 6, 6)]
        + [np.ones(1, np.float32)])[None]


def run(names, ticks=150, physics_dt=.004):
    sim = LiveSim(physics_dt=physics_dt)
    set_mode(sim.adapter, names)
    errors, qpos, targets = [], [], []
    for _ in range(ticks):
        sim.tick()
        actual = sim.data.xpos[sim.adapter.body_ids[sim.four]]
        errors.append(np.linalg.norm(actual-sim.pos0[sim.four], axis=1))
        qpos.append(sim.data.qpos[sim.adapter._policy_qpos_adr].copy())
        targets.append(sim.adapter._default_qpos_p
                       + sim.adapter.action_history[0, -1]*sim.adapter._action_scale_p)
        if sim.reason:
            break
    errors, qpos, targets = map(np.asarray, (errors, qpos, targets))
    tail = errors[-min(50, len(errors)):]
    return {
        'active_names': list(names), 'physics_dt_s': physics_dt,
        'physics_substeps_per_tracker_tick': round(.02/physics_dt),
        'ticks': len(errors), 'stop_reason': sim.reason,
        'final_error_m': dict(zip(FOUR_POINT_NAMES, errors[-1].tolist())),
        'tail_mean_error_m': dict(zip(FOUR_POINT_NAMES, tail.mean(axis=0).tolist())),
        'tail_max_error_m': dict(zip(FOUR_POINT_NAMES, tail.max(axis=0).tolist())),
        'tail_q_step_rms_rad': float(np.sqrt(np.mean(np.diff(qpos[-min(50, len(qpos)):], axis=0)**2))),
        'tail_target_step_rms_rad': float(np.sqrt(np.mean(np.diff(targets[-min(50, len(targets)):], axis=0)**2))),
        '_arrays': (errors, qpos, targets),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    cases = {
        'UMI-4': run(FOUR_POINT_NAMES),
        'UMI-4-training-dt': run(FOUR_POINT_NAMES, physics_dt=.005),
        'VR-5-mask-only': run(('pelvis', *FOUR_POINT_NAMES)),
    }
    arrays = {}
    for label, case in cases.items():
        for key, value in zip(('error_m', 'q29_rad', 'q_target_rad'), case.pop('_arrays')):
            arrays[f'{label}_{key}'] = value
    np.savez(args.output/'trace.npz', **arrays)
    result = {'scope': 'original ONNX, same initial state/reference/full anchor; explicit mode and physics-dt cases',
              'llm_calls': 0, 'cases': cases}
    (args.output/'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
