import json,subprocess,sys
from pathlib import Path
r=Path('/home/galbot/lizekai/RSI');o=r/'human-feedback/dashboard-upgrade/publisher-sync'
sys.path.insert(0,str(r/'human-feedback/tools'))
from feedback_board import OWNERS
from store import immutable,now,digest
owner=OWNERS['simple'];assert owner=='01a0a867-d7aa-71f2-8547-e264d6d09ede'
claim=o/'simple-handoff-claim.json'
if claim.exists():print('Existing claim preserved; no repeated handoff.');raise SystemExit(0)
message=('DASHBOARD-PUBLISHER-SYNC-20260916 工程交接（非人类回答）：现有 http://127.0.0.1:8765/ 已按 instruction-cap-integration/status.json 分项显示ARCH组合长度、MEMORY-PRIORITY、相机标定在SIMPLE上线；门16/水龙头8只作为共同变更的调用链/受限skill_update/独立审计回归，不作单因或泛化归因。NT只显示无期限turn/start ACK与不确定提交锁部分上线，自动闭合失败turn续接仍待audit-compat离线兼容；shared core未晋升。已补真实尝试的oven-campaign行，原五项顺序不变，结果封口与独立审计计分分开，残留等待标记不覆盖终态。继续在现有public-progress/PROGRESS/campaign_audit写公开current_problem/next_step与审计计数即可；UI不进入host审计正文。请在自然边界ACK本次工程交接，勿中断推理、重放动作或为网页启动新模型/物理。UI仍由01a0a980唯一发布，原owner映射和所有回答保留。说明：/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/OWNER_INTERFACE.md；回执目录publisher-sync。')
argv=[str(r/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_provider="openai"','-c','model_reasoning_effort="xhigh"','--thread',owner,'--message',message]
immutable(claim,{'at':now(),'owner':owner,'message':message,'message_sha256':digest(message.encode()),'argv':argv})
try:
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
 receipt={'at':now(),'owner':owner,'queued':p.returncode==0 and b'Queued' in p.stdout and b'usageLimitExceeded' not in p.stdout,'returncode':p.returncode,'output':p.stdout.decode(errors='replace'),'owner_ack':False,'physical_verified':False,'engineering_only':True}
except subprocess.TimeoutExpired:receipt={'at':now(),'owner':owner,'queued':False,'uncertain':True,'no_retry':True}
except OSError:receipt={'at':now(),'owner':owner,'queued':False,'launcher_unavailable':True,'no_retry':True}
immutable(o/'simple-handoff-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
