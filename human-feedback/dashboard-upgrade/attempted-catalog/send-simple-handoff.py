import json,subprocess,sys
from pathlib import Path
r=Path('/home/galbot/lizekai/RSI');o=r/'human-feedback/dashboard-upgrade/attempted-catalog'
sys.path.insert(0,str(r/'human-feedback/tools'))
from feedback_board import OWNERS
from store import immutable,now,digest
owner=OWNERS['simple'];assert owner=='01a0a867-d7aa-71f2-8547-e264d6d09ede'
claim=o/'simple-handoff-claim.json'
if claim.exists():print('Existing claim preserved; no repeated handoff.');raise SystemExit(0)
message=('DASHBOARD-ATTEMPTED-CATALOG-20260916 工程交接（非人类回答）：http://127.0.0.1:8765/ 已从现有 campaign_audit 自动接纳有实际动作证据的SIMPLE任务，原6项ID/顺序/链接保留，随后显示新垃圾桶/椅子/XMoveBendPick及后续实际任务。只允许R019规范直接子目录、合法注册task及同目录动作/result证据；动态task复用原媒体和case_media同回合门槛，无任意注册/目录暴露。后续继续更新原清单和public-progress即可，无需为每个任务改UI。NT以nt-audit-integration正式发布回执优先，发布、门19新合同加载、physical_network_recovery_verified三项独立显示；63离线测试不等于真实恢复收益，权限正式动作验证单列，共享core未晋升。请在自然边界ACK本次工程交接；不截断推理、不制造断线、不重放动作、不为网页启动模型/物理/API实验。UI仍由01a0a980唯一发布，原owner映射与回答保留，不重投历史消息。文档：/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/OWNER_INTERFACE.md；交付回执目录attempted-catalog。')
argv=[str(r/'codex-account-2/run.sh'),'queue','-m','gpt-6-astra','-c','model_provider="openai"','-c','model_reasoning_effort="xhigh"','--thread',owner,'--message',message]
immutable(claim,{'at':now(),'owner':owner,'message':message,'message_sha256':digest(message.encode()),'argv':argv})
try:
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
 receipt={'at':now(),'owner':owner,'queued':p.returncode==0 and b'Queued' in p.stdout and b'usageLimitExceeded' not in p.stdout,'returncode':p.returncode,'output':p.stdout.decode(errors='replace'),'owner_ack':False,'physical_verified':False,'engineering_only':True}
except subprocess.TimeoutExpired:receipt={'at':now(),'owner':owner,'queued':False,'uncertain':True,'no_retry':True}
except OSError:receipt={'at':now(),'owner':owner,'queued':False,'launcher_unavailable':True,'no_retry':True}
immutable(o/'simple-handoff-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
