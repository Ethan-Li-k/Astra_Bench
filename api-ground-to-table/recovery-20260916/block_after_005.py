"""Publish the observed HTTP429 boundary; no request or retry."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');REC=Path(__file__).resolve().parent;OUT=REC/'episode005-review'
OUT.mkdir(exist_ok=False)
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));from actor import save
ep=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0005'
result=json.loads((ep/'result.json').read_text())
assert result['api_calls_completed']==9 and result['api_requests_started']==10 and result['actions']==4
assert 'RuntimeError: HTTP 429; no retry; expense unknown' in (REC/'run-005.log').read_text()
for p in (ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',REC/'progress.json',ROOT/'api-ground-to-table/status.json'):
    shutil.copy2(p,OUT/('before-'+p.parent.name+'-'+p.name))
    d=json.loads(p.read_text());d.update(state='ended',terminal_kind='infrastructure_error',
        recovery_state='blocked_http429_no_automatic_retry',actor_alive=False,inference_in_flight=False,
        api_calls_completed=9,api_requests_started=10,actions=4,physical_s=20.040000000001807,
        supervisor_blocker='gateway_http_429',supervisor_alive=True,blocker='gateway_http_429',
        current_problem='005已因HTTP429停止：9调用完成、10号请求费用/结果未知；4动作/20.04秒。自动接续暂停。',
        next_step='需网关限制解除的可核验证据及恢复条件，再准备独立新尝试；不查额度、不自动重试、不换账号。',
        current_video_status='sealed_ffprobe_verified_complete',updated_at_unix=time.time())
    save(p,d)
origin=json.loads((REC/'supervision/active-owner.json').read_text());p=REC/'supervision/owner-state.json'
shutil.copy2(p,OUT/'before-owner-state.json')
save(p,dict(status='blocked',written_ns=time.time_ns(),owner_log=origin['log'],owner=origin['thread'],
    episode='episode-0005',actor_binding='api-ground-to-table/recovery-20260916/supervision/actor-005.json',
    blocker='gateway_http_429',required_condition='Verifiable gateway restriction resolution and an explicit safe resumption boundary; no quota inquiry or automatic probe/retry.',
    unknown_requests_never_repeat=['api-ground-002-call-55','api-ground-004-call-43','api-ground-005-call-10']))
rows=json.loads((ROOT/'artifacts/R020/shared-budget-ledger.json').read_text())['requests']
unknown={k:rows[k] for k in ('api-ground-002-call-55','api-ground-004-call-43','api-ground-005-call-10')}
assert all(x['state']=='inflight' and x['reserved_fen']==1217 for x in unknown.values())
(OUT/'blocker.json').write_text(json.dumps(dict(at_unix=time.time(),blocker='gateway_http_429',
    http_status_observed_in_original_log=429,body_error_code_available=False,
    rate_limit_vs_quota_not_determined=True,unknown_rows=unknown,automatic_retry=False,
    new_run006_prepared=False,actor_alive=False,watcher_pid=456959,
    original_result_sha256=hashlib.sha256((ep/'result.json').read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n')
with (REC/'RECOVERY.md').open('a') as f:f.write('\n## 005真实HTTP429阻塞（覆盖此前在途快照）\n005已结束：9完成调用/10发起、4动作/20.04秒。第10次原日志明确HTTP429；响应体原因未记录，不能判定具体为速率或额度。未知费用与002/55、004/43均保留各1217分。自动接续owner-state已blocked，现有watcher继续存活守候但不得自动发模型请求。需要网关限制解除的可核验证据及恢复条件；不查额度、不自动探测重试、不换账号、不新建006绕过。完整20.08秒录像与追加复盘在episode005-review。\n')
print('HTTP429 boundary published; owner-state blocked; no requests sent')
