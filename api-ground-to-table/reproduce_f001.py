"""Re-run frozen F001 actions in a new simulator; no API or policy generation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path('/home/galbot/lizekai/RSI/api-ground-to-table')
SOURCE = Path('/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table')
EPISODE = SOURCE/'campaign/episode-0004'
FROZEN = SOURCE/'provenance/episodes/episode-0004'
OUT = ROOT/'reproductions/F001-baseline-001'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=False)
    snapshot = OUT/'runtime'
    snapshot.mkdir()
    manifest = json.loads((FROZEN/'setting_manifest.json').read_text())
    sources = []
    for old, expected in manifest['episode_runtime_hashes'].items():
        relative = Path(old).relative_to(SOURCE)
        source = FROZEN/relative
        assert digest(source) == expected, f'Frozen runtime mismatch: {relative}'
        target = snapshot/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        sources.append({'relative':str(relative), 'sha256':expected})
    for name in ('model', 'scene'):
        assert digest(manifest[name+'_path']) == manifest[name+'_sha256']
    sys.path.insert(0, str(snapshot))
    from ground_task import create_backend, GroundEvaluator, model_digest
    from rsi.policy_harness import LocalFourPointHarness
    from rsi.episode_video import EpisodeVideo
    import numpy as np

    backend = create_backend(continuous=True)
    old_reset = json.loads((EPISODE/'reset_provenance.json').read_text())
    assert backend.reset_provenance['settled_state_sha256'] == old_reset['settled_state_sha256'], 'Initial qpos/qvel mismatch; do not call this matched reproduction'
    assert model_digest(backend.model) == manifest['compiled_dynamics_sha256'], 'Scene/dynamics seal mismatch'
    (OUT/'provenance.json').write_text(json.dumps({'frozen_sources':sources,
        'source_episode':str(EPISODE),'reset':backend.reset_provenance,
        'initial_qpos_qvel_hash_match':True,'new_process_pid':os.getpid(),
        'method':'Regenerate frozen initialization and warm-start; no opaque whole-state checkpoint was saved.',
        'human_feedback_triggered':True,'policy_changed':False,'api_calls':0,
        'diagnostic_only':True,'historical_table_offset_m':.55},indent=2))
    capture = EpisodeVideo(backend,OUT/'video',label='F001 NEW PHYSICS REPRODUCTION | fixed old actions | no API',
        extra_trace=lambda sim:{'qpos':sim.data.qpos.tolist(),'qvel':sim.data.qvel.tolist(),
            'normalized_action':sim.adapter.action_history[0,-1].tolist()})
    evaluator=GroundEvaluator(OUT/'host_audit')
    harness=LocalFourPointHarness(backend,OUT/'rollout',image_capture=capture,evaluator=evaluator)
    try:
        harness.start('DIAGNOSTIC: reproduce historical F001 failed actions without learning or success credit')
        for n in range(1,4):
            original=json.loads((EPISODE/f'rollout/episode/execution_{n:04d}.json').read_text())
            harness.scalebfm_act(str(harness.latest_path),original['response'])
            print(json.dumps({'action_completed':n,'sim_s':float(backend.data.time),'stop_reason':backend.reason}),flush=True)
    finally:
        evaluator.close()
        capture.close()
    old=[json.loads(line) for line in (EPISODE/'video/robot_trace.jsonl').read_text().splitlines()]
    new=[json.loads(line) for line in (OUT/'video/robot_trace.jsonl').read_text().splitlines()]
    same_length=len(old)==len(new)
    errors={key:max(float(np.max(np.abs(np.array(a['host_render_state'][key])-np.array(b['host_render_state'][key])))) for a,b in zip(old,new))
        for key in ('qpos','qvel','normalized_action')}
    time_error=max(abs(a['sim_s']-b['sim_s']) for a,b in zip(old,new))
    response=[]
    for n,link in [(1,'right_ankle_roll_link'),(2,'left_ankle_roll_link'),(3,'right_wrist_yaw_link')]:
        motion=json.loads((OUT/f'rollout/motion_{n:04d}/proprioception.json').read_text())['samples']
        z=[s['four_point_world'][link]['position_world_m'][2] for s in motion]
        response.append({'action':n,'link':link,'peak_rise_mm':1000*(max(z)-z[0])})
    result={'backend':'MuJoCo','kind':'new_physics_fixed_action_failure_reproduction',
        'video_replay_only':False,'api_calls':0,'new_success_credit':False,
        'initial_qpos_qvel_hash_match':True,'same_sample_count':same_length,
        'original_samples':len(old),'new_samples':len(new),'max_sample_time_error_s':time_error,
        'max_recorded_errors':errors,'recorded_trajectory_exact_match':same_length and time_error==0 and all(v==0 for v in errors.values()),
        'measured_responses':response,'audit':evaluator.audit.result(),
        'policy_human_feedback_used':False,'triggered_by_human_feedback':True,
        'planning_rule_tested':False,
        'interpretation':'Baseline only. Human reachability-stage rule does not itself diagnose or fix absent foot lift.',
        'video':str(OUT/'video/episode.mp4')}
    (OUT/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    main()
