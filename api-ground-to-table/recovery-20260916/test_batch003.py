"""Real actor/hook, synthetic ledger and fake transport. No credentials/network."""
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
import recovery_budget as hook

class Batch003Tests(unittest.TestCase):
    def test_authorization_is_new_and_hash_pinned(self):
        path=actor.ROOT/'authorization-003.json'
        a,count,skill=actor.validate_authorization(path,'api-ground-003','episode-0003',hook)
        self.assertEqual(count,120);self.assertEqual(a['batch'],hook.BATCH_REF)
        text=skill.read_text()+'\n'+actor.INSTRUCTIONS
        self.assertLessEqual(len(text),6250);self.assertLessEqual(len(text.split()),831)
        self.assertLessEqual(len(''.join(text.split())),5357)
        for path2,ep in [(actor.ROOT/'authorization-002.json','episode-0003'),(path,'episode-0002')]:
            with self.assertRaises(ValueError):actor.validate_authorization(path2,'api-ground-003',ep,hook)

    def test_real_reserve_begin_settle_keep_old_holds_and_no_repeat(self):
        prod=ROOT/'artifacts/R020/shared-budget-ledger.json'
        before=hashlib.sha256(prod.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R021/api-ground-003') as temp:
            p=Path(temp);ledger=p/'ledger.json'
            state=copy.deepcopy(hook.SNAPSHOT);state['data_kind']='synthetic_offline_test'
            ledger.write_text(json.dumps(state))
            (p/'batch.json').write_bytes(hook.BATCH.read_bytes())
            sent=[]
            def fake(payload):
                sent.append(True);r=response();r['_transport']={'http_status':200,'provider_request_id':None};return r
            factory=lambda:hook.RecoveryLedger(ledger)
            with patch.object(hook.budget,'BudgetLedger',factory),patch.dict(hook.base.REGISTERED,{'api-ground-003':p}):
                session=actor.ResponsesSession(p/'calls',hook,fake,'api-ground-003',max_calls=120)
                session.call(payload());session.call(payload())
                d=json.loads(ledger.read_text())
                for key,row in hook.SNAPSHOT['requests'].items():self.assertEqual(d['requests'][key],row)
                self.assertEqual(len(sent),2)
                row=d['requests']['api-ground-003-call-02']
                plan=json.loads((p/'api-ground-003-call-02-plan.json').read_text())
                begun=factory().begin_empirical(row['request_id'],plan['payload_sha256'])
                self.assertFalse(begun['transitioned'])
                d['requests']['foreign-unknown']=dict(row,request_id='foreign-unknown',batch=None)
                ledger.write_text(json.dumps(d))
                with self.assertRaises(hook.budget.BudgetError):session.call(payload())
                self.assertEqual(len(sent),2)
        self.assertEqual(before,hashlib.sha256(prod.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main(verbosity=2)
