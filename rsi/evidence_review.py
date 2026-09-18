"""Host-only review packets from existing evidence; no model calls or reward writes.

Adapted conceptually from ENPIRE's predicate diagnostics and reflection loop.
Native flags, independent task audit and phase evidence remain separate here.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assess(result, audit, status, progress, *, audit_stale=False):
    raw = result.get('raw_native_final_flag')
    if raw is None and not result.get('completion_contract'):
        outcome = result.get('native_outcome')
        raw = True if outcome == 'success' else False if outcome == 'failure' else None
    reviewed = audit.get('audited_task_success')
    verified = (reviewed is True and status.get('host_success_complete') is True
                and not audit_stale and not result.get('error'))
    conflict = raw is True and reviewed is False
    if result.get('error'):
        verdict, next_step = 'infrastructure_interruption', 'repair_infrastructure'
    elif audit_stale:
        verdict, next_step = 'stale_audit', 'refresh_evidence_review'
    elif conflict:
        verdict, next_step = 'conflict', 'review_verifier_and_missing_task_evidence'
    elif verified:
        verdict, next_step = 'verified_task_success', 'reuse_within_verified_scope'
    elif (result.get('stop_reason') or '').startswith('progress_'):
        verdict, next_step = 'progress_learning_stop', 'learn_missing_prerequisite'
    elif reviewed is False or result.get('native_outcome') == 'failure':
        verdict, next_step = 'task_not_completed', 'locate_first_divergence'
    else:
        verdict, next_step = 'unknown', 'collect_missing_evidence'
    mapping = {'done':'confirmed_pass', 'stopped':'stopped_unmet',
               'active':'unresolved', 'blocked':'not_attempted'}
    phases = [dict(phase=p['id'],status=mapping.get(p.get('status'),'unknown'),
        source='host_progress_contract',contract=progress.get('contract'))
        for p in progress.get('phases',[])]
    return dict(verdict=verdict, next_step=next_step, native_final_flag=raw,
        task_success_verified=verified, independent_task_audit=reviewed,
        phase_evidence=phases, stability_credit=False, formal_credit=False,
        next_learning_focus=progress.get('next_learning_focus'),
        attribution='Evidence projection, not a new physical audit or proven root cause.')


def review_episode(episode):
    from tools.audit_simple_campaigns import episode_status
    episode = Path(episode).resolve()
    if not episode.is_relative_to(ROOT):
        raise ValueError('Review only this project evidence')
    sources = {}
    def read(relative):
        p = episode/relative
        if not p.is_file():return {}
        data = p.read_bytes()
        sources[str(p.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
        return json.loads(data)
    result = read('result.json')
    if not result:raise ValueError('Episode is not terminal; never label an unfinished trial')
    audit = read('success_review.json')
    failure = read('failure_review.json')
    progress = read('rollout/progress.json')
    scene = read('video/scene_setup.json')
    spec = read('agent/task_specification.json')
    status = episode_status(episode)
    for p in sorted(episode.glob('turn_*.json')):read(p.name)
    expected = audit.get('evidence_sha256',{})
    actual = sources[str((episode/'result.json').relative_to(ROOT))]
    result_names = ['result.json',str(episode/'result.json'),str((episode/'result.json').relative_to(ROOT))]
    stale = any(expected[k] != actual for k in result_names if k in expected)
    review_reset = audit.get('reset',{}).get('reset_id')
    if review_reset and status.get('reset_id') and review_reset != status['reset_id']:stale=True
    assessment = assess(result,audit,status,progress,audit_stale=stale)
    context = dict(task_id=spec.get('env_id') or scene.get('env_id') or audit.get('task'),
        reset_id=status.get('reset_id'),seed=scene.get('seed'),
        policy_sha256=result.get('starting_skill_sha256'),
        controller=scene.get('pd_profile'),completion_contract=status.get('completion_contract'),
        progress_contract=progress.get('contract'),
        feedback_tier=result.get('feedback_tier') or ('human_assisted' if status.get('human_feedback_used') else 'no_human_feedback_recorded'),
        protocol_phase=(result.get('execution_profile') or {}).get('phase','legacy_learning'))
    packet = dict(contract='evidence-review-v1',actor_access=False,
        source_episode=str(episode.relative_to(ROOT)),context=context,assessment=assessment,
        audit_explanation=audit.get('why') or audit.get('limitations') or failure.get('why'),
        public_evidence_root=str(episode/'rollout'),video=str(episode/'video/episode.mp4'),
        evidence_sha256=sources,model_requests=0,source_records_modified=False)
    packet['evidence_id']=hashlib.sha256(json.dumps(packet,sort_keys=True).encode()).hexdigest()
    return packet


def save_review(packet, directory):
    """Append a revision; late independent audits generate a new immutable packet."""
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    path = directory/(packet['evidence_id']+'.json')
    if not path.exists():
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
        temp.replace(path)
    return path
