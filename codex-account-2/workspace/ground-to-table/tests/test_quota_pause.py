import unittest
from rsi.skill_learning import usage_exhausted

class QuotaPauseTests(unittest.TestCase):
    def test_common_quota_error_spellings_stop_retries(self):
        for error in ('usageLimitExceeded','UsageLimitExceeded','usage_limit_exceeded',
                      "You've hit your usage limit"):
            self.assertTrue(usage_exhausted({'error':error}))

    def test_network_error_or_nonerror_text_is_not_quota(self):
        self.assertFalse(usage_exhausted({'error':'Network timeout'}))
        self.assertFalse(usage_exhausted({'error':None,'note':'usageLimitExceeded'}))

if __name__=='__main__':unittest.main()
