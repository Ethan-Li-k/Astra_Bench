"""No-policy dynamic open/close/open diagnostic for both DEX3 hands."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from rsi.live import LiveSim


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    source = Path(__file__)
    live_source = source.parents[1]/'rsi/live.py'
    (args.output/'sources').mkdir()
    for path in (source, live_source):
        (args.output/'sources'/path.name).write_bytes(path.read_bytes())

    sim = LiveSim(table_offset_x=.1)
    finger_q, request, sim_s = [], [], []
    stages = (('open_initial', 0., 100), ('closed', 1., 150), ('open_final', 0., 150))
    boundaries = {}
    for label, closure, ticks in stages:
        sim.set_grippers(closure, closure)
        for _ in range(ticks):
            sim.tick()
            finger_q.append(sim.data.qpos[sim.fq].copy())
            request.append([closure, closure])
            sim_s.append(sim.data.time)
            if sim.reason:
                break
        boundaries[label] = len(finger_q)
        if sim.reason:
            break

    finger_q = np.asarray(finger_q)
    sides = np.array(['left' if name.startswith('left_') else 'right'
                      for name in sim.fingers])
    closed_end = finger_q[boundaries['closed']-1]
    open_end = finger_q[boundaries.get('open_final', len(finger_q))-1]
    result = {
        'scope': 'both DEX3 open/close/open in free space; no actor, object truth, or grasp',
        'llm_calls': 0, 'stop_reason': sim.reason, 'sim_s': float(sim.data.time),
        'controller': 'mechanical finger PD beside unmodified ScaleBFM UMI-4',
        'stages': boundaries, 'finger_names': sim.fingers,
        'closed_target_rad': sim.closed.tolist(),
        'closed_max_abs_error_rad_by_side': {
            side: float(np.max(np.abs(closed_end[sides == side]-sim.closed[sides == side])))
            for side in ('left', 'right')},
        'reopened_max_abs_position_rad_by_side': {
            side: float(np.max(np.abs(open_end[sides == side])))
            for side in ('left', 'right')},
        'finger_position_range_rad_by_side': {
            side: float(np.max(np.ptp(finger_q[:, sides == side], axis=0)))
            for side in ('left', 'right')},
        'sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (source, live_source)},
    }
    np.savez(args.output/'trace.npz', sim_s=sim_s, finger_q_rad=finger_q,
             closure_request=request, finger_names=sim.fingers)
    (args.output/'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
