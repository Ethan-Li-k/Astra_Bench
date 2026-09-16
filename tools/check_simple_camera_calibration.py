"""Zero-action native SIMPLE camera integration; no policy or task credit."""
import json
from pathlib import Path
from types import SimpleNamespace

from rsi.policy_harness import MujocoImageCapture
from rsi.simple_environment import make_simple_env


def main():
    root = Path('artifacts/R019/camera-calibration-review/native-integration-01')
    root.mkdir(parents=True, exist_ok=False)
    env = make_simple_env('simple/G1WholebodyPickAndPlaceAppleTeleop-v0')
    capture = None
    try:
        env.reset(seed=8)
        b = SimpleNamespace(model=env.unwrapped.mjModel, data=env.unwrapped.mjData)
        names = tuple(b.model.camera(i).name for i in range(b.model.ncam)
                      if 'head' in b.model.camera(i).name)
        capture = MujocoImageCapture(b, cameras=names, width=640, height=360)
        packet = capture(root)
        assert len(packet) == 2
        for camera in packet:
            intr = camera['calibration']['render_intrinsics']
            assert intr['version'] == 'mujoco-render-frustum-v1'
            assert abs(intr['fx']/intr['fy'] - 4/3) < .01
        result = dict(status='passed', additional_physics_steps=0,
                      native_reset_sim_s=float(b.data.time), actor_actions=0,
                      model_calls=0, task_credit=0, images=packet)
        (root/'result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    finally:
        if capture is not None:
            capture.close()
        env.close()


if __name__ == '__main__':
    main()
