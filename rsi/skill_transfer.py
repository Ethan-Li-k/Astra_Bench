"""Compose a short shared core and preserved task experience without global promotion."""
import hashlib
import json
from pathlib import Path
from rsi.skill_learning import skill_size

ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/'skills/loco-manip-core/SKILL.md'
GRASP=ROOT/'artifacts/R018/campaign'


def reviewed_task_sources(manifest):
    """Load supervisor-reviewed public task candidates, without global promotion."""
    manifest=Path(manifest)
    if not manifest.exists():return {}
    data=json.loads(manifest.read_text())
    if data.get('actor_access') is not True:
        raise ValueError('Transfer manifest must contain actor-public information only')
    result={}
    for source in data['sources']:
        sid=source['id'];path=Path(source['path']).resolve()
        parts=path.relative_to((ROOT/'artifacts').resolve()).parts
        public_version=(len(parts)==5 and parts[2:4]==('memory','versions')
                        and path.suffix=='.md' and path.is_file())
        public_rollout=(len(parts)==4 and parts[2].startswith('episode-')
                        and parts[3]=='rollout' and path.is_dir())
        if not sid.startswith('transfer_') or sid in result or not (public_version or public_rollout):
            raise ValueError('Reviewed transfer must name a unique public skill version or rollout')
        if not source.get('applicability') or not source.get('when_not_to_use'):
            raise ValueError('Reviewed transfer requires applicability and negative-transfer limits')
        digest=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if public_version and digest!=source.get('sha256'):
            raise ValueError('Reviewed skill source changed after review')
        result[sid]={k:v for k,v in source.items() if k!='id'}
        result[sid].update(path=str(path),scope='reviewed_task_candidate',sha256=digest,
                           promotion='Candidate only; shared core is unchanged.')
    return result


def prepare_hybrid_skill(campaign, skill):
    campaign,skill=Path(campaign),Path(skill)
    campaign.mkdir(parents=True,exist_ok=True)
    manifest=campaign/'hybrid-assembly.json'
    if not manifest.exists():
        previous=skill.read_text() if skill.exists() else ''
        backup=campaign/'pre-hybrid-SKILL.md'
        if previous:backup.write_text(previous)
        if '## Tested experience\n' in previous:
            local=previous.split('## Tested experience\n',1)[1].split('\n## Audit',1)[0].strip()
        else:
            local=('Read this task\'s latest experience and prior skill selectively. '
                   'Preserve applicable local lessons, but do not copy cube coordinates or '
                   'assume task success transfers. Add verified task-specific corrections here '
                   'after the next physical attempt.')
        core=CORE.read_text().split('---',2)[-1].strip()
        text=('---\nname: loco-manip-direct\ndescription: Apply shared visual control methods '
              'and task-local evidence.\n---\n\n'+core+'\n\n## Task specialization\n\n'+local+'\n')
        limits={'words':831,'characters':6250,'non_whitespace':5357}
        if any(skill_size(text)[k]>v for k,v in limits.items()):
            raise ValueError('Assembled shared + task skill exceeds cap; compress before running')
        skill.parent.mkdir(parents=True,exist_ok=True);skill.write_text(text)
        manifest.write_text(json.dumps({'layout':'shared_core_plus_task_specialization',
            'author':'host composition from existing self-experience; not a new learned result',
            'shared_core':str(CORE),'shared_core_sha256':hashlib.sha256(CORE.read_bytes()).hexdigest(),
            'grasp_source':str(GRASP/'memory/versions/0014.md'),
            'previous_skill':str(backup) if previous else None,
            'previous_sha256':hashlib.sha256(previous.encode()).hexdigest() if previous else None,
            'assembled_sha256':hashlib.sha256(text.encode()).hexdigest(),'size':skill_size(text),
            'promotion':'Task revisions stay local; shared changes require separate validation.'},indent=2))
    paths={'shared_core':CORE,'grasp_v14':GRASP/'memory/versions/0014.md',
           'grasp_success_437':GRASP/'episode-0437/rollout',
           'grasp_success_438':GRASP/'episode-0438/rollout',
           'task_current_skill':skill,'task_previous_skill':campaign/'pre-hybrid-SKILL.md',
           'task_experience':campaign/'memory/experience.jsonl'}
    sources={key:{'path':str(path.resolve()),'scope':('shared_candidate' if key=='shared_core'
                    else 'prior_grasp' if key.startswith('grasp') else 'task_local'),
                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
            for key,path in paths.items() if path.exists()}
    sources.update(reviewed_task_sources(campaign/'reviewed-task-sources.json'))
    return sources
