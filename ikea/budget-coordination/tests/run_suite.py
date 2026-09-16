import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'ikea/budget-coordination'
sys.path[:0] = [str(OUT/'tests'), str(ROOT/'tools/coordination')]
spec = importlib.util.spec_from_file_location('shared_budget', OUT/'candidate/shared_budget.py')
b = importlib.util.module_from_spec(spec); sys.modules['shared_budget'] = b; spec.loader.exec_module(b)
b.ROOT = OUT/'tests/candidate-workspace'; b.OUT = b.ROOT/'artifacts'
b.OUT.mkdir(parents=True, exist_ok=True); b.POLICY = ROOT/'ref/tasks/api-budget.json'
authority = b.ROOT/b.PARALLEL_AUTHORITY['path']; authority.parent.mkdir(parents=True, exist_ok=True)
authority.write_bytes((ROOT/b.PARALLEL_AUTHORITY['path']).read_bytes())
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'test_parallel', 'test_shared_budget', 'test_empirical_budget', 'test_approved_continuation'])
result = unittest.TextTestRunner(verbosity=2).run(suite)
(OUT/'tests/candidate-results.json').write_text(json.dumps(dict(tests_run=result.testsRun,
    passed=result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors),
    candidate_sha256=b.sha(OUT/'candidate/shared_budget.py'), synthetic_only=True,
    production_ledger_accessed=False, network_calls=0), indent=2)+'\n')
raise SystemExit(not result.wasSuccessful())
