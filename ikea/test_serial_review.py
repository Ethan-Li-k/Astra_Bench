"""Negative controls for serial receipt review; entirely synthetic evidence."""
import copy
import unittest
from review_serial_api_evidence import check_series

def fixture():
    series=[dict(global_call=n,run_id=run,batch_call=local)
        for n,(run,local) in enumerate([('a',1),('a',2),('b',1)],1)]
    receipts=[dict(run_id=x['run_id'],call_index=x['batch_call'],state='completed',
        http_status=200,returned_model='gpt-6-astra',returned_reasoning={'effort':'xhigh'},
        finished_at_unix=10.) for x in series]
    transitions=[dict(previous_run='a',new_run='b',previous_call=2,same_reset=True,
        physics_advanced=False,request_sent=False,old_unknown_fees_retained=True)]
    return [series,receipts,['a','b'],{'a':{'max_calls':2},'b':{'max_calls':2}},transitions]

class ReviewChecks(unittest.TestCase):
    def test_valid(self):self.assertTrue(all(check_series(*fixture()).values()))
    def test_reused_global_id(self):
        f=fixture();f[0][-1]['global_call']=1
        self.assertFalse(check_series(*f)['serial_global_index'])
    def test_unknown_previous_response(self):
        f=fixture();f[1][1]['state']='unknown_no_retry'
        self.assertFalse(check_series(*f)['complete_model_calls'])
    def test_early_batch_bypass(self):
        f=fixture();f[3]['a']['max_calls']=120
        self.assertFalse(check_series(*f)['exact_batch_allowances'])
    def test_reset_discontinuity(self):
        f=fixture();f[4][0]['same_reset']=False
        self.assertFalse(check_series(*f)['verified_same_reset_transitions'])
    def test_return_to_old_batch(self):
        f=fixture();f[0].append(dict(global_call=4,run_id='a',batch_call=3))
        f[1].append(dict(f[1][0],call_index=3))
        self.assertFalse(check_series(*f)['serial_global_index'])

if __name__=='__main__':unittest.main()
