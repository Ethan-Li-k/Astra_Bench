"""Offline fixtures: no real registration, ledger, model or simulation."""
import json
from pathlib import Path
from types import SimpleNamespace as NS
import time
import unittest
from serial_batch_continuation import SerialBatchContinuation

ROOT=Path(__file__).resolve().parent/'engineering-evidence/serial-batch-tests'/str(time.time_ns())


class BridgeTests(unittest.TestCase):
    def fixture(self,name,*,state='completed'):
        root=ROOT/name;folder=root/'old/02';folder.mkdir(parents=True)
        receipt=dict(state=state,finished_at_unix=1 if state=='completed' else None,
            returned_model='gpt-6-astra',returned_reasoning={'effort':'xhigh'},http_status=200,response_id='synthetic-response')
        (folder/'receipt.json').write_text(json.dumps(receipt))
        old=NS(output=root/'old',run_id='synthetic-old',count=2,max_calls=2,stopped=False)
        host=NS(execution_error=None,initialization_error=None,finished=False,
            backend=NS(active=None,data=NS(time=15.)),harness=object(),actions=4,episode_id='synthetic-episode')
        calls=[]
        def factory(evidence):
            calls.append(evidence)
            return NS(output=root/'new',run_id='synthetic-new',count=0,max_calls=2,stopped=False)
        return old,host,calls,SerialBatchContinuation(old,host,factory,root/'transitions.jsonl')

    def test_completed_boundary_preserves_host_and_does_not_send(self):
        old,h,c,b=self.fixture('valid');identity=id(h.backend)
        new=b.ready();self.assertEqual(new.run_id,'synthetic-new');self.assertEqual(len(c),1)
        self.assertEqual(id(h.backend),identity);self.assertEqual(h.backend.data.time,15.)
        self.assertEqual(h.actions,4);self.assertIs(b.ready(),new);self.assertEqual(len(c),1)

    def test_unexhausted_session_is_reused(self):
        old,h,c,b=self.fixture('reuse');old.count=1
        self.assertIs(b.ready(),old);self.assertEqual(c,[])

    def test_unknown_response_cannot_advance_or_retry(self):
        old,h,c,b=self.fixture('unknown',state='unknown_no_retry')
        for _ in range(2):
            with self.assertRaises(RuntimeError):b.ready()
        self.assertEqual(c,[])

    def test_inflight_physical_action_forbids_transition(self):
        old,h,c,b=self.fixture('active');h.backend.active=object()
        with self.assertRaises(RuntimeError):b.ready()
        self.assertEqual(c,[])

    def test_registration_refusal_is_not_retried(self):
        old,h,c,b=self.fixture('refuse')
        def refusal(e):c.append(e);raise ValueError('Synthetic shared budget refusal')
        b.replacement_factory=refusal
        with self.assertRaises(ValueError):b.ready()
        with self.assertRaises(RuntimeError):b.ready()
        self.assertEqual(len(c),1);self.assertIs(b.session,old)

    def test_duplicate_run_rejected(self):
        old,h,c,b=self.fixture('duplicate');b.replacement_factory=lambda e:NS(run_id=old.run_id,count=0,stopped=False)
        with self.assertRaises(RuntimeError):b.ready()

    def test_unexpected_reset_rejected(self):
        old,h,c,b=self.fixture('changed')
        def changed(e):
            h.backend=NS(active=None,data=NS(time=0.))
            return NS(run_id='synthetic-new',count=0,stopped=False,max_calls=2)
        b.replacement_factory=changed
        with self.assertRaisesRegex(RuntimeError,'physical state'):b.ready()

    def test_explicit_terminal_review_can_continue_without_new_physics(self):
        old,h,c,b=self.fixture('terminal');h.finished=True
        new=b.ready(phase='terminal_review')
        self.assertEqual(new.count,0);self.assertTrue(h.finished)
        self.assertEqual(c[0]['allowed_terminal_tool'],'conclude');self.assertEqual(h.actions,4)

    def test_reasoning_metadata_may_include_other_provider_fields(self):
        old,h,c,b=self.fixture('metadata');p=old.output/'02/receipt.json'
        receipt=json.loads(p.read_text());receipt['returned_reasoning']['summary']=None;p.write_text(json.dumps(receipt))
        self.assertEqual(b.ready().run_id,'synthetic-new')


if __name__=='__main__':unittest.main()
