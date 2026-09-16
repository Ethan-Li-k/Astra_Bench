import sys,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'tools'))
from feedback_board import OWNERS
from store import immutable,digest,now
out=Path(__file__).resolve().parent
for task,owner in OWNERS.items():
 claim=out/('handoff-'+task+'-claim.json')
 if claim.exists():continue
 message=(f'DASHBOARD-20260916 工程交接（非人类回答）。现有本地页 http://127.0.0.1:8765/ 正在升级为四任务、最新封口视频/公开快照及可保存回答。请读 /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/OWNER_INTERFACE.md；沿用现有状态源，仅在自然边界补公开状态/反馈消费ACK。收到请写 DASHBOARD-20260916 ACK（本目录owner-acks/{task}.json或自身公开回执），列当前episode、公开进度/录像路径、能否读取feedback/answers。后续反馈保存→排队→ownerACK→物理验证分开；实际使用才标human_feedback_used。完整等待在途推理，不中断、不重放、不并发resume、不新增主账号调用。'+('此为UI-only交接；你继续独占no-truncation审查，网页工程不改你的文件或机器人源码。' if task=='framework' else '若公开实时画面尚无输出请如实说明，勿因网页要求改在途录制器。'))
 immutable(claim,{'at':now(),'owner':owner,'message':message,'message_sha256':digest(message.encode())})
 try:
  r=subprocess.run(['/home/galbot/lizekai/RSI/codex-account-2/run.sh','queue','-m','gpt-6-astra','-c','model_reasoning_effort="xhigh"','--thread',owner,'--message',message],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
  ok=r.returncode==0 and b'Queued' in r.stdout and b'usageLimitExceeded' not in r.stdout
  receipt={'at':now(),'owner':owner,'queued':ok,'owner_ack':False,'physical_verified':False,'returncode':r.returncode,'output':r.stdout.decode(errors='replace'),'sha256':digest(r.stdout)}
 except subprocess.TimeoutExpired:receipt={'at':now(),'owner':owner,'queued':False,'uncertain':True,'no_retry':True}
 except OSError:receipt={'at':now(),'owner':owner,'queued':False,'launcher_unavailable':True,'no_retry':True}
 immutable(out/('handoff-'+task+'-receipt.json'),receipt)
 print(task,json.dumps(receipt,ensure_ascii=False),flush=True)
 if not receipt.get('queued'):break
