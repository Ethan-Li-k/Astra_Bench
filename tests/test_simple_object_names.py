from types import SimpleNamespace
import unittest

from simple.core.actor import ObjectActor
from rsi.simple_object_names import unique_object_labels


class ObjectNameTests(unittest.TestCase):
    def actor(self, asset, position):
        actor = ObjectActor.__new__(ObjectActor)
        actor.asset = asset
        actor.pose = SimpleNamespace(position=position)
        return actor

    def test_duplicate_preserves_target_cached_assets_and_geometry(self):
        asset = SimpleNamespace(uid='12', label='apple', name='apple',
                                description=None, collision_meshes_mujoco=['mesh.obj'])
        distractor = self.actor(asset, [1., 2., 3.])
        target = self.actor(asset, [4., 5., 6.])
        actors = {'distractor0': distractor, 'target': target}
        changes = unique_object_labels(actors)
        self.assertEqual(target.asset.label, 'apple')
        self.assertEqual(asset.label, 'apple')
        self.assertEqual(distractor.asset.label, 'rsi_aux_0000')
        self.assertNotIn(target.asset.label, distractor.asset.label)
        self.assertIsNot(distractor.asset, asset)
        self.assertIs(distractor.asset.collision_meshes_mujoco, asset.collision_meshes_mujoco)
        self.assertEqual(distractor.pose.position, [1., 2., 3.])
        self.assertEqual(changes[0]['original'], 'apple')
        self.assertEqual(unique_object_labels(actors), [])

    def test_generated_name_cannot_collide_with_existing_label(self):
        def asset(label):
            return SimpleNamespace(uid=label, label=label, name=label, description=None)
        actors = {key: self.actor(asset(label), [0, 0, 0]) for key, label in
                  [('target', 'apple'), ('d0', 'apple'), ('d1', 'rsi_aux_0000')]}
        unique_object_labels(actors)
        self.assertEqual(actors['d0'].asset.label, 'rsi_aux_0001')


if __name__ == '__main__':
    unittest.main()
