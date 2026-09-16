"""Actual simulation frames; diagnostic track view never goes to the actor."""
import json
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageDraw

from rsi.policy_harness import MujocoImageCapture


class EpisodeVideo(MujocoImageCapture):
    def __init__(self, backend, output, *, label='GPT-6 Astra Direct | no demonstration',
                 cameras=('head_cam', 'right_wrist_cam'), video_cameras=('track', 'head_cam'),
                 width=640, height=480, extra_trace=None):
        super().__init__(backend, cameras=cameras, width=width, height=height)
        self.width, self.height = width, height
        self.video_cameras, self.extra_trace = video_cameras, extra_trace
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        self.ticks = self.frames = 0
        self.label = label
        self.started = time.monotonic()
        self.trace = (output/'robot_trace.jsonl').open('w', buffering=1)
        self.encoder_log = (output/'ffmpeg.log').open('w')
        self.encoder = subprocess.Popen([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-n',
            '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{width*2}x{height+64}',
            '-framerate', '25', '-i', 'pipe:0', '-an', '-c:v', 'libx264',
            '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(output/'episode.mp4')],
            stdin=subprocess.PIPE, stderr=self.encoder_log)
        self.record_tick('in_progress')

    def record_tick(self, native_outcome):
        backend = self.backend
        status = {k: v for k, v in backend.status().items() if not k.startswith('_')}
        row = {'sim_s': float(backend.data.time),
               'wall_s_since_recording': time.monotonic()-self.started,
               'status': status, 'native_outcome': native_outcome,
               'reference': backend.reference_pose_at(backend.data.time).to_mapping(),
               'measured_four_point_position_world_m':
                   backend.data.xpos[backend.adapter.body_ids[backend.four]].tolist(),
               'gripper_command': backend.gripper_command_at(backend.data.time)}
        if self.extra_trace is not None:
            row['host_render_state'] = self.extra_trace(backend)
        self.trace.write(json.dumps(row)+'\n')
        if self.ticks % 2 == 0:
            frame = Image.new('RGB', (self.width*2, self.height+64), (20, 23, 27))
            for x, camera in zip((0, self.width), self.video_cameras):
                self.renderer.update_scene(backend.data, camera=camera)
                frame.paste(Image.fromarray(self.renderer.render()), (x, 64))
            draw = ImageDraw.Draw(frame)
            draw.text((12, 6), self.label+' | MuJoCo | simulation pauses during planning', fill='white')
            draw.text((12, 25), f"sim {row['sim_s']:.2f}s  wall {row['wall_s_since_recording']:.1f}s  "
                      f"{status.get('command_id', '')}  {status['status']}  native={native_outcome}", fill='white')
            draw.text((12, 44), 'Diagnostic camera (not actor input)', fill='white')
            draw.text((self.width+12, 44), 'Actor head RGB', fill='white')
            self.encoder.stdin.write(frame.tobytes())
            self.frames += 1
        self.ticks += 1

    def close(self):
        self.encoder.stdin.close()
        code = self.encoder.wait(timeout=30)
        self.trace.close()
        self.encoder_log.close()
        super().close()
        if code:
            raise RuntimeError(f'Video encoding failed with exit code {code}')
