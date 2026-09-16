"""Reuse the original 12 fixtures and add one real-schema regression with negative cases."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from dashboard import Dashboard, RSI

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('previous_fixtures', OUT.parent/'explicit-blockers/test_explicit_blockers.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
previous.OUT = OUT  # Original fixtures and their logs remain untouched.


class CandidateDeliveryTests(previous.ExplicitBlockerTests):
    def test_actual_result_progress_delivery_combination(self):
        sources = {name:json.loads((OUT/'public-source-snapshot'/name).read_text())
                   for name in ('result.json','progress.json','manager-status.json')}
        result, progress = sources['result.json'], sources['progress.json']
        self.assertNotIn('ready', result)
        self.assertEqual(result['status'], 'candidate_only')
        self.assertEqual(progress['stage'], 'bounded_delivery_complete')
        self.nt_published(); original_nt = self.d.framework()['nt_publication']
        for name, doc in sources.items():
            self.write(previous.STABILITY+name, doc, at=1800000000 if name=='manager-status.json' else 1800000060)
        d = self.d.framework()
        (OUT/'actual-schema-observed.json').write_text(json.dumps({k:d[k] for k in
            ('current_work','summary','problem','next','nt_publication')}, ensure_ascii=False, indent=2)+'\n')
        self.assertEqual(d['current_work']['state'], 'candidate-delivered')
        self.assertIn('候选已交付', d['summary'])
        self.assertIn('候选已完成', d['problem'])
        self.assertNotIn('正在核对', d['problem'])
        self.assertNotIn('完成独立候选', d['next'])
        self.assertIn('唯一发布者', d['next'])
        self.assertIn('自然边界', d['next'])
        self.assertIn('未部署', d['problem'])
        self.assertIn('物理收益未验证', d['problem'])
        self.assertIn('已排队', json.dumps(d, ensure_ascii=False))
        self.assertIn('负责人尚未确认', json.dumps(d, ensure_ascii=False))
        self.assertIs(d['current_work']['deployed'], False)
        self.assertIs(d['current_work']['physical_benefit_verified'], False)
        self.assertEqual(d['nt_publication'], original_nt)
        # Unknown or contradictory combinations must not reuse the completed manager text.
        variants = [
            ('wrong_result_id', {'candidate_id':'UNRELATED-V1'}, {}),
            ('missing_result_id', {'candidate_id':None}, {}),
            ('different_progress_id', {}, {'candidate_id':'UNRELATED-V1'}),
            ('wrong_stage', {}, {'stage':'mapping_and_reproduction'}),
            ('missing_stage', {}, {'stage':None}),
            ('no_result_queue', {'delivery':dict(result['delivery'], queued=False)}, {}),
            ('no_progress_queue', {}, {'delivery_queued':False}),
            ('unknown_handoff', {'delivery':None}, {}),
            ('unknown_candidate_status', {'status':'unknown'}, {}),
            ('contradictory_integration', {'delivery':dict(result['delivery'], integrated=True)}, {}),
        ]
        for name, rpatch, ppatch in variants:
            with self.subTest(name=name):
                self.write(previous.STABILITY+'result.json', dict(copy.deepcopy(result), **rpatch))
                self.write(previous.STABILITY+'progress.json', dict(copy.deepcopy(progress), **ppatch))
                other = self.d.framework()
                self.assertNotEqual(other['current_work']['state'], 'candidate-delivered')
                self.assertEqual(other['nt_publication'], original_nt)
        # Only the expressly authorized function may change in this maintenance turn.
        before = json.loads((OUT/'scope-before.json').read_text())
        cls = next(n for n in ast.parse((RSI/'human-feedback/tools/dashboard.py').read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name=='Dashboard')
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name!='stability_observation':
                self.assertEqual(hashlib.sha256(ast.dump(node).encode()).hexdigest(), before['adapter_methods'][node.name], node.name)


if __name__ == '__main__': unittest.main(verbosity=2)
