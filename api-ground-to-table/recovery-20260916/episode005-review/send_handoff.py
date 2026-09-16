"""One auxiliary queue/inbox delivery of the new005 boundary; no model calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
p=OUT/'review.json';digest=hashlib.sha256(p.read_bytes()).hexdigest()
msg=f'''GROUND-005-HTTP429-20260916：当前问题：独立005已结束，9调用完成、第10请求HTTP429，4动作/20.04秒；当前actor已退出，自动接续暂停。总目标：原桌位红块走近抓持携物放桌。不可重犯：不重发002/55、004/43、005/10，不用新batch或账号绕过429、不把系统中断算物理失败。
唯一辅助owner仍为01a0a982-cec5-71c0-b771-091c31df61f2；现有唯一watcher456959存活，本owner已写blocked。原结果/回执保持，三笔未知hold继续完整占用，不查询quota/费率；HTTP429子码/正文未记录，不能断言是额度或限流。无006。005完整真实录像20.08秒网页/videos/api-ground-episode-0005.mp4，Range206已核验。新公开review {p.relative_to(ROOT)} SHA256 {digest}。
动作2/3/4实际左/右/左踝推进165/152/140mm，但最后右支撑足后退32mm；方向较004小有多条件混杂，后段尚未检验，不能晋升步态。条件化候选见同目录experience-v005.json，未改shared publisher或运行控制器。SIMPLE门19/boxplace4最新公开记忆已留作下一安全边界审阅，不追认005已使用。只交接新系统边界和公共反例，不要求其它分支停止/修改任务，不唤醒主账号。排队不是ACK或集成。'''
with (OUT/'handoff.txt').open('x') as f:f.write(msg+'\n')
receipt=OUT/'framework-queue.json'
with receipt.open('x') as f:json.dump(dict(state='attempt_started',at_unix=time.time()),f)
r=subprocess.run([str(ROOT/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_provider="openai"',
    '-c','model_reasoning_effort="xhigh"','--thread','01a0a94d-6143-74c0-80cd-03d0b61acaf0','--message',msg],capture_output=True,text=True)
ok=r.returncode==0 and 'Queued' in r.stdout and 'usageLimitExceeded' not in r.stdout+r.stderr
receipt.write_text(json.dumps(dict(queued=ok,acknowledged=False,stdout=r.stdout,stderr=r.stderr,returncode=r.returncode,
    message_sha256=hashlib.sha256(msg.encode()).hexdigest()),ensure_ascii=False,indent=2)+'\n')
with (ROOT/'artifacts/R020/supervisor-inbox.md').open('a') as f:f.write('\n\n## GROUND-005-HTTP429-20260916（新系统边界与公开反例）\n'+msg+'\n')
print(json.dumps(dict(framework_queued=ok,simple_inbox_appended=True)))
if not ok:raise SystemExit('Queue uncertain; no retry')
