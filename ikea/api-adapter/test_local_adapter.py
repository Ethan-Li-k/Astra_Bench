"""Offline behavior checks; no credentials, production ledger or network access."""
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from transport_gate import Gate,ResponsesSession,MODEL,EFFORT,physical_preflight

ROOT=Path(__file__).resolve().parent/'test-evidence'/str(time.time_ns());ROOT.mkdir(parents=True)
def decision():return dict(observations='Visible panel',hypothesis='Reposition hand',evidence='Current RGB',
    uncertainty='Contact not yet established',expected='Visible motion',next_test='Small bounded motion')

class FakeHost:
    def __init__(self,root):
        self.rollout_root=root;root.mkdir()
        p=root/'obs.json';p.write_text('{"images":[],"robot_state":"fresh"}')
        self.native='in_progress';self.actions=3;self.finished=False;self.execution_error=None
        self.initialization_error=None;self.stop_reason=None
        self.backend=SimpleNamespace(active=None,reason=None,continuous_chunks_enabled=True,
            physics_substeps=5,model=SimpleNamespace(opt=SimpleNamespace(timestep=.004)),data=SimpleNamespace(time=5.))
        self.harness=SimpleNamespace(latest_path=p,evaluator=SimpleNamespace(outcome=lambda b:self.native))
        self.episode_start_sim_s=5.;self.max_episode_steps=12000;self.calls=[]
    def tool_specs(self):
        return [dict(name='experience_select',description='Select sources',inputSchema=dict(type='object',
            properties=dict(selected_ids={},rationale={},adaptation={},not_reused={}),
            required=['selected_ids','rationale','adaptation','not_reused']))]
    def dispatch(self,name,args):self.calls.append((name,args));return {'selected':True}
    def next_call(self):return dict(tool='scalebfm_act')

class Check(unittest.TestCase):
    def test_safe_stall_does_not_end_episode(self):
        h=FakeHost(ROOT/'stall');g=Gate(h)
        result=g.dispatch('conclude',dict(reason='At door but not pushing',next_hypothesis='Reposition hand',
            revised_skill='',lesson='Need visible progress',public_decision=decision()))
        self.assertFalse(result['rollout_finished']);self.assertFalse(g.concluded);self.assertFalse(h.finished)
        self.assertEqual(h.actions,3)
    def test_selection_and_public_read_cannot_escape(self):
        h=FakeHost(ROOT/'public');g=Gate(h)
        g.dispatch('experience_select',dict(selected_ids=['s1'],rationale='Same controller',adaptation='New geometry',
            not_reused='Coordinates',public_decision=decision()))
        self.assertNotIn('observation_path',h.calls[0][1]);self.assertNotIn('output_dir',h.calls[0][1])
        p=h.rollout_root/'public.md';p.write_text('Public conditional evidence')
        g.register({'path':str(p)});self.assertIn('text',g.read_public(str(p)))
        with self.assertRaises(ValueError):g.read_public(str(ROOT/'private.json'))
    def test_physical_guard_counts_240s_and_wait(self):
        h=FakeHost(ROOT/'timing');r=physical_preflight(h,{'trajectory':[{'duration_s':1.},{'duration_s':1.}]})
        self.assertEqual(r['max_episode_steps'],12000);self.assertTrue(r['accepted'])
        h.backend.data.time=244.;self.assertFalse(physical_preflight(h,{'trajectory':[{'duration_s':1.}]})['accepted'])
    def test_reserve_precedes_send_unknown_holds_retained_no_retry(self):
        events=[]
        class Budget:
            def reserve(self,m):events.append('reserve');return {'id':'synthetic'}
            def settle(self,r,receipt):events.append('settle');self.receipt=receipt
        b=Budget()
        def send(payload):events.append('send');raise ConnectionError('synthetic ambiguous failure')
        s=ResponsesSession(ROOT/'responses',b,send,'api-ikea-door-001',max_calls=120)
        payload=dict(model=MODEL,reasoning={'effort':EFFORT},store=False,stream=True,max_output_tokens=100)
        with self.assertRaises(ConnectionError):s.call(payload)
        self.assertEqual(events,['reserve','send','settle']);self.assertEqual(b.receipt['state'],'unknown_no_retry')
        with self.assertRaises(ValueError):s.call(payload)
        self.assertEqual(events,['reserve','send','settle'])
    def test_no_send_if_budget_rejects(self):
        class Budget:
            def reserve(self,m):raise ValueError('Synthetic refused reservation')
        calls=[];s=ResponsesSession(ROOT/'rejected',Budget(),lambda p:calls.append(p),'api-ikea-door-001',max_calls=120)
        with self.assertRaises(ValueError):s.call(dict(model=MODEL,reasoning={'effort':EFFORT},store=False,stream=True,max_output_tokens=100))
        self.assertEqual(calls,[])

if __name__=='__main__':unittest.main()
