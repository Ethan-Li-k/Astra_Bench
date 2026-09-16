"""Camera-only intrinsics for MuJoCo's actual mono render viewport."""
import math


def render_intrinsics(scene, width, height):
    # mjr_render's mono view averages the stereo cameras. frustum_width is
    # a half-span when explicit sensor intrinsics are set; zero means infer
    # the horizontal span from the viewport aspect ratio.
    cameras = scene.camera
    if any(c.orthographic for c in cameras):
        raise ValueError('Perspective calibration required')
    def mean(key):
        return sum(float(getattr(c, key)) for c in cameras) / len(cameras)
    near = mean('frustum_near')
    bottom, top = mean('frustum_bottom'), mean('frustum_top')
    vertical = top - bottom
    horizontal = 2 * mean('frustum_width') or vertical * width / height
    values = {'fx': width * near / horizontal, 'fy': height * near / vertical,
              'cx': width / 2 - width * mean('frustum_center') / horizontal,
              'cy': height * top / vertical}
    if not all(math.isfinite(v) for v in values.values()) or min(values['fx'], values['fy']) <= 0:
        raise ValueError('Invalid perspective render frustum')
    return dict(values, source='MuJoCo mono render frustum at delivered RGB resolution',
                pixel_convention='pixel index (u,v) has centre (u+0.5,v+0.5)',
                version='mujoco-render-frustum-v1')
