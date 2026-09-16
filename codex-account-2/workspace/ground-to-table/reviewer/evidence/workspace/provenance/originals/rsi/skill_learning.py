"""Evidence-backed skill revisions and distinct-episode success accounting."""
import hashlib
import json
from pathlib import Path
import re


def usage_exhausted(result):
    return 'usageLimitExceeded' in str(result.get('error') or '')


def skill_size(text):
    return {'words': len(text.split()), 'characters': len(text),
            'non_whitespace': len(re.sub(r'\s', '', text))}


class SkillMemory:
    def __init__(self, root, skill):
        self.root, self.skill = Path(root), Path(skill)
        (self.root/'versions').mkdir(parents=True, exist_ok=True)
        self.journal = self.root/'experience.jsonl'
        first = self.root/'versions/0000.md'
        if not first.exists():
            first.write_text(self.skill.read_text())

    def read(self, version=None):
        rows = [json.loads(line) for line in self.journal.read_text().splitlines()] if self.journal.exists() else []
        if version is not None:
            if type(version) is not int or not 1 <= version <= len(rows):
                raise ValueError('Requested experience version does not exist')
            experiences = [rows[version-1]]
        else:
            experiences = []
            selected = rows[-4:]
            first_success = next((r for r in rows if r['native_outcome'] == 'success'), None)
            if first_success is not None and first_success not in selected:
                selected = [first_success]+rows[-3:]
            for row in selected:
                brief = dict(row)
                brief.update(lesson=row['lesson'][:1600],
                    lesson_is_preview=len(row['lesson']) > 1600,
                    evidence_paths=row['evidence_paths'][:3],
                    evidence_count=len(row['evidence_paths']),
                    full_experience_query={'tool': 'experience_read',
                                           'arguments': {'version': row['version']}})
                experiences.append(brief)
        return {'skill': self.skill.read_text(), 'version': len(rows),
                'experiences': experiences, 'length_caps':
                {'words': 831, 'characters': 6250, 'non_whitespace': 5357}}

    def update(self, markdown, lesson, evidence_paths, evidence_root, episode_id, outcome,
               *, transfer_scope='task_specific', change_summary=None, selected_source_ids=()):
        limits = {'words': 831, 'characters': 6250, 'non_whitespace': 5357}
        if not isinstance(markdown, str) or any(skill_size(markdown)[k] > n for k,n in limits.items()):
            raise ValueError('Skill exceeds the upstream maximum: 831 words / 6250 characters / 5357 non-whitespace')
        if not markdown.startswith('---\n') or 'name: loco-manip-direct\n' not in markdown or 'description:' not in markdown:
            raise ValueError('Preserve valid loco-manip-direct skill frontmatter')
        if not isinstance(lesson, str) or not lesson.strip() or not evidence_paths:
            raise ValueError('A lesson and actual episode evidence are required')
        if transfer_scope not in ('task_specific','shared_candidate'):
            raise ValueError('Unsupported transfer scope')
        evidence_root = Path(evidence_root).resolve()
        paths = [Path(p).resolve() for p in evidence_paths]
        invalid = [str(p) for p in paths if evidence_root not in p.parents or not p.is_file()]
        if invalid:
            raise ValueError(f'Evidence must be existing files inside {evidence_root}. Invalid: {invalid}')
        version = self.read()['version']+1
        row = {'version': version, 'episode_id': episode_id, 'native_outcome': outcome,
               'lesson': lesson, 'evidence_paths': [str(p) for p in paths],
               'skill_sha256': hashlib.sha256(markdown.encode()).hexdigest(),
               'size': skill_size(markdown), 'author': 'gpt-6-astra/xhigh',
               'transfer_scope':transfer_scope, 'change_summary':change_summary,
               'selected_source_ids':list(selected_source_ids),
               'promotion_status':('requires_cross_task_validation' if transfer_scope=='shared_candidate'
                                   else 'task_local')}
        (self.root/'versions'/f'{version:04d}.md').write_text(markdown)
        if transfer_scope == 'shared_candidate':
            candidates=self.root/'shared_candidates';candidates.mkdir(exist_ok=True)
            (candidates/f'{version:04d}.md').write_text(markdown)
        with self.journal.open('a') as stream:
            stream.write(json.dumps(row, ensure_ascii=False)+'\n')
        self.skill.write_text(markdown)
        return row


class CampaignLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.rows = json.loads(self.path.read_text())['episodes'] if self.path.exists() else {}

    @property
    def successes(self):
        return sum(row.get('success') is True for row in self.rows.values())

    @property
    def simple_unlocked(self):
        return self.successes >= 10

    def record(self, episode_id, result):
        if episode_id in self.rows:
            return
        self.rows[episode_id] = result
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'successes': self.successes,
            'required_successes': 10, 'simple_unlocked': self.simple_unlocked,
            'episodes': self.rows}, indent=2, ensure_ascii=False))
        temporary.replace(self.path)
