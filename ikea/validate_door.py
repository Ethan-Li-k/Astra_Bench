"""No actor. Actual MuJoCo steps and continuous video of reset/stability."""
import json
from pathlib import Path
import mujoco
import numpy as np
from door_backend import create_backend, ROOT
from rsi.episode_video import EpisodeVideo

def main():
    out=ROOT/'diagnostics/door-v1-001';out.mkdir(parents=True,exist_ok=False)
    b=create_backend(settle_ticks=0)
    video=EpisodeVideo(b,out/'video',label='Engineering validation only | IKEA FBX no-latch v1')
    door=int(b.model.joint('ikea_door_hinge').qposadr[0])
    rows=[]
    try:
        for _ in range(300):
            b.tick();video.record_tick('diagnostic_not_scored')
            rows.append(dict(t=float(b.data.time),angle=float(b.data.qpos[door]),base_z=float(b.data.qpos[2]),reason=b.reason))
            if b.reason:break
        report=dict(backend='MuJoCo',mode='engineering_standing_closed_door_validation',actor_calls=0,
            task_success_credit=0,steps=len(rows),sim_s=float(b.data.time),reset_provenance=b.scene_setup,
            max_door_drift_rad=max(abs(r['angle']) for r in rows),minimum_base_z=min(r['base_z'] for r in rows),
            safety_stop=b.reason,gravity=b.model.opt.gravity.tolist(),passed=b.reason is None,
            contact_sweep='pending separate diagnostic')
        (out/'physics.json').write_text(json.dumps(rows,indent=2)+'\n')
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:video.close()
    # Only publish once ffmpeg exits and container is complete.
    video_path=out/'video/episode.mp4'
    manifest=json.loads((ROOT/'video-manifest.json').read_text())
    manifest['videos'].append(dict(path=str(video_path),complete=True,kind='diagnostic',task='brown_bedroom_door',
        episode='door-v1-001',backend='MuJoCo',title='闭门重力与G1站立诊断（非策略成绩）',sim_s=float(b.data.time)))
    (ROOT/'video-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
