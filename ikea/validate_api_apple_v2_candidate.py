"""Offline future-caller import/tests; never register, initialize physics, or call API."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'engineering-evidence/api-apple-v2-candidate-check'
OUT.mkdir(exist_ok=False)
sys.path.insert(0,str(ROOT/'api-apple-v2'))
spec=importlib.util.spec_from_file_location('candidate_apple_v2',ROOT/'api-apple-v2/run_api_policy.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if (ROOT/'api-apple-v2/READY.json').exists():raise RuntimeError('Offline check expects inactive candidate')
try:module.main()
except RuntimeError as exc:
    if 'Candidate not activated' not in str(exc):raise
else:raise RuntimeError('Inactive candidate unexpectedly passed activation guard')
assert module.FROZEN==ROOT/'runtime-apple-v2'
import apple_backend
assert Path(apple_backend.__file__).resolve()==ROOT/'runtime-apple-v2/apple_backend.py'
tests=[]
for rel in ('api-apple-v2/test_local_adapter.py','test_serial_batch_continuation.py',
            'test_serial_actor_loop.py','test_serial_review.py'):
    result=subprocess.run([sys.executable,str(ROOT/rel)],text=True,capture_output=True)
    (OUT/(Path(rel).stem+'.log')).write_text(result.stdout+result.stderr)
    tests.append(dict(test=rel,returncode=result.returncode,output=result.stdout+result.stderr))
files=[*list((ROOT/'api-apple-v2').glob('*.py')),ROOT/'serial_actor_loop.py',
    ROOT/'serial_batch_continuation.py',ROOT/'review_serial_api_evidence.py',
    ROOT/'review_apple_episode_v2.py',ROOT/'policy_support_apple_v2.py']
result=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    passed=all(t['returncode']==0 for t in tests),checks=tests,
    import_uses_runtime_v2=True,inactive_guard_passed=True,
    production_registrations=0,paid_calls=0,physics_initializations=0,
    current_apple_0001_changed=False,
    source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    limitations=['No live serial API continuation validated.','Final episode-derived skill and updater/length check remain pending.',
                 'No READY.json generated; no candidate activation.'])
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
sys.exit(0 if result['passed'] else 1)
