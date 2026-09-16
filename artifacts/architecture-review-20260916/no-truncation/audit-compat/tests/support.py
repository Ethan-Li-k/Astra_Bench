import ast,hashlib,importlib.util,json,os,sys,time,types
from pathlib import Path
B=Path(__file__).resolve().parents[1];RSI=Path('/home/galbot/lizekai/RSI')
sys.dont_write_bytecode=True
sys.path.insert(0,str(RSI))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
NETWORK={'message':'stream disconnected before response.completed','codexErrorInfo':{'responseStreamDisconnected':{'httpStatusCode':None}}}
def terminal(status='completed',error=None,tid='t1',thread='thread'):
 return {'method':'turn/completed','params':{'threadId':thread,'turn':{'id':tid,'status':status,'error':error}}}
def call(tid='t1',name='scalebfm_act',finish=False):
 return {'method':'item/tool/call','id':tid+name+str(finish),'params':{'threadId':'thread','turnId':tid,'tool':name,'callId':tid+name+str(finish),'arguments':{'finish':finish}}}
def recovered():return [call(),terminal('failed',NETWORK),call('t2',finish=True),call('t2','skill_update'),terminal(tid='t2')]
class Transport:
 def __init__(self,events):self.events=list(events);self.starts=[];self.replies=[];self.waits=[];self.closed=False;self.fail_start_at=None;self.reply_error=None;self.ids=None
 def request(self,method,params,timeout):
  if method=='initialize':return {}
  if method=='thread/start':return {'thread':{'id':'thread'},'model':'gpt-6-astra','reasoningEffort':'xhigh','sandbox':{'type':'workspaceWrite','networkAccess':False},'approvalPolicy':'on-request','approvalsReviewer':'auto_review','runtimeWorkspaceRoots':[params['cwd']]}
  assert method=='turn/start';assert not self.closed;self.starts.append((params,timeout))
  if self.fail_start_at==len(self.starts):raise EOFError('ACK unknown')
  return {'turn':{'id':self.ids[len(self.starts)-1] if self.ids else 't'+str(len(self.starts))}}
 def notify(self,*a):pass
 def reply(self,identifier,result):
  if self.reply_error:raise self.reply_error
  self.replies.append((identifier,result))
 def next_message(self,timeout):
  self.waits.append(timeout)
  if not self.events:raise EOFError('closed without terminal')
  e=self.events.pop(0)
  if callable(e):return e()
  if isinstance(e,Exception):raise e
  return e
 def close(self):self.closed=True
class Host:
 method='direct'
 def __init__(self,output):
  self.output=output;self.rollout_root=output/'rollout';self.rollout_root.mkdir();self.task='fixture only';self.actions=0;self.finished=False;self.skill_updated=False;self.calls=[];self.closed=False;self.require_selection=False
  self.initialization_error=self.execution_error=self.stop_reason=None;self.episode_start_sim_s=0
  self.backend=types.SimpleNamespace(active=None,data=types.SimpleNamespace(time=0),scene_setup={'reset_provenance':{'reset_id':'reset-fixture'}},reason=None)
  self.harness=types.SimpleNamespace(evaluator=types.SimpleNamespace(outcome=lambda b:'success' if self.finished else 'in_progress'))
  (output/'video').mkdir();(output/'video/scene_setup.json').write_text(json.dumps(self.backend.scene_setup))
 def dispatch(self,name,args):
  assert not self.closed;self.calls.append(name)
  if name=='skill_update':self.skill_updated=True;return {'updated':True}
  self.actions+=1;self.finished=args.get('finish',False);self.backend.data.time+=1
  return {'observation':{'step_id':self.actions,'images':[]},'native_outcome':'success' if self.finished else 'in_progress','rollout_finished':self.finished}
 def next_call(self):return {'tool':'skill_update' if self.finished else 'scalebfm_act'}
 def close(self):self.closed=True

def run_case(root,events,*,tree='candidate',adapter_path=None,transport_edit=None,host_edit=None,write_failure=False):
 adapter=load('case_adapter',adapter_path or B/tree/'rsi/codex_app_server.py')
 audit=load('case_audit',B/tree/'tools/audit_simple_campaigns.py')
 memory_mod=load('case_memory',B/'snapshots/rsi/skill_learning.py')
 runner_path=B/tree/'tools/learn_grasp_skill.py';t=ast.parse(runner_path.read_text());f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='run_episode')
 skill=root/'seed.md';skill.write_text('---\nname: fixture\ndescription: Offline fixture.\n---\nObserve current public receipts.\n')
 memory=types.SimpleNamespace(skill=skill,journal=root/'absent',read=lambda:{'version':1})
 transport=Transport(events)
 if transport_edit:transport_edit(transport)
 made=[]
 def host_factory(output,*args):
  h=Host(output);h.memory=args[0];made.append(h)
  if host_edit:host_edit(h)
  return h
 scope=dict(Path=Path,json=json,os=os,time=time,hashlib=hashlib,LearningHost=host_factory,PYTHON=sys.executable,CODEX_LAUNCHER=RSI/'codex-account-2/run.sh',StdioAppServer=lambda *a:transport,CodexPolicyAdapter=adapter.CodexPolicyAdapter,validate_policy_instructions=memory_mod.validate_policy_instructions)
 scope.update({k:getattr(adapter,k) for k in ('TURN_RECORD_CONTRACT','NETWORK_CONTINUATION') if hasattr(adapter,k)})
 exec(compile(ast.Module(body=[f],type_ignores=[]),str(runner_path),'exec'),scope)
 from unittest.mock import patch
 original=Path.open
 def failing_open(p,*args,**kwargs):
  if p.name.startswith('turn_') and ('x' in (args[0] if args else kwargs.get('mode','r'))):raise OSError('injected terminal write failure')
  return original(p,*args,**kwargs)
 with patch.object(Path,'open',failing_open if write_failure else original):
  result=scope['run_episode'](root/'episode',memory,'fixture',0,task_specification={'completion_contract':{'id':'fixed-fixture-contract'},'human_feedback':{'used':True,'sources':[]}})
 ep=root/'episode';(ep/'success_review.json').write_text(json.dumps({'audited_task_success':True,'private_contact':'HOST_SECRET'}))
 return ep,result,audit.episode_status(ep),transport,made[0],audit
