"""New ID/once-only/unknown holds tested in a synthetic ledger only."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))
import actor
import recovery_budget005 as h
from test_actor import payload,response
from stream_evidence import StreamEvidenceError

class Batch005Tests(unittest.TestCase):
    def test_old_adapter_rejects005_and_new_auth_is_distinct(self):
        p=OUT/'episode005-preparation/before-code/actor.py'
        spec=importlib.util.spec_from_file_location('before005',p);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        with tempfile.TemporaryDirectory(dir=OUT) as t:
            with self.assertRaises(ValueError):old.ResponsesSession(Path(t)/'old',None,None,'api-ground-005',max_calls=120)
        auth,n,skill=actor.validate_authorization(actor.ROOT/'authorization-005.json','api-ground-005','episode-0005',h)
        self.assertEqual(auth['batch'],h.BATCH_REF);self.assertEqual(n,120)
        for path,ep in [(actor.ROOT/'authorization-004.json','episode-0005'),(actor.ROOT/'authorization-005.json','episode-0004')]:
            with self.assertRaises(ValueError):actor.validate_authorization(path,'api-ground-005',ep,h)
        text=skill.read_text()+'\n'+actor.INSTRUCTIONS
        self.assertLessEqual(len(text),6250);self.assertLessEqual(len(text.split()),831);self.assertLessEqual(len(''.join(text.split())),5357)

    def test_real_reserve_dispatch_and_unknown_no_retry(self):
        production=ROOT/'artifacts/R020/shared-budget-ledger.json'
        original=production.read_bytes();state=json.loads(original);state['data_kind']='synthetic_offline_test'
        with tempfile.TemporaryDirectory(dir=h.BATCH.parent) as t:
            p=Path(t);ledger=p/'ledger.json';ledger.write_text(json.dumps(state));(p/'batch.json').write_bytes(h.BATCH.read_bytes())
            sent=[]
            def fake(payload):
                sent.append(1)
                if len(sent)==2:raise StreamEvidenceError('missing_terminal_response',{'http_status':200,'terminal_event_seen':False})
                r=response();r['_transport']={'http_status':200,'provider_request_id':None};return r
            factory=lambda:h.RecoveryLedger(ledger)
            atomic=h.budget.atomic_write
            def checked_write(path,*args,**kwargs):
                self.assertIn(p,Path(path).resolve().parents,'Test attempted to write outside its synthetic directory')
                return atomic(path,*args,**kwargs)
            with patch.object(h.budget,'BudgetLedger',factory),patch.dict(h.base.REGISTERED,{'api-ground-005':p}),patch.object(h.budget,'atomic_write',checked_write):
                session=actor.ResponsesSession(p/'calls',h,fake,'api-ground-005',max_calls=120)
                session.call(payload())
                plan=json.loads((p/'api-ground-005-call-01-plan.json').read_text())
                self.assertFalse(factory().begin_empirical('api-ground-005-call-01',plan['payload_sha256'])['transitioned'])
                with self.assertRaises(StreamEvidenceError):session.call(payload())
                with self.assertRaises(ValueError):session.call(payload())
                self.assertEqual(len(sent),2)
                self.assertEqual(session.count,2);self.assertEqual(session.completed_count,1)
                d=json.loads(ledger.read_text())
                for k,v in state['requests'].items():self.assertEqual(d['requests'][k],v)
                for key in ('api-ground-002-call-55','api-ground-004-call-43','api-ground-005-call-02'):
                    self.assertEqual(d['requests'][key]['state'],'inflight');self.assertGreater(d['requests'][key]['reserved_fen'],0)
                receipt=json.loads((p/'calls/02/receipt.json').read_text());self.assertEqual(receipt['state'],'unknown_no_retry')
                self.assertEqual(receipt['transport_evidence']['http_status'],200)
                with self.assertRaises(h.budget.BudgetError):factory().begin_empirical('api-ground-005-call-01',plan['payload_sha256'])
                corrupt=copy.deepcopy(d);corrupt['requests']['api-ground-004-call-43']['reserved_fen']=0;ledger.write_text(json.dumps(corrupt))
                with self.assertRaises(h.budget.BudgetError):
                    with factory().transaction():pass
                corrupt=copy.deepcopy(d);corrupt['requests']['foreign-unknown']=dict(d['requests']['api-ground-005-call-02'],batch=None);ledger.write_text(json.dumps(corrupt))
                with self.assertRaises(h.budget.BudgetError):
                    with factory().transaction():pass
        # Other authorized branches continue appending to production concurrently.
        actual=json.loads(production.read_text())
        for k,v in state['requests'].items():
            if k.startswith('api-ground-'):self.assertEqual(actual['requests'][k],v)

if __name__=='__main__':unittest.main(verbosity=2)
