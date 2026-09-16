"""Offline completion controls; synthetic records never count as physics."""
import unittest
import review_subscription_fridge_v1 as reviewer


def fixture():
    return [dict(model='gpt-6-astra',effort='xhigh',launcher=str(reviewer.ROOT.parent/'codex-account-2/run.sh'),
        inference_deadline=None,thread='synthetic-thread'),
        [dict(id='turn-1',status='completed'),dict(id='turn-2',status='completed')],2]


class ReviewChecks(unittest.TestCase):
    def test_complete_turns(self):self.assertTrue(all(reviewer.subscription_turn_audit(*fixture()).values()))
    def test_failed_turn_is_not_complete(self):
        f=fixture();f[1][-1]['status']='failed'
        self.assertFalse(reviewer.subscription_turn_audit(*f)['real_completed_turns'])
    def test_main_account_or_deadline_rejected(self):
        f=fixture();f[0].update(launcher='codex',inference_deadline=900)
        r=reviewer.subscription_turn_audit(*f)
        self.assertFalse(r['second_account_launcher']);self.assertFalse(r['no_inference_deadline'])
    def test_duplicate_or_missing_completion(self):
        f=fixture();f[1][-1]['id']='turn-1';self.assertFalse(reviewer.subscription_turn_audit(*f)['unique_turns'])
        f=fixture();f[-1]=3;self.assertFalse(reviewer.subscription_turn_audit(*f)['all_turns_accounted'])
    def test_diagnostic_not_policy_evidence(self):
        with self.assertRaisesRegex(ValueError,'refrigerator campaign'):
            reviewer.review(reviewer.ROOT/'diagnostics/fridge-evaluator-contact-001')
    def test_no_sealed_result_no_review(self):
        self.assertFalse((reviewer.ROOT/'campaign/fridge-0001/result.json').exists())
        with self.assertRaisesRegex(ValueError,'No sealed result'):
            reviewer.review(reviewer.ROOT/'campaign/fridge-0001')


if __name__=='__main__':unittest.main()
