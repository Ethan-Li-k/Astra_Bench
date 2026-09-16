import importlib.util, json, os, sys, tempfile, types, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
stub=types.ModuleType('rsi.policy_harness');stub.tool_specs=lambda method:[]
sys.modules['rsi.policy_harness']=stub
source=BASE/os.environ.get('ADAPTER_SOURCE','candidate/rsi/codex_app_server.py')
spec=importlib.util.spec_from_file_location('review_adapter',source)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def terminal(status='completed',error=None,turn='t1'):
 return {'method':'turn/completed','params':{'threadId':'thread','turn':{'id':turn,'status':status,'error':error}}}
def tool():
 return {'method':'item/tool/call','id':1,'params':{'threadId':'thread','turnId':'t1','tool':'act','callId':'physical-1','arguments':{}}}
NETWORK={'codexErrorInfo':{'responseStreamDisconnected':{'httpStatusCode':None}},'message':'stream disconnected before response.completed'}
class Transport:
 def __init__(self,events): self.events=list(events);self.starts=[];self.replies=[];self.waits=[];self.start_error=None;self.reply_error=None
 def request(self,method,params,timeout):
  assert method=='turn/start'
  self.starts.append((params,timeout))
  if self.start_error: raise self.start_error
  return {'turn':{'id':'t'+str(len(self.starts))}}
 def next_message(self,timeout):
  self.waits.append(timeout)
  if not self.events: raise EOFError('closed')
  e=self.events.pop(0)
  if isinstance(e,Exception): raise e
  return e
 def reply(self,identifier,result):
  if self.reply_error: raise self.reply_error
  self.replies.append((identifier,result))
class Host:
 def __init__(self):self.actions=0;self.finished=False;self.skill_updated=False;self.calls=[];self.backend=types.SimpleNamespace(active=False)
 def dispatch(self,name,args):
  self.calls.append(name);self.actions+=1
  return {'observation':{'step_id':self.actions,'images':[]},'rollout_finished':self.finished}
 def next_call(self):return {'name':'loco_observe','arguments':{}}
class Continuity(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=BASE/'tests');self.addCleanup(self.temp.cleanup)
 def setup_adapter(self,events):
  t=Transport(events);h=Host();a=mod.CodexPolicyAdapter(t,h,self.temp.name,developer_instructions='policy');a.thread_id='thread';return a,t,h
 def test_closed_network_after_action_continues_same_thread_without_replay(self):
  a,t,h=self.setup_adapter([tool(),terminal('failed',NETWORK),terminal(turn='t2')])
  self.assertEqual(a.run_turn('go')['status'],'completed');self.assertEqual(h.calls,['act'])
  self.assertEqual(len(t.starts),2);self.assertEqual({x[0]['threadId'] for x in t.starts},{'thread'})
  self.assertEqual(t.waits,[None]*3)
  records=list((Path(self.temp.name)/'continuity').glob('*.json'))
  self.assertEqual(len(records),1);self.assertEqual(json.loads(records[0].read_text())['turn']['error'],NETWORK)
  self.assertNotIn('responseStreamDisconnected',t.starts[1][0]['input'][0]['text'])
 def test_start_ack_has_no_wallclock_deadline(self):
  a,t,h=self.setup_adapter([terminal()]);a.run_turn('go');self.assertIsNone(t.starts[0][1])
 def test_uncertain_start_is_latched_and_not_reissued(self):
  a,t,h=self.setup_adapter([]);t.start_error=TimeoutError('ACK unknown')
  with self.assertRaises(TimeoutError):a.start_turn('go')
  t.start_error=None
  with self.assertRaisesRegex(RuntimeError,'uncertain'):a.start_turn('again')
  self.assertEqual(len(t.starts),1)
 def test_notification_without_terminal_does_not_continue(self):
  a,t,h=self.setup_adapter([tool(),{'method':'error','params':{'threadId':'thread','turnId':'t1','error':NETWORK,'willRetry':True}},EOFError('closed')])
  with self.assertRaises(EOFError):a.run_turn('go')
  self.assertEqual(len(t.starts),1);self.assertEqual(h.calls,['act'])
 def test_repeated_closed_failure_without_new_physical_progress_stops_retries(self):
  a,t,h=self.setup_adapter([tool(),terminal('failed',NETWORK),terminal('failed',NETWORK,'t2')])
  with self.assertRaisesRegex(RuntimeError,'no_new_physical_progress'):a.run_turn('go')
  self.assertEqual(len(t.starts),2);self.assertEqual(h.calls,['act'])
 def test_empty_initial_network_turn_requires_diagnosis(self):
  a,t,h=self.setup_adapter([terminal('failed',NETWORK)])
  with self.assertRaisesRegex(RuntimeError,'no_new_physical_progress'):a.run_turn('go')
  self.assertEqual(len(t.starts),1)
 def test_no_quota_safety_auth_incomplete_cancel_or_budget_retry(self):
  for status,error,finished in [('failed',{'message':'usageLimitExceeded stream disconnected'},False),('failed',{'message':'quota network error'},False),('failed',{'message':'safety network error'},False),('failed',{'message':'unauthorized network error'},False),('incomplete',NETWORK,False),('interrupted',NETWORK,False),('failed',NETWORK,True)]:
   with self.subTest(status=status,error=error,finished=finished):
    a,t,h=self.setup_adapter([tool(),terminal(status,error)]);h.finished=finished
    with self.assertRaises(RuntimeError):a.run_turn('go')
    self.assertEqual(len(t.starts),1)
 def test_uncertain_reply_never_resends_action_or_turn(self):
  a,t,h=self.setup_adapter([tool(),terminal('failed',NETWORK)]);t.reply_error=BrokenPipeError('unknown')
  with self.assertRaises(BrokenPipeError):a.run_turn('go')
  self.assertEqual(len(t.starts),1);self.assertEqual(h.calls,['act']);self.assertEqual(a.call_index,0)
 def test_wrong_terminal_is_ignored_and_natural_completion_unchanged(self):
  a,t,h=self.setup_adapter([terminal('failed',NETWORK,'another'),terminal()])
  self.assertEqual(a.run_turn('go')['status'],'completed');self.assertEqual(len(t.starts),1)
 def test_active_backend_prevents_recovery(self):
  a,t,h=self.setup_adapter([tool(),terminal('failed',NETWORK)]);h.backend.active=True
  with self.assertRaises(RuntimeError):a.run_turn('go')
  self.assertEqual(len(t.starts),1)
if __name__=='__main__': unittest.main(verbosity=2)
