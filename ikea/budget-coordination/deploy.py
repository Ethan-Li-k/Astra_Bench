"""One explicit local publication after reboot. No process control or API calls."""
import ast
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path('/home/galbot/lizekai/RSI')
OUT = ROOT/'ikea/budget-coordination'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def check(ok, message):
    if not ok: raise SystemExit(message)


def callers():
    rows = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        try:
            if not (proc/'exe').resolve().name.startswith('python'): continue
            cwd = (proc/'cwd').resolve()
            scripts = []
            for arg in (proc/'cmdline').read_bytes().split(b'\0')[1:]:
                if not arg.endswith(b'.py'): continue
                path = (cwd/arg.decode()).resolve()
                if ROOT in path.parents: scripts.append(str(path.relative_to(ROOT)))
            if scripts: rows.append(dict(pid=int(proc.name), scripts=scripts))
        except (OSError, PermissionError): continue
    return rows


def main():
    check(not (OUT/'deployment.json').exists(), 'Already published; do not repeat')
    tests = read(OUT/'tests/candidate-results.json')
    source = OUT/'candidate/shared_budget.py'; target = ROOT/'tools/coordination/shared_budget.py'
    check(tests['passed'] and tests['tests_run'] == 49 and sha(source) == tests['candidate_sha256'],
          'Final tested candidate required')
    baseline = read(OUT/'protected-before-deploy.json')
    check(all(sha(ROOT/p) == digest for p, digest in baseline.items()), 'Protected source or ledger changed; reassess')
    incident = read(ROOT/'ikea/recovery-20260916/incident.json')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    check(boot == incident['boot_id'], 'Unexpected boot boundary')
    processes = callers()
    # Unknown new Python actors fail closed too. These two watcher scripts do not call the API.
    safe = {'ikea/continuation/watch.py', 'ikea/progress_watch.py',
            'ikea/budget-coordination/deploy.py', 'human-feedback/tools/server.py',
            'api-ground-to-table/progress_server.py'}
    check(all(script in safe or 'progress' in Path(script).name and 'server' in Path(script).name
              for row in processes for script in row['scripts']),
          'Other RSI Python caller present; inspect explicitly before publication')
    spec = importlib.util.spec_from_file_location('candidate_preflight', source)
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b); b.ROOT = ROOT
    legacy = []
    for name in ('api-ground-001', 'api-ground-002'):
        path = ROOT/'artifacts/R021'/name/'batch.json'
        ref = dict(path=str(path.relative_to(ROOT)), sha256=sha(path))
        check(b.reviewed_batch(ref)['batch_id'] == name, 'Legacy batch no longer readable')
        legacy.append(ref)
    old_ast = ast.parse((OUT/'before/shared_budget.py').read_text())
    new_ast = ast.parse(source.read_text())
    def methods(tree):
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BudgetLedger')
        return {n.name: ast.dump(n, include_attributes=False) for n in cls.body if isinstance(n, ast.FunctionDef)}
    old, new = methods(old_ast), methods(new_ast)
    unchanged = ['transaction', 'reserve', 'begin', 'cancel', 'settle', 'acknowledge_report', 'status']
    check(all(old[k] == new[k] for k in unchanged), 'Unrelated accounting path changed')
    with (OUT/'publication.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check(sha(target) == baseline[str(target.relative_to(ROOT))], 'Publication source changed')
        # No ledger mutation, not even creating its lock file.
        with (ROOT/'artifacts/R020/shared-budget-ledger.lock').open('r') as ledger_lock:
            fcntl.flock(ledger_lock, fcntl.LOCK_EX)
            check(sha(ROOT/'artifacts/R020/shared-budget-ledger.json') == baseline['artifacts/R020/shared-budget-ledger.json'],
                  'Ledger changed during deployment preflight')
            temporary = target.with_name('shared_budget.publish.tmp')
            with temporary.open('xb') as stream:
                stream.write(source.read_bytes()); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, target)
            directory = os.open(target.parent, os.O_DIRECTORY)
            try: os.fsync(directory)
            finally: os.close(directory)
    protected = {p: sha(ROOT/p) == digest for p, digest in baseline.items() if p != str(target.relative_to(ROOT))}
    record = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), boot_id=boot,
        source_before=baseline[str(target.relative_to(ROOT))], deployed_sha256=sha(target),
        candidate_sha256=sha(source), library_published=True, new_api_runtime_verified=False,
        caller_process_snapshot=processes, legacy_batches_valid=legacy, unchanged_methods=unchanged,
        protected_hashes_unchanged=protected, production_ledger_written=False, paid_requests=0,
        caveat='New processes load this library. No actor/hook registration or API dispatch performed.')
    (OUT/'deployment.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__': main()
