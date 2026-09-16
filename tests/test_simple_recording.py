import unittest
from types import SimpleNamespace

import mujoco
import numpy as np

from rsi.simple_recording import external_robot_contacts, named_render_state, restore_named_render_state


class SimpleRecordingTests(unittest.TestCase):
    def test_host_contact_audit_keeps_objects_and_filters_floor_and_self(self):
        model = mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
          <geom name="floor" type="plane" size="2 2 .1"/>
          <body name="pelvis" pos="0 0 .08"><freejoint/>
            <geom name="robot" type="sphere" size=".1"/>
            <body name="hand" pos=".2 0 0"><joint type="slide"/>
              <geom name="finger" type="sphere" size=".1"/></body>
          </body>
          <body name="object" pos=".35 0 .08"><freejoint/>
            <geom name="object_geom" type="sphere" size=".1"/></body>
        </worldbody><contact><pair geom1="robot" geom2="finger"/></contact></mujoco>''')
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        self.assertGreater(data.ncon, 1)
        rows = external_robot_contacts(model, data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['robot_body'], 'hand')
        self.assertEqual(rows[0]['other_geom'], 'object_geom')
        self.assertLess(rows[0]['distance_m'], 0)
        self.assertGreaterEqual(rows[0]['normal_force_n'], 0)

    def test_reordered_render_joints_preserve_door_and_free_robot_root(self):
        root = '<body name="robot"><freejoint name="root"/><geom type="sphere" size=".1"/></body>'
        door = '<body name="door"><joint name="hinge"/><geom type="box" size=".02 .2 .3"/></body>'
        def model(parts):
            return mujoco.MjModel.from_xml_string('<mujoco><worldbody>'+parts+'</worldbody></mujoco>')
        source, target = model(root+door), model(door+root)
        before, after = mujoco.MjData(source), mujoco.MjData(target)
        before.qpos[source.joint('hinge').qposadr[0]] = .6
        before.qpos[source.joint('root').qposadr[0]] = 1.2
        state = named_render_state(SimpleNamespace(model=source, data=before))
        restore_named_render_state(target, after, state)
        self.assertEqual(after.qpos[target.joint('hinge').qposadr[0]], .6)
        self.assertEqual(after.qpos[target.joint('root').qposadr[0]], 1.2)
        np.testing.assert_allclose(after.xpos[target.body('robot').id], [1.2, 0, 0])


if __name__ == '__main__':
    unittest.main()
