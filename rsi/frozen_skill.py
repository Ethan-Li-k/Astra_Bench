"""Frozen public memory and host-only stability boundaries; no new runner or policy."""
import hashlib
import json
from pathlib import Path
import shutil
import datetime
import fcntl
import uuid
import importlib.metadata
import sys

from rsi.skill_learning import SkillMemory


def file_hashes(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Frozen input cannot contain symlinks')
        if path.is_file():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def snapshot_memory(memory, destination):
    """Copy only public skill/history; caller separately pins all other actor inputs."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination/'SKILL.md').write_bytes(memory.skill.read_bytes())
    shutil.copytree(memory.root/'versions', destination/'memory/versions', symlinks=True)
    if memory.journal.exists():
        shutil.copyfile(memory.journal, destination/'memory/experience.jsonl')
    # Freeze retrieval qualification now; later host reviews must not change ranking.
    rows = [json.loads(s) for s in memory.journal.read_text().splitlines()] if memory.journal.exists() else []
    labels = {r['episode_id']: memory.success_review(r['episode_id']) if memory.success_review else {}
              for r in rows}
    # Store only public retrieval labels, never the host audit payload.
    labels = {episode: {k: value.get(k) for k in
              ('task_audit_status', 'completion_contract_matches', 'audited_task_success')}
              for episode, value in labels.items()}
    (destination/'retrieval-labels.json').write_text(json.dumps(labels, sort_keys=True)+'\n')
    return file_hashes(destination)


class FrozenSkillMemory:
    """Read a fixed snapshot; keep mandatory terminal revisions in an audit-only sink.

    This isolates memory only. A caller must pin source allowlists, runtime, assets,
    feedback and controls before declaring a complete frozen candidate.
    """
    def __init__(self, snapshot, proposal_root, expected_hashes):
        self.snapshot = Path(snapshot)
        self.root = self.snapshot/'memory'
        self.skill = self.snapshot/'SKILL.md'
        self.journal = self.root/'experience.jsonl'
        self.proposal_root = Path(proposal_root)
        self.expected_hashes = dict(expected_hashes)
        self.runtime_instructions = ''
        self._updated = False
        self._verify()
        if not (self.root/'versions/0000.md').is_file():
            raise ValueError('Frozen memory requires original version')
        labels = json.loads((self.snapshot/'retrieval-labels.json').read_text())
        self._reader = SkillMemory(self.root, self.skill,
                                  success_review=lambda episode: labels.get(episode, {}))
        self._verify()

    def _verify(self):
        if file_hashes(self.snapshot) != self.expected_hashes:
            raise ValueError('Frozen readable input changed or gained new files')

    def read(self, version=None):
        self._verify()
        self._reader.runtime_instructions = self.runtime_instructions
        return self._reader.read(version=version)

    def update(self, *args, **kwargs):
        self._verify()
        if self._updated or (self.proposal_root/'accepted.json').exists():
            raise ValueError('Frozen episode already has a proposal; never overwrite it')
        # validate/write through the existing complete evidence and size checks.
        self.proposal_root.mkdir(parents=True, exist_ok=True)
        attempt = self.proposal_root/f'attempt-{len(list(self.proposal_root.glob("attempt-*")))+1:04d}'
        attempt.mkdir(exist_ok=False)
        proposal_skill = attempt/'SKILL.md'
        proposal_skill.write_bytes(self.skill.read_bytes())
        sink = SkillMemory(attempt, proposal_skill)
        sink.runtime_instructions = self.runtime_instructions
        try:
            row = sink.update(*args, **kwargs)
        except Exception as error:
            (attempt/'rejected.json').write_text(json.dumps({'error':str(error)})+'\n')
            raise
        with (self.proposal_root/'accepted.json').open('x') as stream:
            json.dump({'proposal':str(attempt), 'skill_sha256':row['skill_sha256']}, stream)
        self._updated = True
        self._verify()
        return dict(row, frozen_proposal_only=True, loaded_candidate_unchanged=True)


def stability_count(task_id, candidate_sha256, rows):
    """Rows must come from completed independent host audits, never actor claims."""
    seen = set()
    consecutive = successes = physical_non_successes = 0
    unresolved = []
    for row in rows:
        if row['task_id'] != task_id or row['candidate_sha256'] != candidate_sha256:
            raise ValueError('Different task/candidate cannot contribute to this streak')
        reset = row.get('reset_id')
        if not isinstance(reset, str) or not reset or reset in seen:
            raise ValueError('Missing or repeated independent reset')
        seen.add(reset)
        if (not row.get('full_turn_completed') or not row.get('skill_updated')
                or row.get('termination_class') == 'infrastructure_interruption'):
            unresolved.append(reset)
            continue
        if (row.get('audited_task_success') is True and row.get('physical_attempt') is True
                and row.get('native_outcome') == 'success'):
            consecutive += 1
            successes += 1
        else:
            consecutive = 0
            physical_non_successes += 1
    return dict(consecutive_successes=consecutive, audited_successes=successes,
                complete_non_successes=physical_non_successes,
                unresolved_resets=unresolved,
                eligible_for_evaluation=consecutive >= 5 and not unresolved)


def validate_evaluation_seeds(seeds, stability_seeds):
    if (not isinstance(seeds, list) or len(seeds) != 10
            or any(type(s) is not int for s in seeds)
            or len(set(seeds)) != 10 or set(seeds).intersection(stability_seeds)):
        raise ValueError('Pre-register ten distinct evaluation seeds disjoint from stability')
    return list(seeds)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _file_digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def environment_versions():
    return {'python':sys.version,'python_executable':str(Path(sys.executable).resolve()),
            'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()
                        if d.metadata['Name']}}


def snapshot_sources(memory, sources, destination):
    """Pin explicitly reviewed public paths and this memory's cited rollout roots.

    Text path references are redirected to the copies. Unlisted citations are
    not grants of access. Never copy episode parents containing host audits.
    """
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    snapshot_memory(memory, destination/'local')
    paths = {str(Path(s['path']).resolve()) for s in sources.values()}
    # Every local journal reference was validated against its public rollout on
    # publication. Restrict the snapshot to that subtree, not the episode parent.
    rows = [json.loads(s) for s in memory.journal.read_text().splitlines()] if memory.journal.exists() else []
    for row in rows:
        for evidence in row['evidence_paths']:
            path = Path(evidence).resolve()
            rollout = next((p for p in path.parents if p.name == 'rollout'
                            and p.parent.name.startswith('episode-')), None)
            if rollout is None:
                raise ValueError('Frozen memory citation is not public rollout evidence')
            paths.add(str(rollout))
    paths -= {str(memory.skill.resolve()), str(memory.journal.resolve())}
    # One copy per enclosing source, with stable sorted names.
    roots = [p for p in sorted(paths) if not any(Path(q) in Path(p).parents for q in paths)]
    redirects = {str(memory.skill.resolve()):str(destination/'local/SKILL.md'),
                 str(memory.journal.resolve()):str(destination/'local/memory/experience.jsonl'),
                 str((memory.root/'versions').resolve()):str(destination/'local/memory/versions')}
    for i, original in enumerate(roots):
        source = Path(original)
        if source.is_symlink() or not source.exists():
            raise ValueError('Invalid frozen public source')
        target = destination/'sources'/f'{i:04d}'/source.name
        target.parent.mkdir(parents=True)
        if source.is_dir():
            file_hashes(source)  # reject links into private/live data
            shutil.copytree(source, target)
        else:
            shutil.copyfile(source, target)
        redirects[original] = str(target)
    def redirect(text):
        for original, target in sorted(redirects.items(), key=lambda x: -len(x[0])):
            text = text.replace(original, target)
        return text
    for path in destination.rglob('*'):
        if path.is_file() and path.suffix in ('.md', '.json', '.jsonl', '.txt'):
            path.write_text(redirect(path.read_text()))
    pinned = {}
    for sid, source in sources.items():
        value = json.loads(redirect(json.dumps(source)))
        path = Path(value['path'])
        if destination not in path.parents or not path.exists():
            raise ValueError('Source redirect escaped frozen public input')
        value['original_sha256'] = source.get('sha256')
        value['sha256'] = _file_digest(path) if path.is_file() else None
        pinned[sid] = value
    (destination/'sources.json').write_text(json.dumps(pinned, indent=2)+'\n')
    return pinned


def seal_candidate(directory, *, task_id, task_specification, task_text, options,
                   dependencies, stability_seeds, evaluation_seeds, audit_contract,
                   ambient_instruction_sources=(), runtime_environment=None):
    """Seal an already prepared public/ tree. Dependencies are host-only paths.

    Caller must supply the actual code, assets, controller and camera dependency
    closure; arbitrary labels are insufficient for admission.
    """
    directory = Path(directory).resolve()
    required = {'runtime', 'retrieval', 'assets', 'controller', 'camera', 'task', 'model_route'}
    if set(dependencies) != required or any(not v for v in dependencies.values()):
        raise ValueError('Incomplete frozen dependency categories')
    if (not stability_seeds or any(type(s) is not int for s in stability_seeds)
            or len(set(stability_seeds)) != len(stability_seeds)):
        raise ValueError('Pre-register unique integer stability seeds')
    validate_evaluation_seeds(evaluation_seeds, stability_seeds)
    if (task_specification['env_id'] != task_id or not audit_contract.get('native')
            or not audit_contract.get('independent') or not audit_contract.get('terminal_hold')):
        raise ValueError('Exact task and native/independent/terminal hold criteria required')
    payload = dict(protocol='SIX-TASK-FIVE-STABLE-V1', task_id=task_id,
        model='gpt-6-astra', effort='xhigh', task_specification=task_specification,
        runtime_environment=runtime_environment,
        task_text=task_text, options=options, audit_contract=audit_contract,
        stability_seeds=list(stability_seeds), evaluation_seeds=list(evaluation_seeds),
        ambient_instruction_sources={str(Path(p).resolve()):_file_digest(p)
                                     for p in ambient_instruction_sources},
        public_files=file_hashes(directory/'public'),
        dependencies={key:{str(Path(p).resolve()):_file_digest(p) for p in paths}
                      for key, paths in dependencies.items()},
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    payload['candidate_sha256'] = _digest(payload)
    with (directory/'manifest.json').open('x') as stream:
        json.dump(payload, stream, indent=2)
    return payload


def verify_candidate(directory, *, task_id=None, options=None, check_environment=False):
    directory = Path(directory).resolve()
    payload = json.loads((directory/'manifest.json').read_text())
    digest = payload.pop('candidate_sha256')
    if _digest(payload) != digest:
        raise ValueError('Candidate manifest was modified')
    payload['candidate_sha256'] = digest
    if check_environment and payload.get('runtime_environment') != environment_versions():
        raise ValueError('Frozen runtime environment/package versions changed')
    if task_id is not None and payload['task_id'] != task_id:
        raise ValueError('Candidate belongs to a different exact task')
    if options is not None and payload['options'] != options:
        raise ValueError('Runtime options differ from frozen candidate')
    if file_hashes(directory/'public') != payload['public_files']:
        raise ValueError('Frozen public read set changed')
    for paths in payload['dependencies'].values():
        for path, digest in paths.items():
            if _file_digest(path) != digest:
                raise ValueError('Frozen dependency changed: '+path)
    for path,digest in payload.get('ambient_instruction_sources',{}).items():
        if _file_digest(path) != digest:
            raise ValueError('Frozen ambient instructions changed: '+path)
    return payload


def claim_episode(directory, *, task_id, options, phase, seed, episode):
    """Exclusive ordered pre-registration; an unresolved prior episode blocks next."""
    directory = Path(directory).resolve()
    manifest = verify_candidate(directory, task_id=task_id, options=options)
    admission_path=directory/'admission-audit.json'
    if admission_path.exists() and json.loads(admission_path.read_text()).get('stability_credit_allowed') is False:
        raise ValueError('Frozen candidate admission was rejected; create a new candidate')
    if phase not in ('stability', 'evaluation'):
        raise ValueError('Frozen phase must be stability or evaluation')
    records = directory/'registrations'; records.mkdir(exist_ok=True)
    with (directory/'registration.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        registrations = [json.loads(p.read_text()) for p in sorted(records.glob('*.json'))]
        outcomes = []
        for registration in registrations:
            path = directory/'outcomes'/f"{registration['registration_id']}.json"
            if not path.exists():
                raise ValueError('Previous registered outcome unresolved; do not skip or replay')
            outcome = json.loads(path.read_text())
            if outcome.get('registration') != registration:
                raise ValueError('Outcome does not match registered attempt')
            for name, digest in outcome['evidence_sha256'].items():
                if _file_digest(Path(registration['episode'])/name) != digest:
                    raise ValueError('Previously audited episode evidence changed')
            outcomes.append(outcome['audit'])
        stable = [o for r,o in zip(registrations,outcomes) if r['phase']=='stability']
        if phase == 'evaluation' and not stability_count(task_id, manifest['candidate_sha256'], stable)['eligible_for_evaluation']:
            raise ValueError('Five consecutive independent audited successes required')
        if phase == 'stability' and any(r['phase']=='evaluation' for r in registrations):
            raise ValueError('Cannot resume stability after evaluation has begun')
        same_phase = [r for r in registrations if r['phase']==phase]
        seeds = manifest[phase+'_seeds']
        if len(same_phase) >= len(seeds) or type(seed) is not int or seeds[len(same_phase)] != seed:
            raise ValueError('Reset seed/order differs from pre-registration')
        if any(r['episode']==str(Path(episode).resolve()) for r in registrations):
            raise ValueError('Episode path already registered')
        if Path(episode).exists():
            raise ValueError('Frozen episode must be a fresh independent reset')
        registration = dict(protocol=manifest['protocol'],registration_id=str(uuid.uuid4()), task_id=task_id,
            candidate_sha256=manifest['candidate_sha256'], phase=phase, seed=seed,
            episode=str(Path(episode).resolve()),
            registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        with (records/f'{len(registrations)+1:04d}.json').open('x') as stream:
            json.dump(registration, stream, indent=2)
        return registration


def record_episode_audit(directory, episode):
    """Bind canonical host result/turn/reset/review to the prior registration.

    Never accept actor-supplied counters or a bare success boolean.
    """
    from tools.audit_simple_campaigns import episode_status
    directory, episode = Path(directory).resolve(), Path(episode).resolve()
    manifest = verify_candidate(directory)
    admission_path=directory/'admission-audit.json'
    if admission_path.exists() and json.loads(admission_path.read_text()).get('stability_credit_allowed') is False:
        raise ValueError('Rejected configuration cannot contribute to frozen scores')
    registration = json.loads((episode/'protocol-registration.json').read_text())
    candidates = [json.loads(p.read_text()) for p in (directory/'registrations').glob('*.json')]
    if (registration not in candidates or registration['episode'] != str(episode)
            or registration['candidate_sha256'] != manifest['candidate_sha256']):
        raise ValueError('Episode lacks matching pre-registration')
    result = json.loads((episode/'result.json').read_text())
    scene = json.loads((episode/'video/scene_setup.json').read_text())
    reset = scene['reset_provenance']
    if (scene['env_id'] != manifest['task_id'] or reset['seed'] != registration['seed']
            or reset['method'] != 'fresh_environment_reset'
            or reset['recorded_utc'] <= registration['registered_utc']
            or result.get('protocol_registration') != registration):
        raise ValueError('Actual reset/result disagrees with registered candidate')
    audit = episode_status(episode)
    if audit['host_success_complete'] and audit['task_audit_status']=='unknown':
        raise ValueError('Native success awaits independent task audit')
    if not audit['full_turn_completed'] or not audit['skill_updated'] or result['error']:
        raise ValueError('Incomplete/infra outcome remains unresolved; no advancement')
    audit.update(task_id=manifest['task_id'], candidate_sha256=manifest['candidate_sha256'])
    outcomes = directory/'outcomes'; outcomes.mkdir(exist_ok=True)
    for path in outcomes.glob('*.json'):
        if json.loads(path.read_text())['audit']['reset_id']==reset['reset_id']:
            raise ValueError('Repeated physical reset cannot earn another result')
    evidence = ['result.json','video/scene_setup.json','protocol-registration.json',
                'frozen-input-verification.json', *[p.name for p in episode.glob('turn_*.json')]]
    if (episode/'success_review.json').exists():evidence.append('success_review.json')
    verification=json.loads((episode/'frozen-input-verification.json').read_text())
    if verification != {'candidate_sha256':manifest['candidate_sha256'],'unchanged_after_turn':True}:
        raise ValueError('Frozen input final verification failed')
    record = dict(registration=registration, audit=audit,
                  evidence_sha256={p:_file_digest(episode/p) for p in evidence})
    with (outcomes/f"{registration['registration_id']}.json").open('x') as stream:
        json.dump(record, stream, indent=2)
    return record
