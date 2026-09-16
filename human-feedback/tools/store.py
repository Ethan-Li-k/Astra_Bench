"""H001 public evidence and append-only human annotations. Standard library only."""
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'cases/H001'
LOCK = ROOT / 'reviews/source-lock.json'
SOURCE = ROOT.parent / 'artifacts/R019/apple-campaign/episode-0003/rollout/episode'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def contained(root, relative):
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('path outside whitelist')
    result = root / p
    if not result.resolve().is_relative_to(root.resolve()) or result.is_symlink():
        raise ValueError('path outside whitelist')
    return result


def immutable(path, value):
    """Publish a fully fsynced inode atomically, never overwrite an existing record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / ('.pending-' + uuid.uuid4().hex)
    with temp.open('xb') as out:
        out.write(encoded(value)); out.flush(); os.fsync(out.fileno())
    temp.chmod(0o444)
    os.link(temp, path)  # EEXIST is a hard failure, including a prior submission.
    temp.unlink()
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def build_lock(case_dir=CASE, source_root=SOURCE):
    raw = (case_dir / 'case.json').read_bytes()
    case = json.loads(raw)
    if case['case_id'] != 'H001' or case['privileged_object_information_included'] is not False:
        raise ValueError('unexpected case')
    sources = {}
    for entry in case['source_manifest']:
        p = Path(entry['path'])
        relative = p.relative_to(source_root).as_posix()
        if not re.fullmatch(r'(observations/\d{4}/(head_stereo_(left|right)\.png|observation\.json)|execution_\d{4}\.json)', relative):
            raise ValueError('source not public whitelist')
        if digest(contained(source_root, relative).read_bytes()) != entry['sha256']:
            raise ValueError('source hash mismatch')
        sources[relative] = entry['sha256']
    assets = {}
    for frame in case['frames']:
        for image in frame['images']:
            rel = image['file']
            expected = sources['observations/' + '/'.join(Path(rel).parts[1:])]
            if digest(contained(case_dir, rel).read_bytes()) != expected:
                raise ValueError('image differs from policy input')
            assets[rel] = expected
        rel = frame['robot_observation']
        if not re.fullmatch(r'frames/\d{4}/robot_observation\.json', rel):
            raise ValueError('robot observation outside whitelist')
        assets[rel] = digest(contained(case_dir, rel).read_bytes())
    return {'schema': 1, 'case_id': 'H001', 'case_sha256': digest(raw),
            'assets': assets, 'public_sources': sources,
            'limitations': ['Selected stills, not continuous video',
                'Historical task/skill/controller/checkpoint hashes not included in case; reproduction unverified',
                'Robot observation is a frozen public subset, not object contact truth']}


def verify(case_dir=CASE, lock_path=LOCK, source_root=SOURCE):
    lock = json.loads(lock_path.read_text())
    if digest((case_dir / 'case.json').read_bytes()) != lock['case_sha256']:
        raise ValueError('case hash mismatch')
    current = build_lock(case_dir, source_root)
    if current != lock:
        raise ValueError('public evidence changed')
    return lock


class Store:
    def __init__(self, root=ROOT, case_dir=CASE, lock_path=LOCK, source_root=SOURCE):
        self.root, self.case_dir, self.lock_path, self.source_root = root, case_dir, lock_path, source_root

    def binding(self):
        lock = verify(self.case_dir, self.lock_path, self.source_root)
        return {'case_sha256': lock['case_sha256'], 'source_lock_sha256': digest(encoded(lock))}

    def submit(self, payload, channel='browser'):
        if not isinstance(payload, dict):
            raise ValueError('JSON object required')
        required = {'request_id', 'case_id', 'case_sha256', 'source_lock_sha256',
                    'synthetic', 'phase', 'answers', 'exposure'}
        optional = {'parent_annotation_id', 'comparison', 'transcripts'}
        if not required <= payload.keys() or payload.keys() - required - optional:
            raise ValueError('unknown or missing submission fields')
        if payload['case_id'] != 'H001' or type(payload['synthetic']) is not bool:
            raise ValueError('invalid case or synthetic flag')
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', str(payload['request_id'])):
            raise ValueError('invalid request id')
        binding = self.binding()
        if any(payload.get(k) != v for k, v in binding.items()):
            raise ValueError('stale evidence binding')
        answers = payload['answers']
        if not isinstance(answers, dict) or not {'observation', 'priority', 'gate'} <= answers.keys():
            raise ValueError('observation / priority / gate required')
        if answers.keys() - {'observation', 'priority', 'gate', 'counterexample', 'confidence'}:
            raise ValueError('unknown answer field')
        for key, value in answers.items():
            if not isinstance(value, str) or len(value) > 12000 or (key in {'observation', 'priority', 'gate'} and not value.strip()):
                raise ValueError('empty or invalid answer')
        exposure = payload['exposure']
        if not isinstance(exposure, dict) or exposure.get('known_failure_outcome') is not True:
            raise ValueError('H001 is known-failure review, not blind evaluation')
        if type(exposure.get('agent_assessment_seen')) is not bool and exposure.get('agent_assessment_seen') != 'unknown':
            raise ValueError('assessment exposure required')
        if payload['phase'] not in {'independent', 'comparison', 'desktop_transcription'}:
            raise ValueError('invalid phase')
        if payload['phase'] == 'independent' and exposure.get('agent_assessment_seen') is not False:
            raise ValueError('independent phase cannot claim unseen after reveal')
        if payload['phase'] == 'comparison' and exposure.get('agent_assessment_seen') is not True:
            raise ValueError('comparison must record revealed assessment')
        if channel == 'browser' and (payload['phase'] == 'desktop_transcription' or 'transcripts' in payload):
            raise ValueError('desktop import is CLI-only')
        if 'comparison' in payload and (not isinstance(payload['comparison'], str) or len(payload['comparison']) > 12000):
            raise ValueError('invalid comparison')
        lane = 'synthetic' if payload['synthetic'] else 'production'
        directory = self.root / 'annotations' / lane
        directory.mkdir(parents=True, exist_ok=True)
        with (self.root / 'annotations/.submit.lock').open('a') as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            for p in directory.glob('HF-H001-*.json'):
                old = json.loads(p.read_text())
                if old['submission']['request_id'] == payload['request_id']:
                    if old['submission'] != payload or old['channel'] != channel:
                        raise ValueError('request id already used with different content')
                    return self.receipt(old, p, True)
            if payload['phase'] == 'comparison':
                parent = payload.get('parent_annotation_id', '')
                if not re.fullmatch(r'HF-H001-[a-f0-9]{32}', parent):
                    raise ValueError('comparison requires initial submission')
                initial = json.loads((directory / (parent + '.json')).read_text())
                if initial['submission']['phase'] != 'independent' or initial['submission']['case_sha256'] != binding['case_sha256']:
                    raise ValueError('invalid initial submission')
            annotation_id = 'HF-H001-' + uuid.uuid4().hex
            record = {'schema': 1, 'annotation_id': annotation_id, 'created_at': now(),
                      'channel': channel, 'rule_status': 'human_proposed',
                      'human_feedback_used': not payload['synthetic'], 'human_demonstration_used': False,
                      'reproduction_status': 'not_executed_by_annotation_tool', 'submission': payload}
            path = directory / (annotation_id + '.json')
            immutable(path, record)
            return self.receipt(record, path, False)

    def receipt(self, record, path, duplicate):
        return {'annotation_id': record['annotation_id'], 'sha256': digest(path.read_bytes()),
                'synthetic': record['submission']['synthetic'], 'duplicate': duplicate,
                'url': '/api/annotation/' + record['annotation_id']}

    def read(self, annotation_id):
        if not re.fullmatch(r'HF-H001-[a-f0-9]{32}', annotation_id):
            raise ValueError('invalid annotation id')
        for lane in ['production', 'synthetic']:
            p = self.root / 'annotations' / lane / (annotation_id + '.json')
            if p.exists():
                return p.read_bytes()
        raise FileNotFoundError('annotation not found')
