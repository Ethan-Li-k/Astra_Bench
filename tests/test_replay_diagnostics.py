import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReplayDiagnosticTests(unittest.TestCase):
    def test_invalid_gripper_override_is_rejected_before_creating_run(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'must-not-start'
            script = Path(__file__).resolve().parents[1]/'tools/replay_direct_episode.py'
            result = subprocess.run([sys.executable, str(script), '--source', directory,
                '--output', str(output), '--replace-right-closure', '.45', '1.5'],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('closure values must be finite and in [0, 1]', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
