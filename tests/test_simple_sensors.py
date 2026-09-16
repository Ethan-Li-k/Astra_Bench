"""A torso gyro must not masquerade as a pelvis gyro."""
import unittest
import mujoco
import numpy as np
from rsi.simple_sensors import add_pelvis_gyro


class PelvisGyroTests(unittest.TestCase):
    def test_waist_motion_does_not_enter_pelvis_gyro(self):
        spec = mujoco.MjSpec.from_string('''<mujoco><worldbody>
          <body name="pelvis"><freejoint/><geom size=".1"/>
            <body name="torso"><joint name="waist" axis="0 0 1"/>
              <geom size=".1"/><site name="imu"/>
            </body></body></worldbody>
          <sensor><gyro name="imu_gyro" site="imu"/></sensor></mujoco>''')
        add_pelvis_gyro(spec)
        model = spec.compile(); data = mujoco.MjData(model)
        data.qpos[3:7] = [.9238795325, .3826834324, 0, 0]
        data.qvel[3:6] = [.2, -.3, .4]
        data.qvel[model.joint('waist').dofadr[0]] = 2.
        mujoco.mj_forward(model, data)
        gyro = model.sensor('gyro_pelvis')
        np.testing.assert_allclose(data.sensordata[gyro.adr[0]:gyro.adr[0]+3], [.2, -.3, .4], atol=1e-8)
        torso = model.sensor('imu_gyro')
        np.testing.assert_allclose(data.sensordata[torso.adr[0]:torso.adr[0]+3], [.2, -.3, 2.4], atol=1e-8)
        self.assertEqual(model.site_bodyid[model.sensor_objid[gyro.id]], model.body('pelvis').id)


if __name__ == '__main__':
    unittest.main()
