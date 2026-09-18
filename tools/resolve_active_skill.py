"""Read the single current skill registry; never launch a model or environment."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve(task=None, route='api'):
    path = ROOT/'skills/ACTIVE.json'
    active_bytes = path.read_bytes()
    active = json.loads(active_bytes)
    if active.get('schema') != 'rsi-active-skills-v1':
        raise ValueError('Unsupported active skill registry')
    selected = active['routes'][route]
    release = ROOT/selected['release_path']
    # ACTIVE is the atomic authority. Compatibility aliases may be ahead or
    # behind during publication; they never select or reject a valid snapshot.
    try:
        current = json.loads((release.parent/'CURRENT.json').read_bytes())
        alias_status = ('matches_active' if current == {
            key: selected[key] for key in ('release_id','manifest_sha256')
        } else 'differs_from_active')
    except (OSError, ValueError):
        alias_status = 'unavailable'
    manifest_path = release/'release.json'
    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != selected['manifest_sha256']:
        raise ValueError('Active release changed')
    manifest = json.loads(manifest_bytes)
    if manifest.get('status') != 'published':
        raise ValueError('Active release is not published')
    result = dict(registry_path=str(path), registry_sha256=hashlib.sha256(active_bytes).hexdigest(),
                  route=route, release_id=selected['release_id'],
                  release_manifest_sha256=selected['manifest_sha256'],
                  compatibility_alias_status=alias_status,
                  launch_authority='Current manager plan and exact native entry; resolution grants no launch.',
                  model_started=False, physics_actions=0)
    native_runtime = manifest.get('native_api_runtime') if route == 'api' else None
    if native_runtime is not None:
        verified_runtime = {}
        for key, ref in native_runtime['files'].items():
            source = ROOT/ref['path']
            if not source.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError('Native API runtime escaped project')
            expected = manifest['runtime_code_hashes'].get(ref['path'])
            if (expected != ref['sha256'] or
                    hashlib.sha256(source.read_bytes()).hexdigest() != expected):
                raise ValueError('Native API runtime source changed: '+ref['path'])
            verified_runtime[key] = dict(path=str(source), sha256=expected)
        result['native_api_runtime'] = dict(version=native_runtime['version'],
            files=verified_runtime, new_reset_only=True,
            adoption='Native owner imports the verified bridge for a fresh reset; this resolver does not launch or change in-flight workers.')
    if task is None:
        result['tasks'] = sorted(selected['templates'])
        result['operator_skills'] = active['operator_skills']
        return result
    template = selected['templates'][task]
    refs = {}
    for key, relative in template['files'].items():
        if relative is None:
            continue
        source = release/'public'/relative
        if not source.resolve().is_relative_to((release/'public').resolve()):
            raise ValueError('Skill reference escaped release')
        expected = manifest['public_hashes'].get(relative)
        if expected is None or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Active public source changed: '+relative)
        refs[key] = dict(path=str(source), sha256=expected)
    result.update(task=task, templates_are_not_control_admission=True,
                  native_interface_required=True, files=refs,
                  loading='Freeze selected sources and exact interface per new reset; record delivered and actually read separately. In-flight versions remain fixed.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task')
    parser.add_argument('--route', choices=('api','main'), default='api')
    args = parser.parse_args()
    print(json.dumps(resolve(args.task, args.route), ensure_ascii=False, indent=2))
