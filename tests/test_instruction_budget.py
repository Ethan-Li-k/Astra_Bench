"""Check the actual runner entrypoint and memory transaction boundary."""
import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from rsi.skill_learning import SkillMemory, skill_size, validate_policy_instructions

ROOT = Path(__file__).resolve().parents[1]
SKILL = '---\nname: loco-manip-direct\ndescription: test\n---\nUse current RGB.\n'


def runner_parts():
    path = ROOT/'tools/learn_grasp_skill.py'
    tree = ast.parse(path.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_episode')
    runtime = next(ast.literal_eval(n.value) for n in ast.walk(function)
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name)
                   and t.id == 'immutable' for t in n.targets))
    namespace = dict(LearningHost=None, PYTHON=None,
                     validate_policy_instructions=validate_policy_instructions,
                     NETWORK_CONTINUATION='Observe; next_call: ')
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return runtime, namespace['run_episode']


class InstructionBudgetTests(unittest.TestCase):
    def test_all_caps_include_runtime(self):
        for text in ['x'+' '*6250, 'x'*5358, 'x '*832]:
            with self.subTest(size=skill_size(text)):
                with self.assertRaises(ValueError):
                    validate_policy_instructions(text)
        runtime, _ = runner_parts()
        self.assertLess(skill_size(SKILL+'x '*600)['words'], 831)
        with self.assertRaises(ValueError):
            validate_policy_instructions(SKILL+'x '*600, runtime)

    def test_preflight_does_not_create_episode_or_host(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp') as d:
            p = Path(d); skill = p/'SKILL.md'; skill.write_text(SKILL+'x '*600)
            calls = []
            def host(*args, **kwargs):
                calls.append(True)
                raise AssertionError('host initialized')
            _, runner = runner_parts()
            with self.assertRaisesRegex(ValueError, 'Combined'):
                runner(p/'episode', SimpleNamespace(skill=skill), 'e1', 0, host_factory=host)
            self.assertFalse((p/'episode').exists())
            self.assertEqual(calls, [])

    def test_invalid_revision_is_atomic_and_valid_revision_keeps_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp') as d:
            p = Path(d); skill = p/'SKILL.md'; skill.write_text(SKILL)
            memory = SkillMemory(p/'memory', skill)
            memory.runtime_instructions = runner_parts()[0]
            evidence = p/'rollout'; evidence.mkdir(); (evidence/'public.json').write_text('{}')
            before = {str(f): f.read_bytes() for f in p.rglob('*') if f.is_file()}
            with self.assertRaisesRegex(ValueError, 'Combined'):
                memory.update(SKILL+'x '*600, 'lesson', [evidence/'public.json'], evidence, 'e1', 'in_progress')
            self.assertEqual(before, {str(f): f.read_bytes() for f in p.rglob('*') if f.is_file()})
            row = memory.update(SKILL+' Reobserve.', 'lesson', [evidence/'public.json'],
                                evidence, 'e1', 'in_progress', selected_source_ids=['task_current_skill'])
            self.assertEqual(row['selected_source_ids'], ['task_current_skill'])
            self.assertEqual((memory.root/'versions/0000.md').read_text(), SKILL)
            self.assertEqual(row['instruction_budget']['combined_size'],
                             skill_size(skill.read_text()+memory.runtime_instructions))
            self.assertEqual(memory.read()['combined_instruction_size'],
                             row['instruction_budget']['combined_size'])


if __name__ == '__main__':
    unittest.main()
