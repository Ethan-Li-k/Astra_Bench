"""Same-state UMI-4 versus pelvis-mask diagnostic; no physics steps."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from locomanip.bfm.scaletrack import BODY_NAMES
from rsi.diagnostic_latent import DiagnosticLatentPolicy
from rsi.four_point import FOUR_POINT_NAMES
from rsi.live import LiveSim


def mode_arrays(names):
    mode = np.zeros((1, len(BODY_NAMES)), np.float32)
    for name in names:
        mode[0, BODY_NAMES.index(name)] = 1
    mapping = np.concatenate([np.repeat(mode[0], width) for width in (3, 3, 6, 6)]
                             + [np.ones(1, np.float32)])[None]
    return mode, mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    sim = LiveSim()
    adapter, data = sim.adapter, sim.data
    motion = SimpleNamespace(num_frames=34,
        body_pos_w=np.tile(sim.pos0, (34, 1, 1)).astype(np.float32),
        body_quat_w=np.tile(sim.quat0, (34, 1, 1)).astype(np.float32))
    anchor_pos = data.xpos[adapter.body_ids[0]].astype(np.float32)
    anchor_quat = adapter._body_quat_wxyz(data, adapter.body_ids[0])
    body_pos = data.xpos[adapter.body_ids].astype(np.float32)
    body_quat = np.asarray([adapter._body_quat_wxyz(data, i) for i in adapter.body_ids])
    task = adapter._build_policy_task(anchor_pos, anchor_quat, body_pos, body_quat, motion, 0)

    eager = DiagnosticLatentPolicy(adapter, 'torch_raw')
    original = adapter.mode.copy(), adapter.mode_mapping.copy()
    results = {}
    try:
        for label, names in (
            ('UMI-4', FOUR_POINT_NAMES),
            ('VR-5-mask-only', ('pelvis', *FOUR_POINT_NAMES)),
        ):
            adapter.mode, adapter.mode_mapping = mode_arrays(names)
            eager.parity_error = None
            action = eager(task)
            results[label] = {
                'active_names': list(names),
                'mode_mapping_sum': float(adapter.mode_mapping.sum()),
                'latent': eager.raw_latent.tolist(),
                'fsq_code': eager.raw_code.tolist(),
                'action': action.tolist(),
                'q_target': (adapter._default_qpos_p + action*adapter._action_scale_p).tolist(),
                'onnx_eager_max_error': eager.parity_error,
            }
    finally:
        adapter.mode, adapter.mode_mapping = original

    left = np.asarray(results['UMI-4']['action'])
    right = np.asarray(results['VR-5-mask-only']['action'])
    latent_left = np.asarray(results['UMI-4']['latent'])
    latent_right = np.asarray(results['VR-5-mask-only']['latent'])
    code_left = np.asarray(results['UMI-4']['fsq_code'])
    code_right = np.asarray(results['VR-5-mask-only']['fsq_code'])
    delta_q = (right-left)*adapter._action_scale_p
    result = {
        'scope': 'offline same state/task/history; only pelvis mode and mode_mapping differ',
        'physics_steps': 0, 'llm_calls': 0,
        'policy_task_identical': True,
        'joint_names': adapter.metadata['joint_names'],
        'modes': results,
        'difference': {
            'latent_l2': float(np.linalg.norm(latent_right-latent_left)),
            'latent_max_abs': float(np.max(np.abs(latent_right-latent_left))),
            'fsq_changed_dimensions': int(np.count_nonzero(code_right != code_left)),
            'fsq_changed_indices': np.flatnonzero(code_right != code_left).tolist(),
            'action_l2': float(np.linalg.norm(right-left)),
            'action_max_abs': float(np.max(np.abs(right-left))),
            'q_target_delta_l2_rad': float(np.linalg.norm(delta_q)),
            'q_target_delta_max_abs_rad': float(np.max(np.abs(delta_q))),
            'q_target_delta_by_joint_rad': dict(zip(adapter.metadata['joint_names'], delta_q.tolist())),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result['difference'], indent=2))


if __name__ == '__main__':
    main()
