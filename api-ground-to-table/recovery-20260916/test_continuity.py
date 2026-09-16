import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
ROOT=Path('/home/galbot/lizekai/RSI')
sys.path.insert(0,str(ROOT/'api-ground-to-table/actor-adapter'))
import actor
from history_bound import PublicHistory

class ContinuityTests(unittest.TestCase):
    def test_completed_no_tool_preserves_same_observation_and_replans(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            p=Path(d)/'obs.json';p.write_text(json.dumps({'observation_id':'same-17','sim_s':42,'images':[]}))
            host=NS(harness=NS(latest_path=p),finished=False,backend=NS(active=False))
            gate=NS(host=host,content=lambda x:[{'type':'input_text','text':json.dumps(x)}])
            h=PublicHistory('original skill',{'goal':'carry place'},[])
            for i in range(5):
                response={'status':'completed','output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'Replan safely.'}]}]}
                self.assertTrue(actor.continue_completed_turn(response,h,gate,{'path':'public-output','sha256':'f'*64}))
            self.assertIs(host.harness.latest_path,p)
            self.assertFalse(host.finished)
            packed=json.dumps(h.payload({},2_000_000))
            self.assertIn('same-17',packed);self.assertIn('original skill',packed)
            self.assertNotIn('function_call_output',packed)
    def test_incomplete_unknown_and_active_never_continue(self):
        for status in ('incomplete','failed','in_progress',None):
            with self.assertRaises(ValueError):actor.continue_completed_turn({'status':status,'output':[]},None,None,{})
    def test_tool_response_uses_normal_dispatch(self):
        self.assertFalse(actor.continue_completed_turn({'status':'completed','output':[{'type':'function_call'}]},None,None,{}))

if __name__=='__main__':unittest.main(verbosity=2)
