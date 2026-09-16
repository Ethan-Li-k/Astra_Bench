"""Calibrate against actual rasterized landmarks, not the implementation formula."""
import unittest
import mujoco
import numpy as np

from rsi.camera_calibration import render_intrinsics
from rsi.policy_harness import pixel_to_horizontal_plane


class RenderCalibrationTests(unittest.TestCase):
    def check_camera(self, camera, width, height, explicit):
        points = [(.2, .1, 0), (-.3, -.2, 0), (0, 0, 0)]
        xml = ('<mujoco><visual><global offwidth="640" offheight="480"/></visual>'
               '<worldbody><camera name="cam" pos="0 0 2" '+camera+'/>'
               + ''.join(f'<geom type="sphere" size=".012" pos="{x} {y} {z}"/>'
                         for x, y, z in points) + '</worldbody></mujoco>')
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        renderer = mujoco.Renderer(model, width=width, height=height)
        try:
            renderer.update_scene(data, camera='cam')
            intr = render_intrinsics(renderer.scene, width, height)
            renderer.enable_segmentation_rendering()
            pixels = renderer.render()
            calibration = dict(width_px=width, height_px=height,
                fovy_deg=float(model.cam_fovy[0]), position_world_m=[0, 0, 2],
                rotation_camera_to_world_row_major=np.eye(3).reshape(-1).tolist(),
                optical_convention='x_right_y_up_minus_z_forward', render_intrinsics=intr)
            old_errors = []
            old_focal = height/(2*np.tan(np.deg2rad(model.cam_fovy[0])/2))
            for i, (x, y, z) in enumerate(points):
                yy, xx = np.where((pixels[:, :, 0] == i) &
                                 (pixels[:, :, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)))
                self.assertGreater(len(xx), 5)
                actual = np.array([xx.mean()+.5, yy.mean()+.5])
                predicted = np.array([intr['fx']*x/2+intr['cx'],
                                      -intr['fy']*y/2+intr['cy']])
                self.assertLess(np.linalg.norm(actual-predicted), .75)
                np.testing.assert_allclose(pixel_to_horizontal_plane(
                    calibration, predicted-.5, 0), [x, y, z], atol=1e-8)
                old = np.array([old_focal*x/2+width/2, -old_focal*y/2+height/2])
                old_errors.append(np.linalg.norm(actual-old))
            if explicit:
                self.assertGreater(max(old_errors), 10)
            else:
                self.assertLess(max(old_errors), .75)
        finally:
            renderer.close()

    def test_explicit_intrinsics_at_original_and_video_resolutions(self):
        for width, height in [(640, 480), (640, 360)]:
            with self.subTest(width=width, height=height):
                self.check_camera('sensorsize="640 480" resolution="640 480" '
                    'focalpixel="606.29968 606.29224" principalpixel="10.76602 12.64606"',
                    width, height, True)

    def test_symmetric_fovy_unchanged(self):
        self.check_camera('fovy="43.1921458"', 640, 360, False)


if __name__ == '__main__':
    unittest.main()
