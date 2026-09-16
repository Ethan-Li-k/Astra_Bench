import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'artifacts/R022/finish-gate-applied'
modules = ['test_learning_host', 'test_finish_gate', 'test_continuous_control', 'test_reference_sequence']
files = ['tools/learn_grasp_skill.py'] + ['tests/'+name+'.py' for name in modules]
def hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
before = hashes()
print('Interpreter:', sys.executable, flush=True)
print('Backend: unit-test fakes and pure numerical boundary checks; no live simulation/model.', flush=True)
print('Modules:', ', '.join(modules), flush=True)
suite = unittest.TestSuite()
for name in modules:
    module = importlib.import_module(name)
    assert Path(module.__file__).resolve() == ROOT/'tests'/f'{name}.py'
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
import tools.learn_grasp_skill as host_module
assert Path(host_module.__file__).resolve() == ROOT/'tools/learn_grasp_skill.py'
started = time.monotonic()
result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
after = hashes()
receipt = {
    'interpreter': sys.executable,
    'modules': modules,
    'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped),
    'successful': result.wasSuccessful() and before == after,
    'elapsed_s': time.monotonic()-started,
    'source_sha256_before': before, 'source_sha256_after': after,
    'sources_unchanged_during_tests': before == after,
    'backend': 'unit_test_fakes_and_pure_numerical_checks',
    'physical_attempts': 0, 'physical_successes': 0,
}
(OUT/'test-results.json').write_text(json.dumps(receipt, indent=2)+'\n')
raise SystemExit(0 if receipt['successful'] else 1)
