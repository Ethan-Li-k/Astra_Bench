from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from rsi.skill_transfer import prepare_hybrid_skill, reviewed_task_sources


class SkillTransferTests(unittest.TestCase):
    def test_reviewed_transfer_accepts_version_but_rejects_changed_or_host_only_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);version=root/'artifacts/R019/source-campaign/memory/versions/0006.md'
            version.parent.mkdir(parents=True);version.write_text('Public learned grasp rule.')
            manifest=root/'sources.json'
            source={'id':'transfer_grasp','path':str(version),
                    'sha256':hashlib.sha256(version.read_bytes()).hexdigest(),
                    'applicability':'Same hand and grasp mechanism.',
                    'when_not_to_use':'No coordinate or container-placement transfer.'}
            manifest.write_text(json.dumps({'actor_access':True,'sources':[source]}))
            with patch('rsi.skill_transfer.ROOT',root):
                self.assertEqual(reviewed_task_sources(manifest)['transfer_grasp']['scope'],
                                 'reviewed_task_candidate')
                version.write_text('Changed after review.')
                with self.assertRaisesRegex(ValueError,'changed after review'):
                    reviewed_task_sources(manifest)
                host=root/'artifacts/R019/source-campaign/episode-0006/video/robot_trace.jsonl'
                host.parent.mkdir(parents=True);host.write_text('hidden state')
                source['path']=str(host);manifest.write_text(json.dumps({'actor_access':True,'sources':[source]}))
                with self.assertRaisesRegex(ValueError,'public skill version or rollout'):
                    reviewed_task_sources(manifest)

    def test_composition_preserves_task_history_and_later_agent_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);core=root/'core.md';skill=root/'task.md'
            core.write_text('---\nname: core\ndescription: Shared.\n---\nRead current RGB.')
            original='---\nname: loco-manip-direct\ndescription: Task.\n---\n## Tested experience\nFailed toe lift.\n## Audit\nKeep evidence.'
            skill.write_text(original)
            with patch('rsi.skill_transfer.CORE',core):
                prepare_hybrid_skill(root/'campaign',skill)
                self.assertIn('Failed toe lift.',skill.read_text())
                self.assertIn('Read current RGB.',skill.read_text())
                learned=skill.read_text()+'\nA new measured correction.'
                skill.write_text(learned)
                prepare_hybrid_skill(root/'campaign',skill)
                self.assertEqual(skill.read_text(),learned)
                self.assertEqual((root/'campaign/pre-hybrid-SKILL.md').read_text(),original)

    def test_overlong_composite_does_not_replace_existing_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);core=root/'core.md';skill=root/'task.md'
            core.write_text('---\nname: core\n---\n'+'word '*900)
            skill.write_text('existing skill')
            with patch('rsi.skill_transfer.CORE',core):
                with self.assertRaises(ValueError):prepare_hybrid_skill(root/'campaign',skill)
            self.assertEqual(skill.read_text(),'existing skill')
