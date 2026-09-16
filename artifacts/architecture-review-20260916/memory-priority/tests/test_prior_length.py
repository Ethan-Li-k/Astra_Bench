import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
C = ROOT / 'combined'
spec = importlib.util.spec_from_file_location('candidate_memory', C/'rsi/skill_learning.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def load_runner(path):
    tree = ast.parse(path.read_text())
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_episode')
    ns = {'LearningHost': None, 'PYTHON': None,
          'validate_policy_instructions': m.validate_policy_instructions}
    exec(compile(ast.Module(body=[func], type_ignores=[]), str(path), 'exec'), ns)
    return ns['run_episode']


class CandidateChecks(unittest.TestCase):
    def test_combined_candidate_passes(self):
        skill = (C/'loco-manip-direct/SKILL.md').read_text()
        runtime = (C/'runtime-instructions.txt').read_text()
        size = m.validate_policy_instructions(skill, runtime)
        (ROOT/'checks/candidate-length.json').write_text(json.dumps({
            'skill': m.skill_size(skill), 'runtime': m.skill_size(runtime),
            'combined': size, 'caps': {'words':831,'characters':6250,'non_whitespace':5357}}, indent=2))

    def test_character_cap(self):
        with self.assertRaises(ValueError):
            m.validate_policy_instructions('x' + ' '*6250)

    def test_nonwhitespace_cap(self):
        m.validate_policy_instructions('x'*5357)
        with self.assertRaises(ValueError):
            m.validate_policy_instructions('x'*5358)

    def test_word_cap(self):
        m.validate_policy_instructions('x '*831)
        with self.assertRaises(ValueError):
            m.validate_policy_instructions('x '*832)

    def test_preflight_has_no_episode_or_host_side_effect(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'checks') as d:
            p=Path(d); skill=p/'skill.md'; skill.write_text('x '*600)
            calls=[]
            def host(*a, **k):
                calls.append(True)
                raise RuntimeError('host created')
            memory=types.SimpleNamespace(skill=skill)
            with self.assertRaisesRegex(ValueError, 'Combined'):
                load_runner(C/'tools/learn_grasp_skill.py')(p/'episode',memory,'id',0,host_factory=host)
            self.assertFalse((p/'episode').exists())
            self.assertEqual(calls, [])

    def test_baseline_reproduces_missing_preflight(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'checks') as d:
            p=Path(d); skill=p/'skill.md'; skill.write_text('x '*600)
            def host(*a, **k):
                raise RuntimeError('host created before checking combined instructions')
            with self.assertRaisesRegex(RuntimeError, 'host created'):
                load_runner(C/'baseline/tools/learn_grasp_skill.py')(
                    p/'episode',types.SimpleNamespace(skill=skill),'id',0,host_factory=host)
            self.assertTrue((p/'episode').is_dir())

    def test_failed_update_preserves_all_memory(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'checks') as d:
            p=Path(d); skill=p/'SKILL.md'; skill.write_text('---\nname: loco-manip-direct\ndescription: test\n---\nshort\n')
            mem=m.SkillMemory(p/'memory',skill)
            mem.runtime_instructions=(C/'runtime-instructions.txt').read_text()
            evidence=p/'rollout'; evidence.mkdir(); (evidence/'public.json').write_text('{}')
            before={str(f.relative_to(p)): f.read_bytes() for f in p.rglob('*') if f.is_file()}
            oversized=skill.read_text()+'x '*600
            with self.assertRaisesRegex(ValueError, 'Combined'):
                mem.update(oversized,'lesson',[evidence/'public.json'],evidence,'e1','in_progress')
            self.assertEqual(before,{str(f.relative_to(p)): f.read_bytes() for f in p.rglob('*') if f.is_file()})

    def test_valid_update_preserves_versions_and_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'checks') as d:
            p=Path(d); skill=p/'SKILL.md'; original='---\nname: loco-manip-direct\ndescription: test\n---\nshort\n';skill.write_text(original)
            mem=m.SkillMemory(p/'memory',skill);mem.runtime_instructions=(C/'runtime-instructions.txt').read_text()
            evidence=p/'rollout'; evidence.mkdir(); (evidence/'public.json').write_text('{}')
            row=mem.update(original+'new\n','observed failure',[evidence/'public.json'],evidence,'e1','in_progress',selected_source_ids=['public1'])
            self.assertEqual((p/'memory/versions/0000.md').read_text(),original)
            self.assertEqual(row['selected_source_ids'],['public1'])
            self.assertEqual(mem.read()['version'],1)
            self.assertEqual(mem.read()['combined_instruction_size'],m.skill_size(skill.read_text()+mem.runtime_instructions))


if __name__ == '__main__':
    unittest.main(verbosity=2)
