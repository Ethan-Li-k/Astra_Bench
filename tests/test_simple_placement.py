import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from rsi.simple_placement import SimplePlacementEvaluator


class PlacementTests(unittest.TestCase):
    def fixture(self):
        names = ['world', 'pelvis', 'left_wrist_yaw_link', 'right_wrist_yaw_link',
                 'left_hand_thumb_2_link', 'left_hand_index_1_link', 'box', 'basket', 'table']
        def body(name):
            i = names.index(name) if isinstance(name, str) else name
            return SimpleNamespace(id=i, name=names[i])
        model = SimpleNamespace(body=body, nbody=len(names), body_parentid=[0,0,1,1,2,2,0,0,0],
                                geom_bodyid=np.arange(len(names)))
        data = SimpleNamespace(xpos=np.zeros((len(names),3)), ncon=0, contact=[], time=0.)
        task = SimpleNamespace(uid='g1_wholebody_bend_pick_and_place_teleop',
            target=SimpleNamespace(asset=SimpleNamespace(label='box')),
            container=SimpleNamespace(asset=SimpleNamespace(label='basket')))
        b = SimpleNamespace(model=model, data=data, env=SimpleNamespace(task=task),
            reason=None, _native_task_success=False,
            gripper_command_at=lambda t: {'left': .4, 'right': 0.})
        e = SimplePlacementEvaluator(); e.reset(b)
        return b, e

    def sample(self, t, **changes):
        return dict(dict(time=t, rise_m=.06, grasped=True, nonhand_support=False,
                         robot_contact=True, container_contact=False,
                         other_support=False, native_success=False), **changes)

    def acquire(self, e):
        e.update_sample(self.sample(0)); e.update_sample(self.sample(.51))
        self.assertTrue(e._acquired)

    def place(self, t, **changes):
        return self.sample(t, **dict(dict(grasped=False, nonhand_support=True,
            robot_contact=False, container_contact=True, native_success=True), **changes))

    def test_native_initial_contact_and_passive_lift_do_not_complete(self):
        _, e = self.fixture()
        for t in (0, 1, 2, 3): e.update_sample(self.place(t))
        self.assertEqual(e.outcome(None), 'in_progress')

    def test_dwell_requires_physics_time_and_release_without_robot(self):
        _, e = self.fixture()
        for _ in range(100): e.update_sample(self.sample(0))
        self.assertFalse(e._acquired)
        self.acquire(e)
        for t in (1,2,3): e.update_sample(self.place(t, robot_contact=True, grasped=True))
        self.assertEqual(e.outcome(None), 'in_progress')
        e.update_sample(self.place(4));e.update_sample(self.place(4.99))
        self.assertEqual(e.outcome(None), 'in_progress')
        e.update_sample(self.place(5.));self.assertEqual(e.outcome(None), 'success')

    def test_drop_or_table_support_breaks_phase_continuity(self):
        for supported in (False, True):
            with self.subTest(supported=supported):
                _, e = self.fixture();self.acquire(e)
                e.update_sample(self.sample(1, grasped=supported, other_support=supported))
                e.update_sample(self.sample(1.4, grasped=supported, other_support=supported))
                for t in (2,3,4):e.update_sample(self.place(t))
                self.assertEqual(e.outcome(None), 'in_progress')

    def test_brief_release_into_container_and_safety_failure(self):
        _, e = self.fixture();self.acquire(e)
        e.update_sample(self.sample(1,grasped=False,robot_contact=False))
        e.update_sample(self.place(1.2));e.update_sample(self.place(2.2))
        self.assertEqual(e.outcome(None),'success')
        e.update_sample(self.place(2.3), 'stability_stop')
        self.assertEqual(e.outcome(None),'failure')

    def test_loaded_opposing_families_and_external_support(self):
        b,e=self.fixture();b.data.xpos[6,2]=.08
        b.data.contact=[SimpleNamespace(geom1=6,geom2=i) for i in (4,5)]
        b.data.ncon=2
        with patch('mujoco.mj_contactForce', side_effect=lambda m,d,i,out:out.__setitem__(0,.2)):
            s=e.sample(b);self.assertTrue(s['grasped']);self.assertFalse(s['nonhand_support'])
            b.data.contact.append(SimpleNamespace(geom1=6,geom2=8));b.data.ncon=3
            self.assertTrue(e.sample(b)['other_support'])
        with patch('mujoco.mj_contactForce'):
            self.assertFalse(e.sample(b)['grasped'])


if __name__=='__main__':unittest.main()
