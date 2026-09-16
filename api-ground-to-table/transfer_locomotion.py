"""Read-only candidate transfer: original table, current-pose-relative references.

No API, no new autonomous exploration credit, no shared-skill publication.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path('/home/galbot/lizekai/RSI/api-ground-to-table')
SOURCE = Path('/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table')
OLD = SOURCE/'campaign/episode-0006/rollout/episode'
FROZEN = SOURCE/'provenance/episodes/episode-0006'
OUT = ROOT/'transfers/original-table-locomotion-001'


def yaw(obs):
    q = obs['pelvis_world']['quaternion_wxyz']
    matrix = Rotation.from_quat(q[1:]+q[:1]).as_matrix()
    return float(np.arctan2(matrix[1, 0], matrix[0, 0]))


def rebase(response, before, current):
    """Transfer local horizontal directions, never copy source world targets."""
    result = copy.deepcopy(response)
    rotation = Rotation.from_rotvec([0, 0, yaw(current)-yaw(before)])
    for row in result['trajectory']:
        if row['active']['orientation']:
            raise ValueError('Candidate audit only supports inactive orientations')
        for name, target in row['target'].items():
            old = before['four_point_world'][name]
            fresh = current['four_point_world'][name]
            delta = np.asarray(target['position_world_m'])-old['position_world_m']
            target['position_world_m'] = (fresh['position_world_m']+rotation.apply(delta)).tolist()
            target['quaternion_wxyz'] = list(fresh['quaternion_wxyz'])
    return result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    runtime = OUT/'runtime'
    runtime.mkdir()
    source_manifest = json.loads((FROZEN/'setting_manifest.json').read_text())
    copied = {}
    for old, expected in source_manifest['episode_runtime_hashes'].items():
        relative = Path(old).relative_to(SOURCE)
        src = FROZEN/relative
        assert digest(src) == expected, f'Frozen source mismatch: {relative}'
        dest = runtime/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied[str(relative)] = expected
    for key in ('model', 'scene'):
        assert digest(source_manifest[key+'_path']) == source_manifest[key+'_sha256']
    sys.path.insert(0, str(runtime))
    import ground_task
    from rsi.policy_harness import LocalFourPointHarness
    from rsi.episode_video import EpisodeVideo
    original_factory = ground_task.tabletop_model
    # New isolated process only; original table is selected BEFORE MjData/reset/seal.
    ground_task.tabletop_model = lambda **kwargs: original_factory(table_only_offset_x=0.)
    backend = ground_task.create_backend(continuous=True)
    evaluator = ground_task.GroundEvaluator(OUT/'host_audit')
    video = EpisodeVideo(backend, OUT/'video', label='ORIGINAL TABLE | relative candidate transfer | diagnostic',
                         extra_trace=lambda b: {'qpos': b.data.qpos.tolist(), 'qvel': b.data.qvel.tolist()})
    harness = LocalFourPointHarness(backend, OUT/'rollout', image_capture=video, evaluator=evaluator)
    manifest = ground_task.setting_manifest(backend)
    manifest['layout_changes_from_tabletop_seed']['table_and_four_legs_translation_m'] = [0, 0, 0]
    manifest.update(source_episode='episode-0006', runtime_hashes=copied,
        candidate_kind='measured-pose-relative/yaw-rebased actor-generated locomotion',
        control_interface_version=source_manifest['control_interface_version'],
        continuous_chunk_contract=source_manifest['continuous_chunk_contract'],
        autonomous_exploration_credit=False, api_calls=0, human_question_count_credit=False,
        reset_provenance=backend.reset_provenance)
    save(OUT/'manifest.json', manifest)
    actions = []
    try:
        harness.start('Diagnostic transfer of candidate locomotion to original table; not task success')
        for index in range(1, 5):
            before = json.loads((OLD/f'observations/{index-1:04d}/observation.json').read_text())
            current = json.loads(harness.latest_path.read_text())
            original = json.loads((OLD/f'execution_{index:04d}.json').read_text())['response']
            response = rebase(original, before, current)
            response['request_id'] = f'original-table-transfer-{index}'
            response['reason'] = '问题：验证自主生成移动候选在原桌位是否可迁移。目标：可用移动经验。不可重犯：不拷贝世界坐标，不算自主探索或完整任务成功。'
            harness.scalebfm_act(str(harness.latest_path), response)
            row = {'action': index, 'sim_s': float(backend.data.time), 'stop_reason': backend.reason,
                   'phase_results': evaluator.audit.result()['phase_results']}
            actions.append(row)
            print(json.dumps(row), flush=True)
            if backend.reason:
                break
    finally:
        evaluator.close()
        video.close()
    result = {'backend': 'MuJoCo', 'new_physics': True, 'original_table_offset_m': 0,
              'candidate_source': 'actor-generated episode-0006 actions1-4, rebased each step',
              'autonomous_exploration_credit': False, 'full_task_success_credit': False,
              'human_failure_threshold_credit': False, 'api_calls': 0, 'actions': actions,
              'audit': evaluator.audit.result(), 'video': str(OUT/'video/episode.mp4')}
    save(OUT/'result.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
