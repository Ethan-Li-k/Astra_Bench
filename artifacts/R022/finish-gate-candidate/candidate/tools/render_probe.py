"""Render saved robot states for inspection, not new simulation evidence."""
import os
os.environ.setdefault('MUJOCO_GL', 'egl')
import argparse
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image
from rsi.scalebfm import SCENE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    states = np.load(args.run / 'robot_states.npz', allow_pickle=False)['qpos']
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [0, 0, .65]
    camera.distance = 2.
    camera.azimuth = 135.
    camera.elevation = -15.
    with mujoco.Renderer(model, height=480, width=640) as renderer:
        for label, qpos in [('start', states[0]), ('end', states[-1])]:
            data.qpos[:] = qpos
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=camera)
            path = args.run / f'{label}.png'
            with path.open('xb') as output:
                Image.fromarray(renderer.render()).save(output, format='PNG')
            print(path)


if __name__ == '__main__':
    main()
