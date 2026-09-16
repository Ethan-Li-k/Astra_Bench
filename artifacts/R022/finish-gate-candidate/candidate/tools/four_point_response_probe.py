"""Local two-wrist response matrix and one held-out compensation check."""
import argparse
import json
from pathlib import Path

import numpy as np

from rsi.live import LiveSim


def run(reference_delta, ticks=150):
    sim = LiveSim()
    initial = sim.pos0[sim.four].copy()
    sim._goal_pose.positions[:2] += np.asarray(reference_delta).reshape(2, 3)
    sim.duration = 1.
    actual = []
    for _ in range(ticks):
        sim.tick()
        actual.append(sim.data.xpos[sim.adapter.body_ids[sim.four]].copy())
        if sim.reason:
            break
    actual = np.asarray(actual)
    tail = actual[-min(25, len(actual)):].mean(axis=0)
    return {'initial': initial, 'tail': tail, 'ticks': len(actual),
            'stop_reason': sim.reason, 'actual': actual}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epsilon', type=float, default=.01)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if not 0 < args.epsilon <= .02:
        raise ValueError('epsilon must be within (0, .02] m')
    args.output.mkdir(parents=True)

    baseline = run(np.zeros(6))
    cases = []
    matrix = np.zeros((6, 6))
    for axis in range(6):
        command = np.zeros(6)
        command[axis] = args.epsilon
        case = run(command)
        matrix[:, axis] = ((case['tail'][:2]-baseline['tail'][:2]) / args.epsilon).reshape(-1)
        cases.append(case)

    desired = (baseline['initial'][:2]-baseline['tail'][:2]).reshape(-1)
    correction = np.linalg.pinv(matrix, rcond=.1) @ desired
    wrist_norms = np.linalg.norm(correction.reshape(2, 3), axis=1)
    validation = run(correction) if np.all(wrist_norms <= .03) else None

    arrays = {'response_matrix': matrix, 'reference_correction_m': correction,
              'baseline_actual': baseline.pop('actual')}
    for i, case in enumerate(cases):
        arrays[f'case_{i}_actual'] = case.pop('actual')
    if validation:
        arrays['validation_actual'] = validation.pop('actual')
    np.savez(args.output/'trace.npz', **arrays)
    def clean(case):
        return {'ticks': case['ticks'], 'stop_reason': case['stop_reason'],
                'tail_error_from_initial_m': (case['tail']-case['initial']).tolist()}
    result = {
        'scope': 'UMI-4 original ONNX; two-wrist position reference only; no object state',
        'epsilon_m': args.epsilon, 'physics_steps_per_case': 150*5, 'llm_calls': 0,
        'response_matrix_actual_wrist_delta_per_reference_delta': matrix.tolist(),
        'response_rank': int(np.linalg.matrix_rank(matrix)),
        'response_condition': float(np.linalg.cond(matrix)),
        'baseline': clean(baseline),
        'reference_correction_m': correction.reshape(2, 3).tolist(),
        'reference_correction_norm_m': wrist_norms.tolist(),
        'validation_run': clean(validation) if validation else None,
        'validation_skipped_reason': None if validation else 'correction exceeds 3 cm per wrist',
        'limit': 'single initial pose; pseudo-inverse rcond=0.1; diagnostic, not production calibration',
    }
    (args.output/'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
