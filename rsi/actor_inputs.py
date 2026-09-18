"""Pinned application inputs for one actor; no account/global instructions copied."""
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def context_text(skill):
    path = Path(skill).parent/'CONTROL_CONTRACT.md'
    if path.is_symlink():
        raise ValueError('Policy context cannot be a symlink')
    return path.read_text() if path.is_file() else ''


def ambient_contract(skill):
    root = Path(skill).parent
    declared = json.loads((root/'ambient-instructions.json').read_text())
    allowed_sources = {'/home/galbot/lizekai/RSI/codex-account-2/home/AGENTS.md',
                       '/home/galbot/lizekai/RSI/main-account/home/AGENTS.md',
                       '/home/galbot/lizekai/RSI/api-actor/AGENTS.md'}
    if len(declared) != 1 or not set(declared) <= allowed_sources:
        raise ValueError('Only the reviewed short role entry is an allowed ambient source')
    allowed = next(iter(declared))
    text = (root/'ROLE_CONTRACT.md').read_text()
    if sha(text.encode()) != declared[allowed] or sha(Path(allowed).read_bytes()) != declared[allowed]:
        raise ValueError('Short ambient role contract changed')
    return declared, text


def pin_actor_inputs(agent, runtime, task_specification, tools, developer_text,
                     public_inputs=(), ambient_sources=None):
    agent = Path(agent)
    (agent/'RUNTIME.md').write_text(runtime)
    (agent/'task_specification.json').write_text(json.dumps(task_specification, indent=2))
    (agent/'tool-contract.json').write_text(json.dumps(tools, sort_keys=True))
    files = [agent/name for name in ('SKILL.md', 'workspace.json', 'RUNTIME.md',
                                    'task_specification.json', 'tool-contract.json')]
    for name in ('CONTROL_CONTRACT.md','ROLE_CONTRACT.md','ambient-instructions.json'):
        if (agent/name).exists():
            files.append(agent/name)
    for original in public_inputs:
        path = Path(original)
        if not path.is_file() or path.is_symlink():
            raise ValueError('Actor read set must list individual public regular files')
        files.append(path)
    expected = {str(p.resolve()): sha(p.read_bytes()) for p in files}
    manifest = {'contract': 'actor-explicit-inputs-v1', 'files': expected,
                'developer_sha256': sha(developer_text.encode()),
                'ambient_instruction_sources': dict(ambient_sources or {}),
                'mutable_episode_files': ['NOTES.md', 'scratch/', 'rpc_calls/'],
                'boundary': 'Application inputs only; built-in safety and sandbox remain active.'}
    (agent/'input-manifest.json').write_text(json.dumps(manifest, indent=2))
    verify_actor_inputs(manifest, developer_text)
    return manifest


def verify_actor_inputs(manifest, developer_text):
    if (manifest.get('contract') != 'actor-explicit-inputs-v1'
            or manifest.get('developer_sha256') != sha(developer_text.encode())):
        raise RuntimeError('Actor application instruction contract changed')
    for path, expected in {**manifest['files'], **manifest.get('ambient_instruction_sources',{})}.items():
        p = Path(path)
        if p.is_symlink() or not p.is_file() or sha(p.read_bytes()) != expected:
            raise RuntimeError('Actor pinned input changed: '+path)


STAGES = ('approach', 'stationary_reach', 'open_enclosure', 'closure', 'probe_lift',
          'separate_hold', 'present', 'receiver_enclosure', 'load_transfer', 'giver_clear',
          'loaded_travel', 'lower', 'release', 'hands_clear_supported')


def stage_claim(reason):
    """Validate claims; losslessly normalize textual bullet lists, never task stages."""
    if not isinstance(reason, str) or len(reason) > 1400:
        raise ValueError('reason: expected JSON string, at most 1400 characters')
    try:
        row = json.loads(reason)
    except (TypeError, ValueError) as e:
        raise ValueError('reason: expected JSON object encoded as a string') from e
    keys = {'verified_completed', 'currently_attempting', 'remaining', 'evidence',
            'expected_exit', 'revert_to'}
    if not isinstance(row, dict) or not keys<=set(row) or set(row)-keys-{'reacquisition_target'}:
        raise ValueError('reason fields: required '+', '.join(sorted(keys))+'; only optional reacquisition_target')
    if 'reacquisition_target' in row and row['reacquisition_target']!='original_task_object':
        raise ValueError('reacquisition_target: expected "original_task_object"')
    legal = ', '.join(STAGES)
    for key in ('verified_completed', 'remaining'):
        value = row[key]
        if not isinstance(value, list) or not all(isinstance(x,str) for x in value) or len(value)!=len(set(value)) or not set(value)<=set(STAGES):
            raise ValueError(key+': expected unique array of stage strings; allowed: '+legal)
    for key in ('currently_attempting', 'revert_to'):
        if row[key] not in STAGES:
            raise ValueError(key+': expected one stage string; allowed: '+legal)
    if set(row['verified_completed']) & (set(row['remaining']) | {row['currently_attempting']}):
        raise ValueError('verified_completed: must not overlap remaining or currently_attempting')
    for key in ('evidence', 'expected_exit'):
        value = row[key]
        if isinstance(value, list) and value and all(isinstance(x,str) and x.strip() for x in value):
            value = '; '.join(value)  # Preserve every supplied item; do not invent evidence.
        if not isinstance(value, str) or not value.strip() or len(value)>400:
            raise ValueError(key+': expected nonempty string (max 400 characters), or nonempty string array joined within that limit')
        row[key] = value
    return row


# Hash-bound project evidence only; no goal watcher or account-owner policy.
def evidence_path(ref, root=Path('/home/galbot/lizekai/RSI')):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('exact_evidence_reference_required')
    relative = Path(ref['path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] not in ('artifacts', 'ref', 'codex-account-2', 'tools', 'rsi', 'skills'):
        raise ValueError('evidence_outside_project_scope')
    forbidden = ('auth', 'token', 'secret', 'cookie', 'api.json', '.env', 'sessions', 'home', '.git', '.codex')
    if any(any(word in part.lower() for word in forbidden) for part in relative.parts):
        raise ValueError('protected_evidence_path')
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('symlink_evidence_forbidden')
    if not isinstance(ref['sha256'], str) or len(ref['sha256']) != 64:
        raise ValueError('evidence_hash_required')
    return path

def read_evidence(ref, root=Path('/home/galbot/lizekai/RSI'), *, json_document=True):
    path=evidence_path(ref,root)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    if h.hexdigest() != ref['sha256']:
        raise ValueError('evidence_changed')
    if not json_document: return path
    if path.suffix != '.json' or path.stat().st_size > 8_000_000:
        raise ValueError('bounded_JSON_evidence_required')
    return json.loads(path.read_text())
