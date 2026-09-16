import json,subprocess,sys
from pathlib import Path
r=Path('/home/galbot/lizekai/RSI');o=r/'human-feedback/dashboard-upgrade/root-review'
sys.path.insert(0,str(r/'human-feedback/tools'))
from feedback_board import OWNERS
from store import immutable,now,digest
owner=OWNERS['ground'];assert owner=='01a0a982-cec5-71c0-b771-091c31df61f2'
claim=o/'ground-owner-handoff-claim.json'
if claim.exists():print('Existing delivery claim preserved; no repeated queue.');raise SystemExit(0)
message=('DASHBOARD-20260916 ROOT-REVIEW 工程交接（非人类回答）：主控已明确授权，本机四任务页 http://127.0.0.1:8765/#ground 的新增回答固定通知你，旧ground收件人回执保留、历史用户回答不自动重投。请在自然边界读 /home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/OWNER_INTERFACE.md；继续使用现有 auxiliary-progress.json，可补 current_problem / next_step 两个短字段。网页答案原文保存在 dashboard-upgrade/feedback/answers，同信息公开包在 feedback/packages；先保存再排队，消费后写精确绑定回答哈希的owner_ack，后续实际使用才标human_feedback_used，物理验证另记。请以工程ACK确认当前episode和可消费路径；工程ACK不是用户回答ACK。完整等待在途turn，不中断、不重放、不resume/启动其它模型或机器人；此消息只交接UI，未提出恢复操作。')
argv=[str(r/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_provider="openai"','-c','model_reasoning_effort="xhigh"','--thread',owner,'--message',message]
immutable(claim,{'at':now(),'owner':owner,'message':message,'message_sha256':digest(message.encode()),'argv':argv})
try:
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
 receipt={'at':now(),'owner':owner,'queued':p.returncode==0 and b'Queued' in p.stdout and b'usageLimitExceeded' not in p.stdout,'returncode':p.returncode,'output':p.stdout.decode(errors='replace'),'owner_ack':False,'physical_verified':False,'engineering_only':True}
except subprocess.TimeoutExpired:receipt={'at':now(),'owner':owner,'queued':False,'uncertain':True,'no_retry':True}
except OSError:receipt={'at':now(),'owner':owner,'queued':False,'launcher_unavailable':True,'no_retry':True}
immutable(o/'ground-owner-handoff-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
