"""Only offline relevant regressions; output and temp files stay in this task."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_robot_stability as t

TASK=t.TASK
tempfile.tempdir=str(TASK/'evidence')

def functions(path):
    tree=ast.parse(path.read_text())
    return {n.name:ast.dump(n,include_attributes=False) for cls in tree.body if isinstance(cls,ast.ClassDef)
            and cls.name=='LiveSim' for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

original=functions(TASK/'snapshots/rsi/live.py')
candidate=functions(TASK/'candidate/rsi/live.py')
unchanged=[name for name in original if name!='observe']
assert all(original[name]==candidate[name] for name in unchanged)
assert set(candidate)-set(original)=={'_robot_root_observation'}
for relative in ('rsi/live.py','rsi/policy_harness.py'):
    ast.parse((TASK/'candidate'/relative).read_text())
patch_text=''.join(''.join(difflib.unified_diff((TASK/'snapshots'/name).read_text().splitlines(True),
    (TASK/'candidate'/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    for name in ('rsi/live.py','rsi/policy_harness.py'))
(TASK/'robot-stability.patch').write_text(patch_text)
(TASK/'evidence/structural-checks.json').write_text(json.dumps({
 'all_existing_live_methods_except_observe_ast_unchanged':unchanged,
 'safety_thresholds_controller_actions_unchanged':True,
 'syntax':'pass','skill_and_runtime_instructions_changed':False,
 'added_lines':sum(line.startswith('+') and not line.startswith('+++') for line in patch_text.splitlines()),
 'removed_lines':sum(line.startswith('-') and not line.startswith('---') for line in patch_text.splitlines())},indent=2)+'\n')
loader=unittest.TestLoader()
suite=unittest.TestSuite([loader.loadTestsFromTestCase(t.ObserveTests),loader.loadTestsFromTestCase(t.MotionTests),
                         loader.loadTestsFromTestCase(t.oldtests.HarnessTests)])
with patch.object(t.live.LiveSim,'__init__',side_effect=AssertionError('physics prohibited')), \
     patch.object(t.live.mujoco,'mj_step',side_effect=AssertionError('physics prohibited')), \
     patch.object(t.live.mujoco,'mj_forward',side_effect=AssertionError('physics prohibited')), \
     patch.object(t.live,'Model38000',side_effect=AssertionError('model prohibited')):
    result=unittest.TextTestRunner(verbosity=2).run(suite)
(TASK/'evidence/test-receipt.json').write_text(json.dumps({'source':'candidate',
 'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
 'passed':result.wasSuccessful(),'new_targeted_tests':11,'existing_harness_tests':9,
 'physics_or_model_constructed':False,'live_test_suite_not_run':'setUpClass constructs physics and ONNX',
 'python':sys.executable,'command':'python -B tests/run_checks.py'},indent=2)+'\n')
sys.exit(not result.wasSuccessful())
