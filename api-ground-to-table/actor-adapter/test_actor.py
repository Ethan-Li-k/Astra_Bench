"""Offline boundary tests; no credentials, network, or simulation imports."""
import json
from pathlib import Path
import tempfile
import unittest

from actor import MAX_CALLS, Gate, ResponsesSession, public_response, validate_endpoint


class Host:
    def __init__(self, root):
        self.rollout_root = root
        self.finished = False
        self.actions = 0
        self.calls = []
        self.harness = type('Harness', (), {'latest_path': root/'observation.json'})()
    def tool_specs(self):
        return [{'name': 'scalebfm_act', 'description': 'act', 'inputSchema': {
            'type': 'object', 'properties': {'observation_path': {'type':'string'},
                'output_dir': {'type':'string'}, 'response': {'type':'object'}},
            'required': ['observation_path','output_dir','response'], 'additionalProperties':False}}]
    def dispatch(self, name, args):
        self.calls.append((name, args))
        self.actions += name == 'scalebfm_act'
        return {'observation_path': str(self.harness.latest_path), 'observation': {'images':[]}}


class Budget:
    def __init__(self, allow=True): self.allow, self.events = allow, []
    def reserve(self, meta):
        self.events.append(('reserve', meta))
        if not self.allow: raise ValueError('budget denied')
        return {'reservation_id': 'offline-test'}
    def settle(self, reservation, receipt): self.events.append(('settle', receipt))


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        self.host = Host(self.root)
        self.gate = Gate(self.host)
    def tearDown(self): self.temp.cleanup()
    def test_illegal_tools(self):
        for name in ('shell', 'exec', 'read_file', 'loco_start', 'pi05_infer', 'skill_update'):
            with self.assertRaises(ValueError): self.gate.dispatch(name, {})
        self.assertFalse(self.host.calls)
    def test_no_model_selected_paths(self):
        with self.assertRaises(ValueError):
            self.gate.dispatch('scalebfm_act', {'response':{}, 'output_dir':'/tmp/escape',
                'public_decision': decision()})
        self.assertFalse(self.host.calls)
    def test_read_must_be_issued_and_inside_rollout(self):
        target = self.root/'visible.json'; target.write_text('{"robot":1}')
        with self.assertRaises(ValueError): self.gate.read_public(str(target))
        self.gate.register({'observation_path': str(target)})
        self.assertEqual(self.gate.read_public(str(target)), {'robot':1})
        for value in ('/etc/passwd', str(self.root/'../secret.json')):
            with self.assertRaises(ValueError): self.gate.read_public(value)
        link = self.root/'link.json'; link.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError): self.gate.register({'observation_path':str(link)})
    def test_finite_arguments_and_summary_required(self):
        for args in ({'response':{}}, {'response':{'x':float('nan')},'public_decision':decision()}):
            with self.assertRaises(ValueError): self.gate.dispatch('scalebfm_act', args)
        self.assertFalse(self.host.calls)
    def test_endpoint_pinned(self):
        for value in ('http://llm-gateway.galbot.com','https://evil.example',
                      'https://llm-gateway.galbot.com:444',
                      'https://secret@llm-gateway.galbot.com',
                      'https://llm-gateway.galbot.com/v1?key=bad'):
            with self.assertRaises(ValueError): validate_endpoint(value)
        self.assertEqual(validate_endpoint('https://llm-gateway.galbot.com/v1'), '/v1/responses')
    def test_public_export_drops_reasoning(self):
        result=public_response({'id':'test','output':[
            {'type':'reasoning','summary':[{'text':'PRIVATE'}], 'encrypted_content':'SECRET'},
            {'type':'function_call','name':'scalebfm_act','arguments':'{}','call_id':'c'},
            {'type':'message','content':[{'type':'output_text','text':'public'}]}]})
        self.assertNotIn('PRIVATE', json.dumps(result)); self.assertNotIn('SECRET', json.dumps(result))
    def test_budget_denial_prevents_transport(self):
        sent=[]
        session=ResponsesSession(self.root/'calls', Budget(False), lambda p: sent.append(p), 'test')
        with self.assertRaises(ValueError): session.call(payload())
        self.assertFalse(sent)
        self.assertEqual(session.count,0)
    def test_six_calls_only_and_no_retries(self):
        budget=Budget(); sent=[]
        def send(p): sent.append(p); return response()
        session=ResponsesSession(self.root/'calls',budget,send,'test')
        for _ in range(MAX_CALLS): session.call(payload())
        with self.assertRaises(ValueError): session.call(payload())
        self.assertEqual(len(sent),6)
        self.assertEqual([e[0] for e in budget.events], ['reserve','settle']*6)
    def test_failure_settled_unknown_and_session_stops(self):
        budget=Budget(); sent=[]
        def send(p): sent.append(p); raise ConnectionError('test transport failure')
        session=ResponsesSession(self.root/'calls',budget,send,'test')
        with self.assertRaises(ConnectionError): session.call(payload())
        with self.assertRaises(ValueError): session.call(payload())
        self.assertEqual(len(sent),1)
        self.assertEqual(budget.events[-1][1]['state'],'unknown_no_retry')
        self.assertIsNone(budget.events[-1][1]['cost_cny'])
    def test_no_downgrade_or_store(self):
        for key,value in [('model','other'),('store',True),('max_output_tokens',999999)]:
            p=payload();p[key]=value
            session=ResponsesSession(self.root/key,Budget(),lambda _:response(),'test')
            with self.assertRaises(ValueError): session.call(p)
    def test_oversized_body_precedes_budget_and_transport(self):
        budget=Budget(); sent=[]
        session=ResponsesSession(self.root/'calls',budget,lambda p:sent.append(p),'test')
        p=payload();p['input']=[{'role':'user','content':'x'*2_000_001}]
        with self.assertRaises(ValueError): session.call(p)
        self.assertFalse(sent);self.assertFalse(budget.events)
    def test_motion_trace_is_bounded_with_indices(self):
        target=self.root/'proprioception.json'
        target.write_text(json.dumps({'samples':[{'sample':i} for i in range(151)]}))
        self.gate.register({'motion_evidence':{'proprioception_path':str(target)}})
        result=self.gate.read_public(str(target))
        self.assertEqual(len(result['samples']),20)
        self.assertEqual(result['total_samples'],151)
        self.assertEqual(result['returned_sample_indices'][0],0)
        self.assertEqual(result['returned_sample_indices'][-1],150)
    def test_skill_and_runtime_cap(self):
        from actor import INSTRUCTIONS
        skill=(Path(__file__).parent/'loco-manip-direct/SKILL.md').read_text()
        complete=skill+'\n'+INSTRUCTIONS
        self.assertLessEqual(len(complete),6250)
        self.assertLessEqual(len(complete.split()),831)
    def test_incomplete_and_safety_stop_are_not_physical_failure(self):
        from actor import terminal_kind
        self.assertEqual(terminal_kind('failure','diagnostic_stability_stop',False,True,3),'safety_stop')
        self.assertEqual(terminal_kind('in_progress',None,False,True,3),'agent_stopped_incomplete')
        self.assertEqual(terminal_kind('in_progress',None,False,False,6),'budget_limited_incomplete')
        self.assertEqual(terminal_kind('in_progress',None,True,False,2),'infrastructure_error')
    def test_physical_budget_with_completed_review_is_budget_not_agent_stop(self):
        from actor import terminal_kind
        self.assertEqual(terminal_kind('in_progress',None,False,True,4,
            stop_reason='episode_step_budget'),'budget_limited_incomplete')
    def test_host_paths_are_injected(self):
        self.gate.dispatch('scalebfm_act',{'response':{},'public_decision':decision()})
        args=self.host.calls[-1][1]
        self.assertEqual(args['observation_path'],str(self.host.harness.latest_path))
        self.assertTrue(Path(args['output_dir']).is_relative_to(self.root))


def decision():
    return dict(observations='visible',hypothesis='test',evidence='current RGB',
                uncertainty='unverified',expected='motion',next_test='reobserve')
def payload():
    return dict(model='gpt-6-astra',reasoning={'effort':'xhigh'},store=False,
                max_output_tokens=16384,stream=True,input=[])
def response():
    return dict(id='offline',status='completed',model='gpt-6-astra',
                reasoning={'effort':'xhigh'},usage={'input_tokens':1,'output_tokens':2},output=[])

if __name__ == '__main__': unittest.main()
