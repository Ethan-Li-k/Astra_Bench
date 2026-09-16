"""Read this episode's public progress only; no process control, API or inference."""
import json
from pathlib import Path
import time

ROOT=Path('/home/galbot/lizekai/RSI')
OUT=Path(__file__).resolve().parent
ACTOR=ROOT/'api-ground-to-table/actor-adapter'
EP=ACTOR/'campaign/episode-0002'

def read(path): return json.loads(path.read_text())

progress=read(ACTOR/'auxiliary-progress.json')
receipts=[read(path) for path in sorted(EP.glob('api_calls/*/receipt.json'))]
latest=receipts[-1] if receipts else {}
record={'updated_at_unix':time.time(),'progress':progress,
    'completed_calls':sum(r['state']=='completed' for r in receipts),
    'latest_request':{k:latest.get(k) for k in ('call_index','state','http_status','input_bytes')},
    'result_exists':(EP/'result.json').exists(),
    'exit_code':(ACTOR/'run-002.exit-code').read_text().strip() if (ACTOR/'run-002.exit-code').exists() else None}
record['monitor_stage'] = ('ended' if record['result_exists'] else
    'tool_execution_or_postprocessing' if latest.get('state') == 'completed'
    and latest.get('call_index',0) > progress.get('api_calls_completed',0) else
    'inference_waiting_no_deadline')
if record['result_exists']:
    result=read(EP/'result.json')
    record['result']={k:result.get(k) for k in ('terminal_kind','native_outcome','stop_reason',
        'actions','api_calls','overall_success','backend_stop_reason','error_type')}
else:
    paths=sorted((EP/'rollout').glob('public_decision_*.json'))
    if paths:
        row=read(paths[-1])
        record['latest_public_decision']={'path':str(paths[-1]),'tool':row['tool'],
            **{k:row['public_decision'][k] for k in ('observations','hypothesis','next_test')}}
temporary=OUT/'auxiliary-progress.next.json'
temporary.write_text(json.dumps(record,indent=2,ensure_ascii=False))
temporary.replace(OUT/'auxiliary-progress.json')
print(json.dumps(record,ensure_ascii=False))
