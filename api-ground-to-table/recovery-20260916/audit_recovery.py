"""Local integrity review, never repairs original evidence or books costs."""
import hashlib
import json
from pathlib import Path
import time
ROOT=Path('/home/galbot/lizekai/RSI')
OUT=ROOT/'api-ground-to-table/recovery-20260916'
EP=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002'
def ref(p):
    raw=p.read_bytes()
    return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
ledger=ROOT/'artifacts/R020/shared-budget-ledger.json'
state=json.loads(ledger.read_text())
errors=[]
def verify(v):
    if isinstance(v,dict):
        if isinstance(v.get('path'),str) and 'sha256' in v:
            p=ROOT/v['path']
            if not p.is_file() or ref(p)['sha256']!=v['sha256']:
                errors.append(dict(reference=v,actual=ref(p) if p.is_file() else None))
        for x in v.values(): verify(x)
    elif isinstance(v,list):
        for x in v:verify(x)
verify(state)
completed=[]
for key,row in state['requests'].items():
    if row['state']=='inflight' and 'completion_evidence' in row:
        p=ROOT/row['completion_evidence']['path'];v=json.loads(p.read_text())
        assert ref(p)['sha256']==row['completion_evidence']['sha256']
        assert v['state']=='completed' and v['http_status']==200 and v['actual_cny_fen'] is None
        completed.append(key)
obs=json.loads((EP/'rollout/episode/observations/0023/observation.json').read_text())
index=json.loads((EP/'public_history_index.json').read_text())
index_errors=[x['public_evidence'] for x in index if ref(Path(x['public_evidence']['path']))['sha256']!=x['public_evidence']['sha256']]
result=dict(schema=1,created_at_unix=time.time(),episode='episode-0002',run_id='api-ground-002',
    terminal_kind='infrastructure_error',stop_reason='host_reboot_infrastructure_interruption',
    native_outcome_at_last_public_ack='in_progress',task_success_verified=False,
    human_failure_count_credit=False,physical_failure=False,backend='MuJoCo',
    same_episode_restorable=False,restore_basis='No complete sim/controller/history checkpoint found; runtime state was process memory. Named robot logs and reset hashes do not restore simulator/object/controller state.',
    last_public_counters=dict(api_calls_completed=54,actions=23,physical_s=108.98000000004748,at_unix=1789549658.838955),
    last_complete_standalone_action=dict(action=22,execution=ref(EP/'rollout/episode/execution_0022.json'),step_id=5224,physical_s=104.48000000004187),
    last_named_observation=dict(reference=ref(EP/'rollout/episode/observations/0023/observation.json'),observation_id=obs['observation_id'],sim_s=obs['sim_s'],
        embedded_ack={k:obs['command_status'].get(k) for k in ['command_id','status','reference_finished','start_sim_s','duration_s']},
        complete_public_rgb_bundle=False,notice='Action23 embedded ACK survives in named observation; standalone execution/RGB/trajectory files are empty. Do not erase this ACK or claim a complete recoverable trajectory.'),
    public_index_entries=len(index),public_index_reference_errors=index_errors,
    ledger=ref(ledger),ledger_json_valid=True,ledger_reference_errors=errors,
    completed_unknown_cost_request_ids=completed,
    interrupted_unknown_request=dict(request_id='api-ground-002-call-55',row=state['requests']['api-ground-002-call-55'],receipt=ref(EP/'api_calls/55/receipt.json'),replay_allowed=False,cost_known=False),
    local_accounting=dict(confirmed_fen=339,unknown_held_fen=74237,total_committed_fen=74576,cap_fen=1000000,report_interval_fen=150000,
        note='Existing empirical reservation is not a verified fee bound. No balance/quota/rate request made; all unknown holds retained.'),
    video=dict(path=str((EP/'video/episode.mp4').relative_to(ROOT)),sealed=False,ffprobe='failed: moov atom not found',original_modified=False,recovered=False))
(OUT/'interruption-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['same_episode_restorable','last_named_observation','ledger_reference_errors','local_accounting']},ensure_ascii=False,indent=2))
