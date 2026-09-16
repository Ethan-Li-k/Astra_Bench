import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from dashboard import Dashboard, SIX_TASKS, hash_json
from feedback_board import FeedbackBoard

OUT=Path(__file__).resolve().parent
NATIVE=SIX_TASKS['XMovePick']

def sample(reset='r1', success=False, assisted=False, stop='budget_truncation', when='2026-09-16T13:00:00Z'):
    return {'episode':'episode-0001','key':'xmovepick','actions':8,'order':1,
      'result_ref':{'at':1,'sha256':'a'*64},'result':{'actions':8,'native_outcome':'success' if success else 'in_progress',
        'stop_reason':'native_success' if success else stop,'error':None,'starting_skill_sha256':'b'*64,'human_feedback_used':assisted},
      'review':{'audited_task_success':success,'full_turn_and_skill_update':True,'turn_record_integrity':'complete_terminal_sequence'},
      'scene':{'env_id':NATIVE,'variant':'native checkpoint','pd_profile':'checkpoint','human_feedback_used':assisted,
        'reset_provenance':{'method':'fresh_environment_reset','reset_id':reset,'recorded_utc':when}},
      'budget':{'skill_sha256':'b'*64,'runtime_sha256':'c'*64},'ledger':{'completion_contract':'native_simple_criterion'},'evaluation':{}}

class Scores(unittest.TestCase):
    def score(self,rows,**kw):
        from simple_six import scorecard
        return scorecard(rows,NATIVE,'2026-09-16T12:28:40Z',**kw)
    def group(self,s):return s['groups'][0]
    def test_empty_is_unmeasured(self):
        s=self.score([]);self.assertEqual(s['current']['semantic']['denominator'],0);self.assertIsNone(s['current']['semantic']['percent']);self.assertIsNone(s['stability']['consecutive']);self.assertEqual(s['frozen']['planned'],10)
    def test_completed_budget_and_safety_are_denominator(self):
        a=sample('a',True);b=sample('b');c=sample('c',stop='runtime_safety_stop')
        s=self.score([a,b,c]);self.assertEqual(s['current']['semantic'],{'numerator':1,'denominator':3,'percent':100/3})
    def test_native_and_semantic_disagreement(self):
        a=sample(success=True);a['review']['audited_task_success']=False;s=self.score([a]);g=self.group(s)
        self.assertEqual(g['native']['numerator'],1);self.assertEqual(g['semantic']['numerator'],0)
    def test_inflight_missing_audit_or_identity_never_failure(self):
        a=sample('a');a['result_ref']=None;b=sample('b');b['review']={};c=sample('c');c['scene'].pop('pd_profile')
        s=self.score([a,b,c]);self.assertEqual(s['current']['semantic']['denominator'],0);self.assertEqual(s['dispositions']['pending'],2);self.assertEqual(s['dispositions']['inflight'],1)
    def test_assistance_history_variants_and_duplicate_reset_separate(self):
        a=sample('a',True,True,when='2026-09-16T11:00:00Z');b=sample('b');c=sample('c');c['scene']['variant']='repaired'
        s=self.score([a,b,c,copy.deepcopy(b)]);self.assertEqual(len(s['groups']),3);self.assertEqual(s['dispositions']['duplicate'],1)
        h=next(x for x in s['groups'] if x['period']=='history');self.assertEqual(h['assistance'],'assisted');self.assertEqual(h['semantic']['numerator'],1)
    def test_system_pause_and_replay_are_explicit_exclusions(self):
        a=sample('a',stop='infrastructure_error');b=sample('b',stop='user_requested_pause');c=sample('c');c['review']['no_replay_or_diagnostic_initial_state']=False
        s=self.score([a,b,c]);self.assertEqual(s['current']['semantic']['denominator'],0)
        for k in ('infrastructure','paused','replay'):self.assertEqual(s['dispositions'][k],1)
    def test_unknown_configuration_not_silently_counted_and_no_host_data(self):
        a=sample();a['scene']['object_truth']='POISON';a['review']['host_only_question']='POISON';s=self.score([a]);self.assertNotIn('POISON',json.dumps(s));a['budget']['skill_sha256']='d'*64
        self.assertEqual(self.score([a])['dispositions']['pending'],1)
    def test_actual_step_budget_schema_remains_valid_failure(self):
        a=sample();a['result']['stop_reason']='episode_step_budget';a['review']['termination_class']='budget_truncation'
        s=self.score([a]);self.assertEqual(s['current']['semantic']['denominator'],1);self.assertEqual(s['current']['semantic']['numerator'],0)
    def test_fixed_candidate_five_and_frozen_actual_denominator_not_planned(self):
        import hashlib
        from simple_six import CONFIG_KEYS,PROTOCOL
        config={k:'f'*64 for k in CONFIG_KEYS};config.update(skill='b'*64,runtime='c'*64);digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        manifest={'protocol':PROTOCOL,'native_env_id':NATIVE,'locked':True,'config_sha256':config,'candidate_sha256':digest,
          'human_feedback_used':False,'registered_at':'2026-09-16T12:59:00Z','stability_reset_ids':['s'+str(i) for i in range(5)],'frozen_reset_ids':['f'+str(i) for i in range(10)]}
        rows=[sample(rid,True) for rid in manifest['stability_reset_ids']]+[sample('f0',False)]
        for r in rows:r['evaluation']={'candidate_sha256':digest,'config_sha256':config,'loaded':True,'config_unchanged':True}
        s=self.score(rows,candidate=manifest);self.assertEqual(s['stability']['consecutive'],5);self.assertTrue(s['frozen']['registered'])
        self.assertEqual(s['frozen']['semantic']['denominator'],1);self.assertEqual(s['frozen']['semantic']['numerator'],0);self.assertEqual(s['current']['semantic']['denominator'],0)
        rows[2]['evaluation']={};s=self.score(rows,candidate=manifest);self.assertIsNone(s['stability']['consecutive']);self.assertFalse(s['frozen']['registered'])

class Binding(unittest.TestCase):
    def test_context_pins_exact_six_task_immutable_and_old_payload_still_valid(self):
        root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));d=Dashboard(root);b=FeedbackBoard(d,root/'feedback',True)
        task={'id':'simple','subtasks':[{'id':'benchmark-1','native_env_id':NATIVE}]};task['version']=hash_json(task);b.publish_packages([task])
        p={'request_id':'fixture-context-001','task_id':'simple','case_id':None,'source_version':task['version'],'text':'工程隔离原文','choice':'','user_timestamp':'2026-09-16T13:00:00Z','correction_of':None,'context':{'subtask_id':'benchmark-1','native_env_id':NATIVE}}
        with patch('subprocess.run') as noqueue:
            rec=b.submit(p);self.assertEqual(rec['submission']['text'],p['text']);self.assertTrue(b.submit(p)['duplicate']);noqueue.assert_not_called()
        bad=copy.deepcopy(p);bad['request_id']='fixture-context-002';bad['context']['native_env_id']=SIX_TASKS['BendPick']
        with self.assertRaises(ValueError):b.submit(bad)
        old=copy.deepcopy(p);old.pop('context');old['request_id']='fixture-legacy-001';self.assertTrue(b.submit(old)['status']['saved'])

class PublicSources(unittest.TestCase):
    def test_historical_goal_does_not_complete_current_unsealed_episode(self):
        root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));d=Dashboard(root)
        def write(rel,value):
            p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        write('artifacts/architecture-review-20260916/six-task-focus/benchmark-mapping-evidence.json',{'mapping':SIX_TASKS})
        base='artifacts/R019/xmovepick-campaign'
        write(base+'/progress.json',{'task':NATIVE,'successes':1})
        write(base+'/episode-0003/video/scene_setup.json',{'env_id':NATIVE})
        write(base+'/episode-0003/result.json',{'actions':3,'native_outcome':'success'})
        write(base+'/episode-0003/success_review.json',{'task':NATIVE,'audited_task_success':True,'reset':{'reset_id':'old'}})
        write(base+'/episode-0004/video/scene_setup.json',{'env_id':NATIVE})
        write(base+'/episode-0004/rollout/episode/execution_0001.json',{'receipts':[{'command_id':'fixture-only','duration_s':1}]})
        write('artifacts/R019/campaign_audit.json',{'campaigns':[{'campaign':base,'task':NATIVE,'physical_attempts':2,'audited_task_successes':1,
          'episodes':[{'episode_id':'episode-0003','physical_attempt':True,'actions':3},{'episode_id':'episode-0004','physical_attempt':True,'actions':1}]}]})
        row=d.simple()['subtasks'][0];self.assertEqual(row['episode'],'episode-0004');self.assertNotEqual(row['state'],'complete');self.assertIsNone(row['success'])
    def test_actual_complete_episode_publisher_does_not_regress_to_candidate(self):
        root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));d=Dashboard(root)
        for name in ['status.json','first-action-physical-verification.json']:
            p=root/'artifacts/R019/robot-stability-integration-20260916'/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((OUT/('public-'+name)).read_bytes())
        row=d.framework();work=row['current_work'];self.assertTrue(work['deployed']);self.assertTrue(work['first_action_fields_verified'])
        self.assertTrue(work['first_complete_episode_audited']);self.assertFalse(work['physical_benefit_verified']);self.assertNotIn('未部署',row['problem'])
        self.assertIn('首个完整回合受限审计通过',row['summary'])

if __name__=='__main__':unittest.main(verbosity=2)
