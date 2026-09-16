"""Isolated real-ledger transitions; fake transport, no credential/API access."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))
import actor
from test_actor import payload,response

class Batch004Tests(unittest.TestCase):
    def test_new_run_requires_explicit_registration(self):
        # Before implementation this reproduces the absent fresh-run support.
        with tempfile.TemporaryDirectory(dir=OUT) as t:
            s=actor.ResponsesSession(Path(t)/'calls',None,lambda _:None,'api-ground-004',max_calls=120)
            self.assertEqual(s.run_id,'api-ground-004')

    def test_auth_and_real_ledger_keep_003_and_old_unknown(self):
        import recovery_budget004 as h
        path=actor.ROOT/'authorization-004.json'
        auth,n,skill=actor.validate_authorization(path,'api-ground-004','episode-0004',h)
        self.assertEqual(n,120);self.assertEqual(auth['batch'],h.BATCH_REF)
        for wrong,ep in [(actor.ROOT/'authorization-003.json','episode-0004'),(path,'episode-0003')]:
            with self.assertRaises(ValueError):actor.validate_authorization(wrong,'api-ground-004',ep,h)
        prod=ROOT/'artifacts/R020/shared-budget-ledger.json'
        original=prod.read_bytes();state=json.loads(original);state['data_kind']='synthetic_offline_test'
        # Production snapshot is read-only; all mutations occur in this synthetic copy.
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R021/api-ground-004') as t:
            p=Path(t);ledger=p/'ledger.json';ledger.write_text(json.dumps(state))
            (p/'batch.json').write_bytes(h.BATCH.read_bytes());sent=[]
            def fake(payload):
                sent.append(1);r=response();r['_transport']={'http_status':200,'provider_request_id':None};return r
            factory=lambda:h.RecoveryLedger(ledger)
            with patch.object(h.budget,'BudgetLedger',factory),patch.dict(h.base.REGISTERED,{'api-ground-004':p}):
                session=actor.ResponsesSession(p/'calls',h,fake,'api-ground-004',max_calls=120)
                session.call(payload());session.call(payload())
                d=json.loads(ledger.read_text())
                for k,v in state['requests'].items():self.assertEqual(d['requests'][k],v)
                self.assertEqual(d['requests']['api-ground-002-call-55']['state'],'inflight')
                row=d['requests']['api-ground-004-call-02']
                plan=json.loads((p/'api-ground-004-call-02-plan.json').read_text())
                self.assertFalse(factory().begin_empirical(row['request_id'],plan['payload_sha256'])['transitioned'])
                d['requests']['foreign-unknown']=dict(row,request_id='foreign-unknown',batch=None)
                ledger.write_text(json.dumps(d))
                with self.assertRaises(h.budget.BudgetError):session.call(payload())
                self.assertEqual(len(sent),2)
        self.assertEqual(hashlib.sha256(original).hexdigest(),hashlib.sha256(prod.read_bytes()).hexdigest())
        text=skill.read_text()+'\n'+actor.INSTRUCTIONS
        self.assertLessEqual(len(text.split()),831);self.assertLessEqual(len(text),6250)
        self.assertLessEqual(len(''.join(text.split())),5357)

if __name__=='__main__':unittest.main(verbosity=2)
