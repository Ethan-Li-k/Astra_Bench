"""Six-second passive validation of an explicitly different robot reset; no actor."""
import hashlib
import json
from pathlib import Path
import numpy as np
from apple_backend_close_reset_v2 import ROOT,SCENE,create_backend,apple_geometry,apple_contacts
from rsi.episode_video import EpisodeVideo


def main():
    out=ROOT/'diagnostics/apple-close-reset-001';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(settle_ticks=0);start=apple_geometry(b)
    video=EpisodeVideo(b,out/'video',label='Apple closer ROBOT reset | passive engineering only')
    rows=[]
    try:
        for i in range(300):
            b.tick();video.record_tick('diagnostic_not_scored')
            geometry=apple_geometry(b);rot=b.data.xmat[b.model.body('pelvis').id].reshape(3,3)
            rows.append(dict(sim_s=float(b.data.time),center=geometry['center'].tolist(),bottom=geometry['bottom'],
                base_z=float(b.data.qpos[2]),tilt_rad=float(np.arccos(np.clip(rot[2,2],-1,1))),
                safety_reason=b.reason,**apple_contacts(b)))
            if b.reason:break
    finally:video.close()
    report=dict(kind='passive_reset_diagnostic',actor_calls=0,policy_attempts=0,task_success_credit=0,
        backend='MuJoCo',variant='source-aligned-apple-convex-close-robot-v2',original_usd=False,
        scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),sim_s=float(b.data.time),
        reset=b.reset_provenance,apple_center_drift_m=float(np.linalg.norm(np.array(rows[-1]['center'])-start['center'])),
        min_base_z=min(r['base_z'] for r in rows),max_tilt_deg=float(np.rad2deg(max(r['tilt_rad'] for r in rows))),
        terminal_external_support=rows[-1]['external_support'],robot_safety_stop=b.reason,
        limitation='Robot spawn shifted0.25m toward table; original apple/table and scene identical. No manipulation, reachability or approach success established; current apple-0001 unchanged.')
    report['passed']=bool(report['apple_center_drift_m']<.005 and report['min_base_z']>.55 and report['max_tilt_deg']<35 and b.reason is None and report['terminal_external_support'])
    (out/'host-physics.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
