from support import *
import copy,tempfile,unittest
from unittest.mock import patch

class JointTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=B/'tests');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def case(self,events=None,**kwargs):return run_case(self.root,recovered() if events is None else events,**kwargs)
 def test_recovered_sequence_recorded_before_successor_and_audited(self):
  def inspect(t):
   original=t.request
   def request(method,params,timeout):
    if method=='turn/start' and len(t.starts)==1:
     prior=json.loads((self.root/'episode/turn_001.json').read_text())
     self.assertEqual(prior['status'],'failed');self.assertEqual(prior['error'],NETWORK)
     self.assertFalse(t.closed)
    return original(method,params,timeout)
   t.request=request
  ep,r,s,t,h,a=self.case(transport_edit=inspect)
  self.assertTrue(r['success']);self.assertTrue(s['audited_task_success'])
  self.assertEqual(sorted(p.name for p in ep.glob('turn_*.json')),['turn_001.json','turn_002.json'])
  self.assertEqual(r['codex_turn_ids'],['t1','t2']);self.assertEqual(r['codex_turns'],2)
  self.assertEqual(h.calls,['scalebfm_act','scalebfm_act','skill_update']);self.assertEqual(h.actions,2)
  self.assertTrue(h.closed);self.assertTrue(t.closed);self.assertTrue(all(x is None for x in t.waits))
  self.assertEqual({p['threadId'] for p,_ in t.starts},{'thread'})
  self.assertTrue(all(p['approvalPolicy']=='on-request' for p,_ in t.starts))
  self.assertTrue(s['human_feedback_used']);self.assertEqual(s['completion_contract'],'fixed-fixture-contract');self.assertEqual(s['reset_id'],'reset-fixture')
  for i,status in [(1,'failed'),(2,'completed')]:
   row=json.loads((ep/f'turn_{i:03d}.json').read_text());self.assertEqual(row['id'],f't{i}');self.assertEqual(row['status'],status);self.assertEqual(row['_rsi_terminal']['sequence'],i)
  self.assertNotIn('HOST_SECRET',json.dumps(t.starts+t.replies));self.assertNotIn('reset-fixture',json.dumps(t.starts+t.replies))
 def test_unrecovered_failed_terminal_is_preserved(self):
  ep,r,s,t,h,a=self.case([call(),terminal('failed',{'message':'usageLimitExceeded stream disconnected'})])
  self.assertFalse(s['audited_task_success']);self.assertFalse(s['full_turn_completed']);self.assertEqual(len(t.starts),1)
  self.assertEqual(json.loads((ep/'turn_001.json').read_text())['status'],'failed')
 def test_no_new_progress_after_recovery_does_not_loop(self):
  ep,r,s,t,h,a=self.case([call(),terminal('failed',NETWORK),terminal('failed',NETWORK,'t2')])
  self.assertIn('no_new_physical_progress',r['error']);self.assertEqual(len(t.starts),2);self.assertEqual(h.actions,1)
  self.assertEqual(len(list(ep.glob('turn_*.json'))),2);self.assertFalse(s['audited_task_success']);self.assertTrue(h.closed)
 def test_notifications_eof_wrong_terminal_never_start_successor(self):
  for suffix in ([{'method':'error','params':{'error':NETWORK,'willRetry':False}}], [terminal('failed',NETWORK,'another')], [terminal('failed',NETWORK,thread='other')], [EOFError('lost')]):
   with self.subTest(suffix=suffix),tempfile.TemporaryDirectory(dir=B/'tests') as d:
    ep,r,s,t,h,a=run_case(Path(d),[call()]+suffix)
    self.assertEqual(len(t.starts),1);self.assertEqual(h.actions,1);self.assertFalse(s['audited_task_success']);self.assertEqual(list(ep.glob('turn_*.json')),[])
 def test_unknown_reply_and_successor_ack_never_replay(self):
  for change,actions,starts,receipts in [(lambda t:setattr(t,'reply_error',BrokenPipeError('unknown reply')),1,1,0),(lambda t:setattr(t,'fail_start_at',2),1,2,1)]:
   with self.subTest(starts=starts),tempfile.TemporaryDirectory(dir=B/'tests') as d:
    ep,r,s,t,h,a=run_case(Path(d),recovered(),transport_edit=change)
    self.assertEqual(h.actions,actions);self.assertEqual(len(t.starts),starts);self.assertEqual(len(list(ep.glob('turn_*.json'))),receipts);self.assertFalse(s['audited_task_success'])
 def test_permission_safety_incomplete_interrupted_and_budget_not_recovered(self):
  cases=[('failed',{'message':x+' stream disconnected'},False) for x in ('quota','permission denied','safety','authorization','httpStatusCode429')]
  cases += [('incomplete',NETWORK,False),('interrupted',NETWORK,False),('failed',NETWORK,True)]
  for status,error,finished in cases:
   with self.subTest(status=status,error=error),tempfile.TemporaryDirectory(dir=B/'tests') as d:
    ep,r,s,t,h,a=run_case(Path(d),[call(finish=finished),terminal(status,error)])
    self.assertEqual(len(t.starts),1);self.assertFalse(s['audited_task_success']);self.assertTrue((ep/'turn_001.json').exists())
 def test_reset_backend_host_validity_and_pending_execution(self):
  for kind in ('reset','backend','active','missing_reset','malformed_reset'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=B/'tests') as d:
    hosts=[]
    def mutate():
     h=hosts[0]
     if kind=='reset':h.backend.scene_setup['reset_provenance']['reset_id']='different'
     if kind=='backend':h.backend=copy.copy(h.backend)
     if kind=='active':h.backend.active='unacknowledged action'
     if kind=='missing_reset':h.backend.scene_setup={}
     if kind=='malformed_reset':h.backend.scene_setup={'reset_provenance':None}
     return terminal('failed',NETWORK)
    ep,r,s,t,h,a=run_case(Path(d),[call(),mutate],host_edit=hosts.append)
    self.assertEqual(len(t.starts),1);self.assertFalse(s['audited_task_success'])
 def test_auditor_rejects_number_identity_order_and_truncated_records(self):
  ep,r,s,t,h,a=self.case();self.assertTrue(s['audited_task_success'])
  original={p.name:p.read_text() for p in ep.glob('turn_*.json')};result=(ep/'result.json').read_text()
  changes=['missing','extra','duplicate_id','wrong_id','wrong_thread','wrong_sequence','last_failed','last_incomplete','unrecovered','changed_reset','truncated','missing_contract','unknown_contract','wrong_count','duplicate_ack_ids']
  for change in changes:
   with self.subTest(change=change):
    for p in ep.glob('turn_*.json'):p.unlink()
    for name,text in original.items():(ep/name).write_text(text)
    (ep/'result.json').write_text(result)
    p=ep/'turn_002.json';row=json.loads(p.read_text());changed_result=json.loads(result)
    if change=='missing':(ep/'turn_001.json').unlink()
    elif change=='extra':(ep/'turn_003.json').write_text(original['turn_002.json'])
    elif change=='truncated':p.write_text('{')
    elif change=='missing_contract':changed_result.pop('turn_record_contract');(ep/'result.json').write_text(json.dumps(changed_result))
    elif change=='unknown_contract':changed_result['turn_record_contract']='v99';(ep/'result.json').write_text(json.dumps(changed_result))
    elif change=='wrong_count':changed_result['codex_turns']=1;(ep/'result.json').write_text(json.dumps(changed_result))
    elif change=='duplicate_ack_ids':changed_result['codex_turn_ids']=['t1','t1'];(ep/'result.json').write_text(json.dumps(changed_result))
    else:
     if change=='duplicate_id':row['id']='t1'
     if change=='wrong_id':row['id']='wrong'
     if change=='wrong_thread':row['_rsi_terminal']['thread_id']='wrong'
     if change=='wrong_sequence':row['_rsi_terminal']['sequence']=1
     if change=='last_failed':row['status']='failed';row['error']=NETWORK;row['_rsi_terminal']['recovery_reason']='confirmed_closed_network_turn'
     if change=='last_incomplete':row['status']='inProgress'
     if change=='changed_reset':row['_rsi_terminal']['reset_id']='other'
     if change=='unrecovered':
      p=ep/'turn_001.json';row=json.loads(p.read_text());row['_rsi_terminal']['recovery_reason']='nonrecoverable_terminal'
     p.write_text(json.dumps(row))
    audited=a.episode_status(ep);self.assertFalse(audited['full_turn_completed']);self.assertFalse(audited['audited_task_success'])
 def test_write_failure_does_not_continue_or_count_success(self):
  for events in (recovered(),[call(finish=True),call(name='skill_update'),terminal()]):
   with self.subTest(events=events),tempfile.TemporaryDirectory(dir=B/'tests') as d:
    ep,r,s,t,h,a=run_case(Path(d),events,write_failure=True)
    self.assertIn('write failure',r['error']);self.assertEqual(len(t.starts),1);self.assertFalse(s['audited_task_success'])
 def test_fsync_failure_cannot_count_success(self):
  with patch('os.fsync',side_effect=OSError('fsync failed')):
   ep,r,s,t,h,a=self.case([call(finish=True),call(name='skill_update'),terminal()])
  self.assertIn('fsync failed',r['error']);self.assertFalse(s['host_success_complete']);self.assertFalse(s['audited_task_success'])
 def test_duplicate_start_identity_cannot_overwrite_first_turn(self):
  ep,r,s,t,h,a=self.case(transport_edit=lambda t:setattr(t,'ids',['t1','t1']))
  self.assertIn('duplicate',r['error']);self.assertEqual(len(list(ep.glob('turn_*.json'))),1);self.assertEqual(h.actions,1);self.assertFalse(s['audited_task_success'])
 def test_existing_terminal_is_not_overwritten(self):
  marker='original evidence'
  def edit(h):(h.output/'turn_001.json').write_text(marker)
  ep,r,s,t,h,a=self.case(host_edit=edit)
  self.assertEqual((ep/'turn_001.json').read_text(),marker);self.assertIn('FileExistsError',r['error']);self.assertEqual(len(t.starts),1);self.assertFalse(s['audited_task_success'])
 def test_host_success_revision_contract_feedback_and_audit_gates_remain(self):
  ep,r,s,t,h,a=self.case();original=(ep/'result.json').read_text()
  for key,value in [('success',False),('native_outcome','failure'),('skill_updated',False),('actions',0),('error','fault')]:
   with self.subTest(key=key):
    j=json.loads(original);j[key]=value;(ep/'result.json').write_text(json.dumps(j));self.assertFalse(a.episode_status(ep)['audited_task_success'])
  (ep/'result.json').write_text(original)
  renamed=ep.with_name('episode-0001');ep.rename(renamed);ep=renamed
  same=a.memory_success_review(ep.parent,'fixed-fixture-contract')(ep.name)
  other=a.memory_success_review(ep.parent,'other-contract')(ep.name)
  self.assertTrue(same['audited_task_success']);self.assertTrue(same['completion_contract_matches'])
  self.assertFalse(other['completion_contract_matches'])
  for review in (False,None):
   (ep/'success_review.json').write_text(json.dumps({'audited_task_success':review}));self.assertFalse(a.episode_status(ep)['audited_task_success'])
 def test_legacy_no_recovery_success_and_failure_preserved(self):
  ep,r,s,t,h,a=self.case([call(finish=True),call(name='skill_update'),terminal()])
  rr=json.loads((ep/'result.json').read_text());rr.pop('turn_record_contract');rr.pop('codex_turn_ids');rr.pop('codex_thread_id')
  row=json.loads((ep/'turn_001.json').read_text());row.pop('_rsi_terminal');(ep/'turn_001.json').write_text(json.dumps(row));(ep/'result.json').write_text(json.dumps(rr))
  self.assertTrue(a.episode_status(ep)['audited_task_success'])
  rr['success']=False;rr['native_outcome']='failure';(ep/'result.json').write_text(json.dumps(rr));self.assertFalse(a.episode_status(ep)['audited_task_success'])
 def test_previous_candidate_gap_is_rejected_by_new_legacy_count_check(self):
  a=load('audit_gap',B/'candidate/tools/audit_simple_campaigns.py')
  self.assertFalse(a.episode_status(B/'evidence/reproduction-episode/episode')['audited_task_success'])

 def test_new_incomplete_receipt_chain_is_ineligible_for_success_memory(self):
  ep,r,s,t,h,a=self.case();renamed=ep.with_name('episode-0001');ep.rename(renamed);ep=renamed
  m=load('new_chain_memory',B/'snapshots/rsi/skill_learning.py')
  skill=self.root/'memory-skill.md';skill.write_text('---\nname: loco-manip-direct\ndescription: Fixture.\n---\nObserve.\n')
  memory=m.SkillMemory(self.root/'memory',skill,success_review=a.memory_success_review(self.root,'fixed-fixture-contract'))
  public=ep/'rollout/public.json';public.write_text('{"observed":"fixture"}')
  memory.update(skill.read_text(),'Public fixture lesson',[public],ep/'rollout',ep.name,'success')
  self.assertTrue(memory.read()['experiences'][0]['retrieval']['success_priority_eligible'])
  original=memory.journal.read_bytes();(ep/'turn_001.json').unlink()
  packet=memory.read();self.assertFalse(packet['experiences'][0]['retrieval']['success_priority_eligible'])
  self.assertEqual(memory.journal.read_bytes(),original);self.assertNotIn('HOST_SECRET',json.dumps(packet))
 def test_completed_historical_episodes_match_current_auditor(self):
  old=load('old_audit',B/'snapshots/tools/audit_simple_campaigns.py');new=load('new_audit',B/'candidate/tools/audit_simple_campaigns.py')
  for campaign,episode in [('door','0016'),('faucet','0008'),('apple','0007')]:
   path=RSI/f'artifacts/R019/{campaign}-campaign/episode-{episode}'
   with self.subTest(episode=str(path)):
    before=old.episode_status(path);after=new.episode_status(path);after.pop('turn_record_integrity')
    self.assertEqual(before,after)
 def test_recovery_is_disabled_without_terminal_recorder(self):
  a=load('no_sink_adapter',B/'candidate/rsi/codex_app_server.py');root=self.root/'raw';root.mkdir();h=Host(root);t=Transport([call(),terminal('failed',NETWORK)])
  adapter=a.CodexPolicyAdapter(t,h,root/'agent',developer_instructions='fixture');adapter.connect()
  with self.assertRaisesRegex(RuntimeError,'terminal_recorder_required'):adapter.run_turn('go')
  self.assertEqual(len(t.starts),1);self.assertEqual(h.actions,1)

if __name__=='__main__':unittest.main(verbosity=2)
