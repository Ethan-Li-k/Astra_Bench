import tempfile
import unittest
from unittest.mock import patch
from simple.scenes.hssd import HssdSceneManager
from rsi.simple_environment import load_hssd_metadata


class SceneMetadataTests(unittest.TestCase):
    def test_mujoco_metadata_matches_native_loader_without_usd_operations(self):
        manager = HssdSceneManager()
        with tempfile.TemporaryDirectory() as directory:
            with patch('simple.scenes.hssd.resolve_data_path', return_value=directory):
                native = manager.load('hssd:scene0')
        with patch('simple.scenes.hssd.resolve_data_path', side_effect=AssertionError('USD access')):
            metadata = load_hssd_metadata(manager, 'hssd:scene0')
        for field in ('uid','name','conf','data_dir','center_offset','center_orientation'):
            self.assertEqual(getattr(native,field),getattr(metadata,field))


if __name__=='__main__': unittest.main()
