from pathlib import Path
import json, datetime
from rsi.codex_app_server import CodexPolicyAdapter
from rsi.stdio_transport import StdioAppServer
r=Path('/home/galbot/lizekai/RSI');out=r/'artifacts/R019/recovery-20260916/permission-handshake';out.mkdir()
class Host:
    method='direct'
transport=StdioAppServer([str(r/'codex-account-2/run.sh'),'app-server','--stdio'],out/'app_server')
try:
    adapter=CodexPolicyAdapter(transport,Host(),out/'agent',developer_instructions='Permission handshake only; no model turn will be started.')
    reply=adapter.connect()
    summary={k:reply[k] for k in ['model','reasoningEffort','approvalPolicy','approvalsReviewer','sandbox','runtimeWorkspaceRoots']}
    summary.update(model_turns_started=0,physics_actions=0,verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='app-server thread creation only, no inference request')
    (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
finally:
    transport.close()
