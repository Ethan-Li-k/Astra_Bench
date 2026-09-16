"""Supplemental camera rendering of an existing recorded physics trajectory."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image,ImageDraw
from ground_task import ROOT,GroundSim

def main():
    p=argparse.ArgumentParser();p.add_argument('--episode',required=True)
    p.add_argument('--trace-path',type=Path);p.add_argument('--output-dir',type=Path)
    p.add_argument('--wide-azimuth',type=float,default=235.)
    p.add_argument('--feet-azimuth',type=float,default=55.);args=p.parse_args()
    source=args.trace_path or ROOT/'campaign'/args.episode/'video/robot_trace.jsonl'
    out=args.output_dir or ROOT/'artifacts'/(args.episode+'-feet-render')
    if ROOT not in out.resolve().parents:raise ValueError('Output must remain inside this task root')
    out.mkdir(parents=True,exist_ok=False)
    b=GroundSim();m,d=b.model,b.data
    renderer=mujoco.Renderer(m,height=480,width=640)
    camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance=2.1;camera.azimuth=args.wide_azimuth;camera.elevation=-18
    camera.lookat[:]=[0.,0.,.5]
    encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-n','-f','rawvideo',
        '-pixel_format','rgb24','-video_size','1280x544','-framerate','25','-i','pipe:0',
        '-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',
        '-movflags','+faststart',str(out/'feet.mp4')],stdin=subprocess.PIPE)
    frames=0;max_restore_error=0.
    try:
        for i,line in enumerate(source.open()):
            if i%2:continue
            row=json.loads(line);state=row['host_render_state']
            d.qpos[:]=state['qpos'];d.qvel[:]=state['qvel'];d.time=row['sim_s']
            mujoco.mj_forward(m,d) # NO mj_step; this is rendering only.
            max_restore_error=max(max_restore_error,float(abs(d.qpos-np.array(state['qpos'])).max()))
            camera.lookat[:]=[d.qpos[0],d.qpos[1],.45]
            frame=Image.new('RGB',(1280,544),(20,23,27));draw=ImageDraw.Draw(frame)
            draw.text((12,8),'RECORDED TRAJECTORY RE-RENDER | '+args.episode+' | MuJoCo | NO NEW PHYSICS',fill='white')
            draw.text((12,29),f"original sim {row['sim_s']:.2f}s | original status {row['status']['status']} | two diagnostic views, never actor input",fill='white')
            renderer.update_scene(d,camera=camera);frame.paste(Image.fromarray(renderer.render()),(0,64))
            camera.azimuth=args.feet_azimuth;camera.elevation=-10;camera.distance=1.45;camera.lookat[2]=.22
            renderer.update_scene(d,camera=camera);frame.paste(Image.fromarray(renderer.render()),(640,64))
            camera.azimuth=args.wide_azimuth;camera.elevation=-18;camera.distance=2.1
            encoder.stdin.write(frame.tobytes())
            if frames==0:frame.save(out/'initial.png')
            last=frame;frames+=1
        last.save(out/'final.png')
    finally:
        encoder.stdin.close();code=encoder.wait(timeout=30);renderer.close()
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'backend':'MuJoCo','physics_rollout':False,'new_task_successes':0,'frames':frames,
        'fps':25,'max_qpos_restore_error':max_restore_error,'encoder_exit':code,
        'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'wide_azimuth_deg':args.wide_azimuth,'feet_azimuth_deg':args.feet_azimuth,
        'purpose':'Foot visibility supplement; primary actual-physics video remains campaign episode.mp4'}
    (out/'render_manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    assert code==0

if __name__=='__main__':main()
