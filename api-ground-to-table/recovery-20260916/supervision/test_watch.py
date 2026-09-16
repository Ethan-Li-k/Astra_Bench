import json
from pathlib import Path
import tempfile
import unittest
import watch

class WatchTests(unittest.TestCase):
    def setUp(self):
        self.o=dict(boot_id='boot',thread=watch.THREAD,log='log',started_ns=10)
        self.s=dict(status='continue',owner_log='log',written_ns=11,episode='episode-0004')
        self.e=dict(complete=True,failure=None,thread=watch.THREAD)
    def d(self,**kw):
        args=dict(origin=self.o,state=self.s,event=self.e,owner_alive=False,actor_alive=False,used=set(),boot='boot');args.update(kw)
        return watch.decision(**args)
    def test_both_natural_boundaries_required(self):
        self.assertEqual(self.d(owner_alive=True),'waiting_owner_natural_exit')
        self.assertEqual(self.d(actor_alive=True),'waiting_actor_natural_exit')
        self.assertEqual(self.d(),'resume')
    def test_incomplete_quota_or_wrong_owner_never_resume(self):
        for e in [dict(self.e,complete=False),dict(self.e,failure='error'),dict(self.e,thread='other')]:
            self.assertTrue(self.d(event=e).startswith('blocked'))
    def test_stale_disposition_and_repeated_episode_block(self):
        for s in [None,dict(self.s,written_ns=9),dict(self.s,owner_log='old'),dict(self.s,status='blocked')]:
            self.assertTrue(self.d(state=s).startswith('blocked'))
        self.assertEqual(self.d(used={'episode-0004'}),'blocked_repeated_boundary')
    def test_other_boot_rejected(self):self.assertEqual(self.d(boot='other'),'blocked_identity')
    def test_actual_events_not_quoted_errors(self):
        with tempfile.TemporaryDirectory(dir=watch.OUT) as d:
            p=Path(d)/'log';rows=[dict(type='thread.started',thread_id=watch.THREAD),dict(type='turn.started'),
                dict(type='item.completed',text='old usageLimitExceeded turn.failed'),dict(type='turn.completed')]
            p.write_text('\n'.join(map(json.dumps,rows)));self.assertEqual(watch.event_status(p),self.e)
            with p.open('a') as f:f.write('\n'+json.dumps(dict(type='turn.started')))
            self.assertFalse(watch.event_status(p)['complete'])

if __name__=='__main__':unittest.main(verbosity=2)
