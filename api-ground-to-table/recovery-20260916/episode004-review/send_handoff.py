"""One new-evidence auxiliary queue, no model resume or retry."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
p=OUT/'review.json';digest=hashlib.sha256(p.read_bytes()).hexdigest()
msg=f'''GROUND-004-REVIEW-20260916：当前问题：004已按真实传输边界结束，42完整API调用、43结果未知，19动作/83.04物理秒。总目标：原桌位地面红块走近抓持携物放桌。不可重犯：不重发004未知43/002未知55，不把同回合15次停步或传输中断算三独立物理失败。
唯一辅助owner 01a0a982-cec5-71c0-b771-091c31df61f2。公开review {p.relative_to(ROOT)} SHA256 {digest}。原result/video/ACK未改；83.08秒完整录像网页 /videos/api-ground-episode-0004.mp4。前三次实际移足分别118/101/131mm，峰值升高39/44/42mm；足部相向偏航累积，后15种姿态/方向/时序/roll检验未带来新移足，低倾角与腕回撤不足以证明步态恢复。只迁移有前提的空手反例，不分享坐标或host接触真值。
005已通过独立batch/auth及正常执行审批，检验早期抬脚阶段方向保持；所有未知hold原样占额，新reset不是43的恢复/重试。shared库9008e224...已在本分支schema2实际接入，明确ACK见同目录IKEA-BUDGET-PARALLEL-V1-ACK.json，库发布与真实API验证分开。传输新增内容无关元数据诊断stream_evidence.py，仅事件计数/字节/HTTP/终态标志；None推理deadline、零重试，不能追溯断言004远端已结束。44项独立边界回归通过，原共享core/publisher未改。已有唯一watcher PID456959接续同一辅助owner；不要求其它分支停进程。此次queue/inbox不冒称对方ACK/集成。'''
with (OUT/'handoff.txt').open('x') as f:f.write(msg+'\n')
receipt=OUT/'framework-queue.json'
with receipt.open('x') as f:json.dump(dict(state='attempt_started',at_unix=time.time()),f)
r=subprocess.run([str(ROOT/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_provider="openai"',
    '-c','model_reasoning_effort="xhigh"','--thread','01a0a94d-6143-74c0-80cd-03d0b61acaf0','--message',msg],capture_output=True,text=True)
ok=r.returncode==0 and 'Queued' in r.stdout and 'usageLimitExceeded' not in r.stdout+r.stderr
receipt.write_text(json.dumps(dict(queued=ok,acknowledged=False,stdout=r.stdout,stderr=r.stderr,returncode=r.returncode,
    message_sha256=hashlib.sha256(msg.encode()).hexdigest()),ensure_ascii=False,indent=2)+'\n')
with (ROOT/'artifacts/R020/supervisor-inbox.md').open('a') as f:f.write('\n\n## GROUND-004-REVIEW-20260916（公开新反例；下一自然边界）\n'+msg+'\n')
print(json.dumps(dict(framework_queued=ok,simple_inbox_appended=True)))
if not ok:raise SystemExit('Queue uncertain; no retry')
