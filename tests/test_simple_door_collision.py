import unittest
from pathlib import Path

import mujoco
import numpy as np

from rsi.simple_door_collision import apply_frame_override, frame_boxes

SOURCE = Path(__file__).resolve().parents[1]/'data/simple/runtime/assets/articulated/003/output_mjcf/003.xml'
MESH = SOURCE.parent/'meshes/textured_objs/original-1.stl'


class DoorCollisionTests(unittest.TestCase):
    def test_real_frame_keeps_mass_and_hinge_dynamics_and_clears_opening(self):
        spec = mujoco.MjSpec.from_file(str(SOURCE))
        before = spec.compile()
        apply_frame_override(spec, MESH)
        after = spec.compile()
        for field in ('body_mass', 'body_inertia', 'body_ipos', 'body_iquat',
                      'jnt_range', 'jnt_axis', 'dof_damping', 'dof_frictionloss', 'dof_armature'):
            np.testing.assert_allclose(getattr(before, field), getattr(after, field), atol=1e-12)
        self.assertEqual(after.geom('link_0_collision').contype, 0)
        self.assertEqual(after.geom('link_0_collision').conaffinity, 0)
        boxes = frame_boxes(MESH)
        # Source central opening, frame solid on each of its four sides.
        for point, expected in [([0, 0, .04], False),
                                ([-.333, 0, .04], True), ([.33, 0, .04], True),
                                ([0, -.93, .04], True), ([0, .927, .04], True)]:
            inside = any(np.all(np.abs(np.array(point)-b['position']) <= np.array(b['half_size']))
                         for b in boxes)
            self.assertEqual(inside, expected)
        old = before.geom('link_0_collision')
        for i in range(4):
            bar = after.geom(f'rsi_door_frame_bar_{i}')
            for key in ('contype', 'conaffinity', 'condim', 'friction', 'solref', 'solimp', 'margin', 'gap'):
                np.testing.assert_allclose(getattr(bar, key), getattr(old, key))

    def test_unreviewed_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            frame_boxes(SOURCE)


if __name__ == '__main__':
    unittest.main()
