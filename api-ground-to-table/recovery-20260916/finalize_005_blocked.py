"""Refresh final administrative disposition only; never alter physical time."""
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path('/home/galbot/lizekai/RSI');REC=Path(__file__).resolve().parent;OUT=REC/'episode005-review'
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'));from actor import save
origin=json.loads((REC/'supervision/active-owner.json').read_text())
state_path=REC/'supervision/owner-state.json';state=json.loads(state_path.read_text())
assert state['status']=='blocked' and state['owner_log']==origin['log'] and state['episode']=='episode-0005'
state.update(written_ns=time.time_ns(),final_review='api-ground-to-table/recovery-20260916/episode005-review/FINAL.md',
    required_condition='网关限制解除的可核验证据及安全恢复条件；不查询额度、不自动探测或重试；随后仍需独立reset、新batch/auth和正常执行审批。')
save(state_path,state)
for p in (ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json',REC/'progress.json',ROOT/'api-ground-to-table/status.json'):
    d=json.loads(p.read_text());assert d['actions']==4 and d['api_calls_completed']==9 and d['state']=='ended'
    d.update(supervisor_alive=True,actor_alive=False,supervisor_pid=456959,supervisor_blocker='gateway_http_429',
        supervisor_state='current_owner_finishing_then_blocked_no_automatic_resume',review_complete=True,
        final_report='api-ground-to-table/recovery-20260916/episode005-review/FINAL.md',updated_at_unix=time.time(),
        current_problem='005已因HTTP429停止：9调用完成、10号请求费用/结果未知；4动作/20.04秒。复盘完成，自动接续暂停。',
        next_step='需网关限制解除的可核验证据及安全恢复条件；不查额度、不重试旧请求、不换账号。随后仍需独立reset、新授权及正常执行审批。')
    save(p,d)
with (REC/'RECOVERY.md').open('a') as f:
    f.write('\n005最终自诊断与交接 '+str(time.time())+'：episode005-review/REVIEW.md和FINAL.md已完成；20.08秒完整录像网页发现及Range206通过，4动作/20.04秒物理时间保持。原002/004/005清单与旧ground账本行无修改，三笔未知请求不重发。现有watcher456959存活持锁，005 actor已退出；owner-state=blocked绑定当前同一辅助owner日志。当前工程turn自然结束后保持可观测阻塞，恢复需HTTP429限制解除的可核验证据与安全条件，不进行额度/价格查询或自动探测。没有006；框架辅助queue和SIMPLE既有inbox交接完成，未声称消费ACK。\n')
receipt=dict(at_unix=time.time(),owner=state['owner'],status='blocked',blocker='gateway_http_429',
    owner_log=state['owner_log'],written_ns=state['written_ns'],actor_binding=state['actor_binding'],
    public_progress_sha256=hashlib.sha256((ROOT/'api-ground-to-table/actor-adapter/auxiliary-progress.json').read_bytes()).hexdigest(),
    final_report_sha256=hashlib.sha256((OUT/'FINAL.md').read_bytes()).hexdigest(),
    last_physical_update_at_unix=d['last_physical_update_at_unix'],new_episode_started=False)
with (OUT/'final-disposition-receipt.json').open('x') as f:f.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=state['status'],episode=state['episode'],actor_alive=False,watcher_pid=456959,blocker=state['blocker'])))
