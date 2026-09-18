"""Finalize an independently replayed C2 review after explicit owner RGB inspection.

This is an offline evidence interface, not an actor tool or a new supervisor.
It starts no simulation/model requests and never changes an episode outcome.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.coverage_rounds import classify
from rsi.training_gate import reviewed_attempt


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize(ep, independent, integrity, frames, assessment, reviewer, check_only=False):
    ep, independent, integrity = [p.resolve(strict=True) for p in (ep, independent, integrity)]
    assert ROOT in ep.parents and ROOT in independent.parents and ROOT in integrity.parents
    assert assessment.strip() and reviewer.strip() and frames
    x, original = read(independent), read(ep/'result.json')
    assert x['episode'] == str(ep) and x['result'] == 'PASS' and not x['issues']
    assert x['host_criteria_replay_pass'] and x['training_full_task_criteria_satisfied']
    assert x['frozen_curriculum']['level'] == 'C2'
    assert x['frozen_curriculum'] == original['curriculum_contract']
    assert original['error'] is None and original['stop_reason'] == 'task_success'
    assert original['raw_native_final_flag'] is True
    assert x['reset_id'] == read(ep/'reset-receipt.json')['reset_id']
    assert x['final_host_sample']['command_complete'] is True
    assert x['final_host_sample']['native_success'] is True
    matches = [r for r in read(integrity)['rows'] if r['episode'] == str(ep)]
    assert len(matches) == 1
    row = matches[0]
    assert row['reset_id'] == x['reset_id'] and row['actions'] == original['actions']
    assert row['full_decode_passed'] and row['public_ACK_chain_verified']
    assert row['unique_request_ids'] and row['all_dynamic_results_present']
    assert row['terminal_status'] == 'complete_terminal_sequence'
    for evidence in (row['evidence_sha256'], x['source_sha256']):
        for path, sha in evidence.items():
            assert digest(Path(path)) == sha, f'Changed review source: {path}'
    evidence = [Path(p) for p in row['evidence_sha256']] + [ep/'agent/NOTES.md', ep/'agent/SKILL.md']
    evidence += [ep/'rollout/episode/observations'/f'{n:04}'/'head_stereo_left.png' for n in frames]
    assert all(p.is_file() and ep in p.resolve().parents for p in evidence)
    plan = read(ROOT/'artifacts/six-transfer-20260917/plan.json')
    classified = classify(ep, plan['started_at'], plan['id'])
    assert classified['complete'] and classified['success'] and not classified.get('curriculum_complete')
    target = ep/'training-attempt-review.json'
    if target.exists():
        old = read(target)
        assert old['reset_id'] == x['reset_id'] and old['audited_task_success'] is True
        for path, sha in old['evidence_sha256'].items():
            assert digest(Path(path)) == sha
        return dict(status='existing_verified_not_rewritten', episode=ep.name, review=str(target))
    if check_only:
        return dict(status='sources_verified_no_write', episode=ep.name)
    copied = ep/'independent-curriculum-replay.json'
    if copied.exists():
        assert digest(copied) == digest(independent)
    else:
        shutil.copy2(independent, copied)
    evidence.append(copied)
    minimum = x['retention_intervals']['right']['min_whole_object_clearance_m']
    duration = x['final_release_window']['duration_s']
    review = dict(contract='independent-training-attempt-review-v1', reviewed_at=time.time(),
        reviewer=reviewer, host_only=True, actor_input_allowed=False,
        env_id=x['frozen_curriculum']['env_id'], episode_id=ep.name, reset_id=x['reset_id'],
        curriculum_level='C2', curriculum_spec_sha256=x['frozen_curriculum']['spec_sha256'],
        complete_valuable_attempt=True, audited_curriculum_success=True,
        audited_task_success=True, full_task_success=True, official_success=False,
        termination_class='full_task_training_success',
        reason=f'Independent frozen C2 replay, complete ACK/model-turn/video checks and owner RGB inspection passed. Right/left independent retention precedes original-table released stability {duration:.3f} s; current native and standing verified. Right minimum clearance {minimum*1000:.6f} mm; preserve 20 ms sampling and margin limitations. No inference/API cutoff or unknown action. Not official benchmark credit. Owner visual assessment: '+assessment,
        evidence_paths=[str(p) for p in evidence],
        evidence_sha256={str(p):digest(p) for p in evidence},
        integrity={k:v for k,v in row.items() if k not in ('evidence_sha256','source_classification')},
        public_visual_inspection=dict(left_observations=frames, assessment=assessment,
            limit='Precise contact/support predicates come from recorded host replay, not RGB alone.'),
        finalizer=dict(path=str(Path(__file__).resolve()),sha256=digest(Path(__file__).resolve())))
    # Exclusive create prevents an overlapping reviewer from overwriting a review.
    with target.open('x') as stream:
        json.dump(review, stream, indent=2); stream.write('\n')
    credit = reviewed_attempt(ep, classified)
    assert credit['complete'] and credit['audited_success']
    return dict(status='reviewed_full_task_training_success', episode=ep.name,
        review=str(target), official_success=False, new_model_calls=0, new_physics_actions=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('episode', type=Path)
    p.add_argument('--independent', required=True, type=Path)
    p.add_argument('--integrity', required=True, type=Path)
    p.add_argument('--rgb-frames', required=True, nargs='+', type=int)
    p.add_argument('--visual-assessment', required=True)
    p.add_argument('--reviewer', required=True)
    p.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    print(json.dumps(finalize(a.episode,a.independent,a.integrity,a.rgb_frames,
        a.visual_assessment,a.reviewer,a.check_only)))
