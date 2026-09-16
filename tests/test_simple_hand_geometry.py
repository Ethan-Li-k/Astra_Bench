from types import SimpleNamespace
import unittest

import mujoco
import numpy as np

from rsi.simple_hand_geometry import finger_geometry, hand_collision_model


class HandGeometryTests(unittest.TestCase):
    def test_native_finger_bounds_use_robot_geometry_and_are_world_invariant(self):
        bodies = ''
        for side in ('left', 'right'):
            fingers = ''.join(
                f'<body name="{side}_hand_{finger}_{segment}_link" pos=".1 0 0">'
                '<geom type="mesh" mesh="pad"/></body>'
                for finger, segment in (('thumb', 2), ('index', 1), ('middle', 1)))
            bodies += f'<body name="{side}_wrist_yaw_link">{fingers}</body>'
        xml = ('<mujoco><asset><mesh name="pad" vertex="0 0 0 .02 0 0 0 .03 0 0 0 .04"/>'
               '</asset><worldbody><body><freejoint/>'+bodies+'</body>'
               '<body name="target_object" pos="9 8 7"><geom size=".5"/></body>'
               '</worldbody></mujoco>')
        model = mujoco.MjModel.from_xml_string(xml);data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        backend = SimpleNamespace(model=model, data=data)
        first = finger_geometry(backend)
        self.assertEqual(set(first), {'left', 'right'})
        for hand in first.values():
            self.assertEqual(set(hand), {'thumb', 'index', 'middle'})
            for pad in hand.values():
                np.testing.assert_allclose(pad['bounds_min_wrist_m'], [.1, 0, 0], atol=1e-7)
                np.testing.assert_allclose(pad['bounds_max_wrist_m'], [.12, .03, .04], atol=1e-7)
        data.qpos[:3] = [1, 2, 3];data.qpos[3:7] = [.5, .5, .5, .5]
        mujoco.mj_forward(model, data)
        second = finger_geometry(backend)
        for side in first:
            for finger in first[side]:
                for key in ('bounds_min_wrist_m', 'bounds_max_wrist_m', 'link_origin_wrist_m'):
                    np.testing.assert_allclose(first[side][finger][key],second[side][finger][key],atol=1e-7)

    def test_collision_model_excludes_objects_and_is_body_local(self):
        xml = '''<mujoco><asset><mesh name="tetra" vertex="0 0 0 .02 0 0 0 .03 0 0 0 .04"/></asset>
        <worldbody><body><freejoint/><geom size=".05"/>
        <body name="left_wrist_yaw_link"><geom type="box" size=".1 .2 .3"/>
          <body name="left_hand_proximal" pos=".2 0 0"><geom type="mesh" mesh="tetra"/></body></body>
        <body name="right_wrist_yaw_link"><geom type="capsule" size=".01 .03"/></body>
        </body><body name="hidden_object" pos="9 8 7"><geom size=".5"/></body></worldbody></mujoco>'''
        m = mujoco.MjModel.from_xml_string(xml);d = mujoco.MjData(m);mujoco.mj_forward(m,d)
        b = SimpleNamespace(model=m,data=d);first = hand_collision_model(b)
        self.assertEqual(set(first['bodies']), {'left_wrist_yaw_link','left_hand_proximal','right_wrist_yaw_link'})
        self.assertFalse(first['contains_object_or_contact_state'])
        v = np.array(first['bodies']['left_hand_proximal'][0]['vertices_body_m'])
        np.testing.assert_allclose(v.min(axis=0), [0,0,0], atol=1e-7)
        np.testing.assert_allclose(v.max(axis=0), [.02,.03,.04], atol=1e-7)
        d.qpos[:3]=[1,2,3];d.qpos[3:7]=[.5,.5,.5,.5];mujoco.mj_forward(m,d)
        second=hand_collision_model(b)
        # Hull vertex/face ordering may differ after floating-point transforms;
        # compare geometry extents in the invariant link frame.
        v2=np.array(second['bodies']['left_hand_proximal'][0]['vertices_body_m'])
        np.testing.assert_allclose(v2.min(axis=0),v.min(axis=0),atol=1e-7)
        np.testing.assert_allclose(v2.max(axis=0),v.max(axis=0),atol=1e-7)
