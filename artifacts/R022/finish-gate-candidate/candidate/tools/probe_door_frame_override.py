"""Host-only differential validation of the exact asset003 frame override."""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import restore_named_render_state, simple_video


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recorded-state', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seed', type=int, default=8)
    p.add_argument('--case', choices=('original_convex_hull', 'four_boxes'), required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = json.loads(args.recorded_state.read_text())['host_render_state']
    all_rows = []
    states = []
    for enabled in (args.case == 'four_boxes',):
        name = 'four_boxes' if enabled else 'original_convex_hull'
        b = create_closed_door_backend(seed=args.seed, pd_profile='checkpoint', push_open=True,
                                      door_frame_override=enabled)
        video = None
        try:
            video = simple_video(b, args.output/name/'video', door_audit=True,
                label='Frame collision validation | 0 model calls | no task credit')
            trajectory = [b.data.qpos.copy()]
            for _ in range(350):
                b.tick(); video.record_tick('diagnostic_only')
                trajectory.append(b.data.qpos.copy())
            states.append(np.asarray(trajectory))
            np.save(args.output/name/'standing_qpos.npy', states[-1])
            m, d = b.model, b.data
            def pairs():
                result = []
                for c in d.contact:
                    names = [m.body(int(m.geom_bodyid[g])).name for g in (c.geom1, c.geom2)]
                    if any('hand_' in n for n in names) and any(n in ('link_0','link_1','link_2') for n in names):
                        result.append({'bodies': names, 'distance_m': float(c.dist)})
                return result
            restore_named_render_state(m, d, source)
            original_contacts = pairs()
            # Diagnostic geometry counterfactual only, never a physical policy action:
            # move the recorded robot root through the old phantom surface to
            # establish that the unchanged moving panel remains collidable.
            adr = int(m.joint('floating_base_joint').qposadr[0])
            d.qpos[adr] += .05
            mujoco.mj_forward(m, d)
            forward_contacts = pairs()
            row = {'case': name, 'stop_reason': b.reason,
                   'standing_physical_ticks': 350, 'standing_sim_s': 7.,
                   'recorded_state_contacts': original_contacts,
                   'kinematic_robot_forward_50mm_contacts': forward_contacts,
                   'frame_override': b.scene_setup.get('frame_collision_override'),
                   'source_recorded_state': str(args.recorded_state.resolve()),
                   'new_task_successes': 0, 'actor_access': False,
                   'kinematic_counterfactual_not_a_policy_action': True}
            all_rows.append(row)
            (args.output/name/'result.json').write_text(json.dumps(row, indent=2)+'\n')
            print(json.dumps(row), flush=True)
        finally:
            if video: video.close()
            b.close()
    result = {'cases': all_rows,
              'gpt_calls': 0, 'task_success_credit': False,
              'conclusion': 'Compare independently launched cases before formal activation.'}
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'complete': args.case}), flush=True)


if __name__ == '__main__':
    main()
