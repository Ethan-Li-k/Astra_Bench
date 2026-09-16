import unittest
from types import SimpleNamespace as NS
import mujoco
import numpy as np
from rsi.simple_door_setup import configure_push_side


class DoorSetupTests(unittest.TestCase):
    def test_flip_preserves_closed_panel_center_and_opens_away(self):
        model = mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
          <body name="pelvis" pos="-1 0 .75"><freejoint/><geom size=".1"/></body>
          <body name="articulate_base"><body name="leaf" pos="0 -.5 1">
            <joint name="articulate_joint_1" axis="0 0 1" range="0 1.5"/>
            <geom pos="0 .5 0" type="box" size=".02 .5 .8"/>
          </body></body></worldbody></mujoco>''')
        data = mujoco.MjData(model)
        data.joint('articulate_joint_1').qpos[0] = .1
        data.time = 3.7
        mujoco.mj_forward(model, data)
        actor = NS(pose=NS(position=[0,0,0], quaternion=[1,0,0,0]))
        runtime = NS(mjModel=model, mjData=data, task=NS(layout=NS(actors={'articulated':actor})))
        initial = data.xipos[model.body('leaf').id].copy()
        result = configure_push_side(runtime)
        np.testing.assert_allclose(data.xipos[model.body('leaf').id], initial, atol=1e-9)
        self.assertLess(result['opening_dot_before'], 0)
        self.assertGreater(result['opening_dot_after'], 0)
        self.assertEqual(data.time, 3.7)
        self.assertEqual(float(data.joint('articulate_joint_1').qpos[0]), .1)


if __name__ == '__main__': unittest.main()
