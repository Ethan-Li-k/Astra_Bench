"""Validate management route targets before atomically replacing route-overrides.

Read-only: no model requests, worker signals, or physics. A task-local release
must never be assigned to other tasks, even when its publication hash is valid.
"""
import hashlib
import json
from pathlib import Path


def validate(routes):
    checked = []
    for env, route in routes.items():
        if route['env_id'] != env or route['route'] != 'main_chatgpt':
            raise ValueError('Route identity or account mismatch: ' + env)
        if (route['model'], route['effort']) != ('gpt-6-astra', 'xhigh'):
            raise ValueError('Model setting mismatch: ' + env)
        root = Path(route['release_path'])
        manifest_bytes = (root / 'release.json').read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != route['release']['manifest_sha256']:
            raise ValueError('Release hash mismatch: ' + env)
        manifest = json.loads(manifest_bytes)
        if manifest['release_id'] != route['release']['release_id']:
            raise ValueError('Release identity mismatch: ' + env)
        if env not in manifest['tasks']:
            raise ValueError('Exact routed task absent from release: ' + env)
        task = manifest['tasks'][env]
        if not task['ready_for_load'] or not task['bindings'].get('main_account'):
            raise ValueError('Task is not ready for this route: ' + env)
        spec = root / 'public' / task['task_spec_path']
        if hashlib.sha256(spec.read_bytes()).hexdigest() != task['bindings']['task_spec_sha256']:
            raise ValueError('Task specification hash mismatch: ' + env)
        checked.append({'env_id': env, 'release_id': manifest['release_id']})
    return checked


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('routes', type=Path)
    args = parser.parse_args()
    print(json.dumps({'status': 'PASS', 'routes': validate(json.loads(args.routes.read_text()))}))
