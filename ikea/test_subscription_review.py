"""Subscription terminal evidence controls; no model or simulation calls."""
import unittest
from review_subscription_apple_v2 import subscription_turn_audit, ROOT

def fixture():
    return [dict(model='gpt-6-astra',effort='xhigh',launcher=str(ROOT.parent/'codex-account-2/run.sh'),
        inference_deadline=None,thread='synthetic-thread'),
        [dict(id='turn-1',status='completed'),dict(id='turn-2',status='completed')],2]

class ReviewChecks(unittest.TestCase):
    def test_complete_turns(self):self.assertTrue(all(subscription_turn_audit(*fixture()).values()))
    def test_usage_or_system_failed_turn_is_not_complete(self):
        f=fixture();f[1][-1]['status']='failed'
        self.assertFalse(subscription_turn_audit(*f)['real_completed_turns'])
    def test_main_account_or_timeout_rejected(self):
        f=fixture();f[0].update(launcher='codex',inference_deadline=900)
        r=subscription_turn_audit(*f);self.assertFalse(r['second_account_launcher']);self.assertFalse(r['no_inference_deadline'])
    def test_duplicate_or_missing_completion(self):
        f=fixture();f[1][-1]['id']='turn-1';self.assertFalse(subscription_turn_audit(*f)['unique_turns'])
        f=fixture();f[-1]=3;self.assertFalse(subscription_turn_audit(*f)['all_turns_accounted'])

if __name__=='__main__':unittest.main()
