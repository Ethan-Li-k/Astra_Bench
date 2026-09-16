import tempfile
import unittest
from pathlib import Path

from rsi.skill_learning import SkillMemory, CampaignLedger, usage_exhausted


class SkillLearningTests(unittest.TestCase):
    def test_shared_proposal_remains_a_candidate_with_selection_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);skill=root/'SKILL.md'
            text='---\nname: loco-manip-direct\ndescription: Learn.\n---\nUse RGB.'
            skill.write_text(text);memory=SkillMemory(root/'memory',skill)
            evidence=root/'episode/receipt.json';evidence.parent.mkdir();evidence.write_text('{}')
            row=memory.update(text+' Verify transfer.', 'new lesson', [str(evidence)],
                evidence.parent,'e1','in_progress',transfer_scope='shared_candidate',
                change_summary='Verify support independently of wrist motion.',
                selected_source_ids=['grasp_v14'])
            self.assertEqual(row['promotion_status'],'requires_cross_task_validation')
            self.assertEqual(row['selected_source_ids'],['grasp_v14'])
            self.assertTrue((memory.root/'shared_candidates/0001.md').is_file())

    def test_earliest_audited_self_success_survives_recent_failures(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); skill = root/'SKILL.md'
            text = '---\nname: loco-manip-direct\ndescription: Learn grasping.\n---\nUse RGB.'
            skill.write_text(text); memory = SkillMemory(root/'memory', skill,
                success_review=lambda episode: {'task_audit_status':'passed',
                    'completion_contract_matches':True, 'audited_task_success':True})
            evidence = root/'episode/result.json'; evidence.parent.mkdir(); evidence.write_text('{}')
            for i in range(6):
                memory.update(text, f'Attempt {i}', [str(evidence)], evidence.parent,
                              f'e{i}', 'success' if i == 1 else 'in_progress')
            versions = [x['version'] for x in memory.read()['experiences']]
            self.assertEqual(versions, [2, 4, 5, 6])

    def test_default_memory_is_compact_and_full_lesson_is_retrievable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); skill = root/'SKILL.md'
            text = '---\nname: loco-manip-direct\ndescription: Learn grasping.\n---\nUse RGB.'
            skill.write_text(text); memory = SkillMemory(root/'memory', skill)
            evidence = root/'episode/result.json'; evidence.parent.mkdir(); evidence.write_text('{}')
            lesson = 'Measured result. ' * 1000
            memory.update(text, lesson, [str(evidence)]*20, evidence.parent, 'e1', 'failure')
            brief = memory.read()['experiences'][0]
            self.assertLessEqual(len(brief['lesson']), 1600)
            self.assertTrue(brief['lesson_is_preview'])
            self.assertLessEqual(len(brief['evidence_paths']), 3)
            self.assertEqual(brief['evidence_count'], 20)
            full = memory.read(version=1)['experiences'][0]
            self.assertEqual(full['lesson'], lesson)
            self.assertEqual(len(full['evidence_paths']), 20)

    def test_usage_exhaustion_stops_retries_not_slow_inference(self):
        self.assertTrue(usage_exhausted({'error': "RuntimeError: Codex turn failed: {'codexErrorInfo': 'usageLimitExceeded'}"}))
        self.assertFalse(usage_exhausted({'error': None, 'wall_s': 1800}))
        self.assertFalse(usage_exhausted({'error': 'socket EOF'}))

    def test_overlong_skill_and_outside_evidence_do_not_modify_skill(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            skill = root/'SKILL.md'
            original = '---\nname: loco-manip-direct\ndescription: Learn visual manipulation.\n---\nUse RGB.'
            skill.write_text(original)
            memory = SkillMemory(root/'memory', skill)
            evidence = root/'episode/result.json'
            evidence.parent.mkdir()
            evidence.write_text('{}')
            for text, paths in ((original+' word'*832, [str(evidence)]),
                                (original, [str(skill)])):
                with self.assertRaises(ValueError):
                    memory.update(text, 'lesson', paths, evidence.parent, 'e1', 'failure')
                self.assertEqual(skill.read_text(), original)

    def test_accepted_revision_preserves_old_version_and_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);skill=root/'SKILL.md'
            original='---\nname: loco-manip-direct\ndescription: Learn grasping.\n---\nUse RGB.'
            skill.write_text(original);memory=SkillMemory(root/'memory',skill)
            evidence=root/'episode/result.json';evidence.parent.mkdir();evidence.write_text('{}')
            result=memory.update(original+' Verify lifting.', 'verify', [str(evidence)], evidence.parent, 'e1', 'failure')
            self.assertEqual(result['version'],1)
            self.assertEqual((root/'memory/versions/0000.md').read_text(),original)
            self.assertEqual(memory.read()['experiences'][0]['episode_id'],'e1')

    def test_ten_gate_counts_distinct_successful_episodes_only(self):
        with tempfile.TemporaryDirectory() as d:
            ledger=CampaignLedger(Path(d)/'progress.json')
            for i in range(9): ledger.record(str(i), {'success':True})
            ledger.record('0', {'success':True})
            ledger.record('failed', {'success':False})
            self.assertEqual(ledger.successes,9)
            self.assertFalse(ledger.simple_unlocked)
            ledger.record('tenth', {'success':True})
            self.assertTrue(ledger.simple_unlocked)
