"""Execute the snapshotted real run_episode function with fake transport/backend only."""
import ast,hashlib,json,os,sys,tempfile,time,types,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_continuity import BASE,mod,Transport,Host,tool,terminal,NETWORK
class CallerIntegration(unittest.TestCase):
 def test_existing_caller_keeps_host_until_recovered_turn_finishes(self):
  with tempfile.TemporaryDirectory(dir=BASE/'tests') as tmp:
   root=Path(tmp);memory=types.SimpleNamespace(skill=root/'seed.md',journal=root/'absent',read=lambda:{'version':1})
   memory.skill.write_text('seed')
   events=[tool(),terminal('failed',NETWORK)]
   second=tool();second['id']=2;second['params'].update(turnId='t2',callId='physical-2');events.append(second)
   update=tool();update['id']=3;update['params'].update(turnId='t2',callId='update',tool='skill_update');events.extend([update,terminal(turn='t2')])
   transport=Transport(events);closed=[]
   base_request=transport.request
   def request(method,params,timeout):
    if method=='initialize':return {}
    if method=='thread/start':return {'thread':{'id':'thread'},'model':'gpt-6-astra','reasoningEffort':'xhigh'}
    return base_request(method,params,timeout)
   transport.request=request;transport.notify=lambda *a:None
   transport.close=lambda:closed.append('transport')
   host=Host();host.method='direct';host.task='public task';host.rollout_root=root/'public';host.require_selection=False
   host.initialization_error=host.execution_error=host.stop_reason=None;host.episode_start_sim_s=0
   host.backend.data=types.SimpleNamespace(time=0)
   host.harness=types.SimpleNamespace(evaluator=types.SimpleNamespace(outcome=lambda b:'in_progress'))
   host.close=lambda:closed.append('host')
   dispatch=host.dispatch
   def checked_dispatch(name,args):
    self.assertEqual(closed,[])
    if name=='skill_update':host.skill_updated=True;return {'updated':True}
    return dispatch(name,args)
   host.dispatch=checked_dispatch
   tree=ast.parse((BASE/'snapshots/tools/learn_grasp_skill.py').read_text())
   node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_episode')
   scope=dict(Path=Path,json=json,os=os,time=time,hashlib=hashlib,
    LearningHost=lambda *a:host,PYTHON=sys.executable,
    CODEX_LAUNCHER=Path('/home/galbot/lizekai/RSI/codex-account-2/run.sh'),
    StdioAppServer=lambda *a:transport,CodexPolicyAdapter=mod.CodexPolicyAdapter)
   exec(compile(ast.Module(body=[node],type_ignores=[]),'snapshotted_run_episode','exec'),scope)
   result=scope['run_episode'](root/'episode',memory,'test',0)
   self.assertIsNone(result['error']);self.assertEqual(result['codex_turns'],2)
   self.assertEqual(result['actions'],2);self.assertEqual(host.calls,['act','act'])
   self.assertEqual(closed,['host','transport'])
   self.assertTrue((root/'episode/turn_002.json').exists())
   self.assertEqual(len(list((root/'episode/agent/continuity').glob('*.json'))),1)
if __name__=='__main__':unittest.main(verbosity=2)
