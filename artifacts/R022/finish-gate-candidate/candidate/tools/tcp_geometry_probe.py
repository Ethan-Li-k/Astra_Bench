"""Robot-only FK inspection of DEX3 collision geometry; not a grasp test."""
import argparse
import json
import os
import hashlib
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from PIL import Image
from rsi.scalebfm import SCENE
from locomanip.utils.dex3 import DEX3_CLOSED_POS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    fingers = list(DEX3_CLOSED_POS)
    s = SimpleNamespace(model=model, data=data,
        fq=np.array([model.joint(n).qposadr[0] for n in fingers]),
        closed=np.array([DEX3_CLOSED_POS[n] if n.startswith('right_') else 0. for n in fingers]))
    mujoco.mj_forward(model,data)
    (args.output/'sources').mkdir()
    for source in (Path(__file__),SCENE):
        (args.output/'sources'/source.name).write_bytes(source.read_bytes())
    body = s.model.body('right_wrist_yaw_link').id
    pad_names = ['right_hand_thumb_2_collision', 'right_hand_index_1_pad_collision',
                 'right_hand_middle_1_pad_collision']
    pads = [s.model.geom(name).id for name in pad_names]
    renderer = mujoco.Renderer(s.model, height=480, width=640)
    rows = []
    try:
        for closure in (0., .25, .5, .75, 1.):
            s.data.qpos[s.fq] = s.closed*closure
            mujoco.mj_forward(s.model, s.data)
            origin = s.data.xpos[body]
            rotation = s.data.xmat[body].reshape(3, 3)
            centers = (s.data.geom_xpos[pads]-origin) @ rotation
            midpoint = .5*(centers[0]+.5*(centers[1]+centers[2]))
            distances = []
            for opposing in pads[1:]:
                segment = np.zeros(6)
                distance = mujoco.mj_geomDistance(s.model,s.data,pads[0],opposing,1.,segment)
                distances.append({'opposing_geom':s.model.geom(opposing).name,
                    'signed_surface_distance_m':float(distance)})
            rows.append({'closure': closure, 'collision_centers_wrist_m': dict(zip(pad_names, centers.tolist())),
                'surface_distances': distances,
                'opposing_centers_distance_m': float(np.linalg.norm(centers[0]-.5*(centers[1]+centers[2]))),
                'midpoint_wrist_m': midpoint.tolist(),
                'palm_site_wrist_m': ((s.data.site_xpos[s.model.site('right_palm').id]-origin)@rotation).tolist(),
                'meaning': 'Mixed thumb capsule / opposing pad center proxy; not validated grasp TCP. Pair surface distance alone does not certify object clearance.'})
            camera = mujoco.MjvCamera()
            camera.lookat[:] = origin + rotation @ np.array([.12, 0, 0])
            camera.distance = .42
            camera.azimuth = 125
            camera.elevation = -20
            renderer.update_scene(s.data, camera=camera)
            Image.fromarray(renderer.render()).save(args.output / f'closure-{closure:.2f}.png')
    finally:
        renderer.close()
    (args.output / 'geometry.json').write_text(json.dumps({
        'scope': 'robot-only kinematics; no simulation rollout or object-directed action',
        'wrist_frame': 'right_wrist_yaw_link',
        'physical_steps': 0, 'model_inference_calls': 0,
        'sources': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),SCENE)},
        'samples': rows, 'llm_calls': 0}, indent=2))
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
