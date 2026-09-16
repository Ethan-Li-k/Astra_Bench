"""Import the explicitly authorized, user-confirmed historical calibration cost.

No pricing is invented and no pre-dispatch reservation is fabricated. Keep the
ledger halted for an empirical reservation adapter before future paid requests.
"""
import json
from pathlib import Path
import sys

ROOT=Path('/home/galbot/lizekai/RSI')
sys.path.insert(0,str(ROOT))
from tools.coordination.shared_budget import BudgetLedger,now,sha,fingerprint,totals

receipt_path=ROOT/'artifacts/R021/api-calibration-001/user-billing-confirmation.json'
receipt=json.loads(receipt_path.read_text())
api=json.loads((ROOT/'api-ground-to-table/api/calibration-001/receipt.json').read_text())
assert api['state']=='response.completed' and api['request_id']==receipt['request_id']
assert receipt['actual_cny_fen']==339 and receipt['final'] is True
ref={'path':str(receipt_path.relative_to(ROOT)),'sha256':sha(receipt_path)}
binding={'receipt':ref,'content_sha256':fingerprint(receipt)}
book=BudgetLedger()
with book.transaction() as (state,policy):
    key=receipt['request_id']
    if key in state['requests']:
        row=state['requests'][key]
        assert row['state']=='settled' and row['actual_fen']==339
        assert row['billing_event_id']==receipt['billing_event_id']
        changed=False
    else:
        assert not any(r.get('billing_event_id')==receipt['billing_event_id'] for r in state['requests'].values())
        prior,held=totals(state)
        state['requests'][key]={
            'request_id':key,'inputs':{'scope':{'role':'reviewer','environment':'local','branch':'api-ground-to-table'},'maxima':{'output_tokens':16384}},
            'reserved_fen':0,'state':'settled','actual_fen':339,
            'settlement':binding,'billing_event_id':receipt['billing_event_id'],
            'created_at':api['started_at'],'settled_at':now(),
            'record_type':'post_hoc_user_authorized_external_calibration',
            'pre_dispatch_ledger_reservation':False,
            'pre_dispatch_exclusive_hold':'api-ground-to-table/api/calibration-hold.json',
            'pricing':None,'pricing_verified':False,
            'authorization_evidence':'api-ground-to-table/api/calibration-001/authorization.json'}
        state['halted']='historical_calibration_cost_recorded; empirical_reservation_adapter_pending'
        spent,held=totals(state)
        for threshold in state['terms']['thresholds_fen']:
            if prior < threshold <= spent:
                state['report_events'][str(threshold)]={'threshold_fen':threshold,'status':'pending',
                    'settled_fen_at_crossing':spent,'reserved_fen_at_crossing':held,
                    'remaining_uncommitted_fen_at_crossing':state['terms']['cap_fen']-spent-held,
                    'trigger_request':key,'created_at':now(),
                    'required_content':['cumulative_and_remaining_cost','task_progress','independent_success_counts','failure_findings']}
        changed=True
print(json.dumps({'changed':changed,**book.status()},ensure_ascii=False,indent=2))
