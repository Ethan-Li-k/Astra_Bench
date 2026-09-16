"""Actual six-second source-apple support diagnostic; no actor or task score."""
import json
from pathlib import Path
import numpy as np
from apple_backend import create_backend, apple_geometry, apple_contacts, ROOT
from rsi.episode_video import EpisodeVideo


def main():
    out = ROOT / 'diagnostics/apple-reset-001'
    out.mkdir(parents=True, exist_ok=False)
    b = create_backend(settle_ticks=0)
    initial = apple_geometry(b)
    video = EpisodeVideo(b, out / 'video', label='IKEA original apple support | engineering only')
    samples = []
    try:
        for _ in range(300):
            b.tick()
            video.record_tick('diagnostic_not_scored')
            g, c = apple_geometry(b), apple_contacts(b)
            samples.append(dict(t=float(b.data.time), center=g['center'].tolist(), bottom=g['bottom'],
                                base_z=float(b.data.qpos[2]), reason=b.reason, **c))
            if b.reason:
                break
    finally:
        video.close()
    (out / 'host-physics.json').write_text(json.dumps(samples, indent=2) + '\n')
    b.capture_note = 'diagnostic only'
    drift = float(np.linalg.norm(np.asarray(samples[-1]['center']) - initial['center']))
    report = dict(backend='MuJoCo', original_usd=False, variant='source-aligned-apple-convex-0.18kg-v1',
                  actor_calls=0, task_success_credit=0, sim_s=float(b.data.time),
                  apple_center_drift_m=drift, final_external_support=samples[-1]['external_support'],
                  robot_safety_stop=b.reason, minimum_base_z=min(x['base_z'] for x in samples),
                  gravity=b.model.opt.gravity.tolist(), passed=b.reason is None and drift < .005 and
                  bool(samples[-1]['external_support']) and not samples[-1]['loaded_opposition'],
                  note='Original apple visual mesh/pose preserved; convex collision and .18kg mass are declared adaptations.')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
