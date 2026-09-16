"""Exercise the future real caller loop with fake network/physics/registration only."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace as NS
import unittest

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'api-apple-v2'))
from transport_gate import ResponsesSession,MODEL,EFFORT
from history_bound import PublicHistory
from serial_actor_loop import SerialActorLoop
ROOT=BASE/'engineering-evidence/serial-loop-tests'/str(time.time_ns())

def save(path,data):Path(path).write_text(json.dumps(data))

class FakeBudget:
    def __init__(self,run):self.batch={'batch_id':run,'max_calls':2};self.events=[]
    def reserve(self,meta):self.events.append(('reserve',meta['call_index']));return meta
    def settle(self,reservation,receipt):self.events.append(('settle',receipt['state']))

class LoopTests(unittest.TestCase):
    def fixture(self,name,fail_at=None):
        root=ROOT/name;root.mkdir(parents=True);rollout=root/'rollout';rollout.mkdir()
        observation=rollout/'obs.json';save(observation,{'robot':'synthetic'})
        host=NS(episode_id='synthetic',backend=NS(active=None,data=NS(time=5.)),
            harness=NS(latest_path=observation),actions=0,execution_error=None,initialization_error=None,
            selection_recorded=True,finished=False,rollout_root=rollout,progress=lambda p:None,
            next_call=lambda:{'tool':'act'})
        calls=[];sessions=[];registrations=[]
        class Gate:
            concluded=False
            def specs(self):return []
            def register(self,v):pass
            def content(self,v):return [{'type':'input_text','text':json.dumps(v)}]
            def dispatch(self,name,args):
                if host.finished:
                    assert name=='conclude';self.concluded=True
                else:
                    assert name=='act';host.actions+=1;host.backend.data.time+=.02
                    host.finished=host.actions==4
                return {'observation_path':str(observation),'step_id':host.actions}
        gate=Gate()
        def send(payload):
            calls.append(payload)
            if len(calls)==fail_at:raise ConnectionError('Synthetic ambiguous transport')
            name='conclude' if host.finished else 'act'
            if host.finished:self.assertEqual(payload['tool_choice'],{'type':'function','name':'conclude'})
            return dict(status='completed',model=MODEL,reasoning={'effort':EFFORT},id=f'synthetic-{len(calls)}',
                _transport={'http_status':200},output=[dict(type='function_call',name=name,
                    call_id=f'call-{len(calls)}',arguments=json.dumps({'public_decision':{'evidence':'synthetic'}}))])
        def factory(previous=None):
            run=f'synthetic-b{len(sessions)+1}';registrations.append(previous)
            session=ResponsesSession(root/run,FakeBudget(run),send,run,max_calls=2);sessions.append(session)
            return session
        history=PublicHistory('synthetic contract',{'task':'synthetic'},gate.content({}),
            index_path=str(rollout/'public-history-index.json'))
        loop=SerialActorLoop(host,gate,history,factory(),factory,root,save,
            model=MODEL,effort=EFFORT,max_tokens=100,max_body=2_000_000)
        return host,gate,history,loop,calls,sessions,registrations

    def test_actual_loop_crosses_policy_and_terminal_boundaries(self):
        h,g,hist,loop,calls,sessions,regs=self.fixture('complete');identity=id(h.backend)
        self.assertEqual(loop.run(),5);self.assertTrue(g.concluded)
        self.assertEqual(h.actions,4);self.assertEqual(id(h.backend),identity)
        self.assertAlmostEqual(h.backend.data.time,5.08);self.assertEqual(len(hist.index),5)
        self.assertEqual([s.count for s in sessions],[2,2,1])
        self.assertEqual(regs[1]['phase'],'policy');self.assertEqual(regs[2]['phase'],'terminal_review')
        self.assertEqual(len(list(h.rollout_root.glob('public_tool_*.json'))),5)
        series=[json.loads(s) for s in (loop.output/'api-call-series.jsonl').read_text().splitlines()]
        self.assertEqual([x['global_call'] for x in series],[1,2,3,4,5])
        self.assertEqual([x['batch_call'] for x in series],[1,2,1,2,1])
        for row in series:self.assertEqual((loop.flat_calls/f"{row['global_call']:02d}").resolve(),Path(row['source']))
        self.assertTrue((h.rollout_root/'public-history-index.json').exists())

    def test_ambiguous_request_not_replayed_or_acted(self):
        h,g,hist,loop,calls,sessions,regs=self.fixture('unknown',fail_at=2)
        with self.assertRaises(ConnectionError):loop.run()
        self.assertEqual(h.actions,1);self.assertEqual(len(regs),1);self.assertEqual(len(calls),2)
        self.assertEqual(sessions[0].budget.events[-1],('settle','unknown_no_retry'))
        with self.assertRaises(RuntimeError):loop.run()
        self.assertEqual(len(calls),2)

    def test_history_over_120_preserved_and_byte_bounded(self):
        history=PublicHistory('contract',{},[],index_path='issued-public-index')
        for n in range(131):
            call=dict(type='function_call',name='act',call_id=str(n),arguments=json.dumps({'public_decision':{'evidence':'e'*160}}))
            history.append([call],call,{'step_id':n},[],{'path':f'public-{n}.json','sha256':'synthetic'})
        payload=history.payload({},4000)
        self.assertEqual(len(history.index),131)
        notice=json.loads(payload['input'][2]['content'])
        self.assertGreater(notice['older_index_entries_omitted'],0)
        self.assertEqual(notice['public_history_index'][-1]['call_id'],'130')
        self.assertLessEqual(len(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()),4000)

    def test_real_registration_function_returns_matching_new_scope(self):
        root=ROOT/'registration';output=root/'second';output.mkdir(parents=True)
        budget=root/'budget-coordination';budget.mkdir()
        save(budget/'batch-terms.example.json',{'example_only':True,'max_calls':120})
        skill=root/'skill.md';skill.write_text('synthetic');scene=root/'scene.xml';scene.write_text('synthetic')
        tree=ast.parse((BASE/'api-apple-v2/run_api_policy.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='register')
        commands=[]
        def fake_run(cmd,**kw):commands.append(cmd);return NS(returncode=0,stdout='offline',stderr='')
        scope=dict(ROOT=root,SCENE=scene,RUN='first',Path=Path,json=json,hashlib=hashlib,
            sys=sys,subprocess=NS(run=fake_run),save=save,__file__=str(BASE/'api-apple-v2/run_api_policy.py'))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-register','exec'),scope)
        result=scope['register'](output,skill,'second','apple-test',{'previous_run':'first'})
        self.assertEqual(result,root/'budget-coordination/approvals/second/registration.json')
        self.assertIn('second',commands[0]);terms=json.loads((output/'batch-terms.json').read_text())
        self.assertEqual(terms['batch_id'],'second');self.assertEqual(terms['previous_completed_batch']['previous_run'],'first')


if __name__=='__main__':unittest.main()
