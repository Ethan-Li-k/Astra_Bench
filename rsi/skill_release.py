"""Central immutable skill releases, reusing the existing frozen memory boundary."""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil

from rsi.frozen_skill import FrozenSkillMemory, file_hashes
from rsi.skill_learning import validate_policy_instructions

AUTHOR = '01a0a949-dc8e-70c3-b8a6-53131882e19d'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_public_payload(value):
    forbidden = {'host_audit', 'evaluator', 'object_state', 'object_pose',
                 'contacts', 'contact_truth', 'reward', 'qpos', 'mjData', 'oracle'}
    if isinstance(value, dict):
        if forbidden.intersection(value):
            raise ValueError('Privileged fields cannot enter public experience')
        for child in value.values():
            validate_public_payload(child)
    elif isinstance(value, list):
        for child in value:
            validate_public_payload(child)


def task_snapshot(public, task):
    root = Path(public).resolve()
    path = (root/task['snapshot']).resolve()
    if root not in path.parents:
        raise ValueError('Task snapshot must stay within released public files')
    return path


def runtime_instructions(caller, adapter, *, frozen=True):
    def literal(path, name):
        tree = ast.parse(Path(path).read_text())
        return next(ast.literal_eval(n.value) for n in ast.walk(tree)
                    if isinstance(n, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == name for t in n.targets))
    immutable = literal(caller, 'immutable')
    if frozen:
        # Evaluate only the caller's text-only rendering branch, not run_episode.
        tree = ast.parse(Path(caller).read_text())
        branch = next((n for n in ast.walk(tree) if isinstance(n, ast.If)
                       and ast.unparse(n.test) == 'frozen_context is not None'
                       and any(isinstance(x, ast.Name) and x.id == 'immutable'
                               for x in ast.walk(n))), None)
        if branch is not None:
            scope = {'immutable':immutable, 'frozen_context':{}}
            exec(compile(ast.Module(body=[branch], type_ignores=[]), str(caller), 'exec'), scope)
            immutable = scope['immutable']
    return immutable + literal(adapter, 'NETWORK_CONTINUATION')


def execution_profile(phase, evaluation_steps=None):
    if phase in ('learning', 'stability'):
        if evaluation_steps is not None:
            raise ValueError('Learning has checkpoints, not a cumulative stop budget')
        return {'id': 'learning-horizon-v1', 'phase': phase,
                'max_episode_steps': None, 'checkpoint_steps': 12000,
                'native_benchmark': False}
    if phase != 'evaluation' or type(evaluation_steps) is not int or evaluation_steps <= 0:
        raise ValueError('Evaluation requires its preregistered positive step budget')
    return {'id': 'evaluation-finite-v1', 'phase': phase,
            'max_episode_steps': evaluation_steps, 'checkpoint_steps': 12000,
            'native_benchmark': 'depends_on_pinned_assets_and_native_contract'}


def select_sources(index, env_id, phases, control, feedback_allowed, limit=3):
    """Small conditional selection: exact success, compatible success, counterexample."""
    if type(limit) is not int or not 1 <= limit <= 4:
        raise ValueError('Select at most four public entries')
    selected = []
    for row in index['sources']:
        if (row['control_contract'] != control or not set(phases).intersection(row['phases'])
                or (row.get('human_feedback_used') and not feedback_allowed)):
            continue
        success = row['status'] == 'audited_source'
        if not success and row['status'] != 'counterexample':
            continue
        rank = (0 if row['env_id'] == env_id else 1) if success else (2 if row['env_id'] == env_id else 3)
        selected.append((rank, row['id'], row))
    ordered = sorted(selected)
    positives = [row for rank, _, row in ordered if rank < 2]
    counterexamples = [row for rank, _, row in ordered if rank >= 2]
    reserve = int(bool(counterexamples) and limit > 1)
    return positives[:limit-reserve] + counterexamples[:limit-min(len(positives), limit-reserve)]


def publish_release(draft, releases, release_id, *, author, expected_previous, runtime):
    """Exclusive publisher and compare-and-swap pointer. No existing version is overwritten."""
    if author != AUTHOR or not release_id or Path(release_id).name != release_id:
        raise ValueError('Wrong central author or release identity')
    draft, releases = Path(draft), Path(releases)
    releases.mkdir(parents=True, exist_ok=True)
    with (releases/'.publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = releases/'CURRENT.json'
        previous = json.loads(current.read_text()) if current.exists() else None
        if (previous or {}).get('manifest_sha256') != expected_previous:
            raise ValueError('Publisher pointer changed; review before publication')
        manifest = json.loads((draft/'release.json').read_text())
        if manifest['author'] != author or manifest['release_id'] != release_id:
            raise ValueError('Draft author/identity mismatch')
        hashes = file_hashes(draft/'public')
        if hashes != manifest['public_hashes']:
            raise ValueError('Draft changed after validation')
        if manifest['runtime_sha256'] != hashlib.sha256(runtime.encode()).hexdigest():
            raise ValueError('Unreviewed runtime')
        for path in (draft/'public').rglob('*.json'):
            validate_public_payload(json.loads(path.read_text()))
        for task in manifest['tasks'].values():
            validate_policy_instructions((task_snapshot(draft/'public', task)/'SKILL.md').read_text(), runtime)
        # Copy to a new path only; an interrupted publication remains unapproved,
        # with all partial evidence intact and CURRENT unchanged.
        destination = releases/release_id
        shutil.copytree(draft, destination, symlinks=True)
        if file_hashes(destination/'public') != hashes:
            raise ValueError('Publication copy changed')
        manifest.update(status='published', rollback=previous)
        (destination/'release.json').write_text(json.dumps(manifest, indent=2)+'\n')
        pointer = {'release_id': release_id, 'manifest_sha256': digest(destination/'release.json')}
        temporary = releases/f'.CURRENT-{release_id}.json'
        with temporary.open('x') as stream:
            json.dump(pointer, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(current)
        return pointer


def verify_release(release, expected_sha256, env_id, runtime):
    release = Path(release)
    if digest(release/'release.json') != expected_sha256:
        raise ValueError('Unpublished or changed release manifest')
    manifest = json.loads((release/'release.json').read_text())
    if manifest.get('status') != 'published' or manifest.get('author') != AUTHOR:
        raise ValueError('Only a central published release may load')
    if env_id not in manifest['tasks']:
        raise ValueError('Exact task entry is absent from release')
    if file_hashes(release/'public') != manifest['public_hashes']:
        raise ValueError('Published public input changed or gained files')
    if manifest['runtime_sha256'] != hashlib.sha256(runtime.encode()).hexdigest():
        raise ValueError('Runtime differs from published candidate')
    validate_policy_instructions(
        (task_snapshot(release/'public', manifest['tasks'][env_id])/'SKILL.md').read_text(), runtime)
    return manifest


def verify_load_configuration(manifest, env_id, bindings):
    task = manifest['tasks'][env_id]
    if not task.get('ready_for_load'):
        raise ValueError('Native task/control admission still pending')
    if bindings != task['bindings']:
        raise ValueError('Task/control/feedback configuration differs from released input')


def verify_frozen_release_inputs(manifest, candidate_public, *, env_id, permitted_hashes):
    """Sealing cannot turn unreviewed proposals into an approved public corpus."""
    allowed = set(permitted_hashes)
    feedback = set(manifest['tasks'][env_id]['bindings'].get('human_feedback_sha256', []))
    if not allowed <= set(manifest['public_hashes'].values()) | feedback:
        raise ValueError('Requested read set contains unpublished inputs')
    allowed.update(feedback)
    for relative, actual in file_hashes(candidate_public).items():
        if relative == 'sources.json':
            continue  # generated path map; underlying copied files are checked
        if actual not in allowed:
            raise ValueError('Frozen input was not included in central publication: '+relative)


class ReleasedSkillMemory(FrozenSkillMemory):
    """All phases retain proposals outside the fixed actor-readable release."""
    def __init__(self, release, expected_sha256, env_id, proposal_root, runtime):
        self.release, self.release_hash = Path(release), expected_sha256
        self.env_id, self.release_runtime = env_id, runtime
        manifest = verify_release(release, expected_sha256, env_id, runtime)
        snapshot = task_snapshot(self.release/'public', manifest['tasks'][env_id])
        if snapshot.resolve() in Path(proposal_root).resolve().parents or self.release.resolve() in Path(proposal_root).resolve().parents:
            raise ValueError('Proposal sink must be outside released inputs')
        super().__init__(snapshot, proposal_root, file_hashes(snapshot))
        self.runtime_instructions = runtime

    def _verify(self):
        verify_release(self.release, self.release_hash, self.env_id, self.release_runtime)
        super()._verify()
