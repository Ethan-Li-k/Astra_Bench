"""Publication-safe copy of the eight alignment checks; synthetic fixtures only.
Original benchmark-alignment evidence remains unchanged. Uses ref baseline snapshot.
"""
import copy, json, tempfile, unittest, sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'human-feedback/tools'))
from dashboard import Dashboard, SIX_TASKS
from simple_six import scorecard

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


class AlignmentTests(unittest.TestCase):
    def score(self,rows=None,candidate=None):return scorecard(rows or [],NATIVE,'2026-09-16T12:28:40Z',candidate)
    def test_new_plan_is_six_times_three_times_ten_no_planned_denominator(self):
        s=self.score();self.assertEqual(s['frozen']['planned'],30)
        self.assertEqual(list(s['frozen']['levels']),['L0','L1','L2'])
        self.assertEqual(sum(v['planned'] for v in s['frozen']['levels'].values())*6,180)
        for v in s['frozen']['levels'].values():
            self.assertEqual(v['state'],'alignment-pending');self.assertEqual(v['planned'],10)
            for key in ('native','semantic'):
                self.assertEqual(v[key]['denominator'],0);self.assertIsNone(v[key]['percent'])
    def test_learning_never_backfills_official_level_even_when_labeled_l0(self):
        a=sample('a',True,True);a['evaluation']={'benchmark_level':'L0','dr_level':0,'renderer':'Isaac','ready':True}
        b=sample('b',False,True);s=self.score([a,b]);self.assertEqual(s['current']['semantic']['denominator'],2)
        for v in s['frozen']['levels'].values():self.assertEqual(v['native']['denominator'],0)
    def test_levels_and_native_semantic_are_distinct_objects(self):
        s=self.score();levels=s['frozen']['levels'];levels['L0']['native']['numerator']=9
        self.assertEqual(levels['L0']['semantic']['numerator'],0);self.assertEqual(levels['L1']['native']['numerator'],0)
    def test_legacy_ten_reset_manifest_is_preserved_but_not_official(self):
        import hashlib
        from simple_six import CONFIG_KEYS,PROTOCOL
        config={k:'f'*64 for k in CONFIG_KEYS};config.update(skill='b'*64,runtime='c'*64)
        digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        manifest={'protocol':PROTOCOL,'native_env_id':NATIVE,'locked':True,'config_sha256':config,'candidate_sha256':digest,
          'human_feedback_used':False,'registered_at':'2026-09-16T12:59:00Z','stability_reset_ids':['s'+str(i) for i in range(5)],'frozen_reset_ids':['f'+str(i) for i in range(10)]}
        rows=[sample(rid,True) for rid in manifest['stability_reset_ids']]+[sample('f0',False)]
        for r in rows:r['evaluation']={'candidate_sha256':digest,'config_sha256':config,'loaded':True,'config_unchanged':True,'dr_level':0}
        s=self.score(rows,manifest);self.assertEqual(s['stability']['consecutive'],5)
        self.assertTrue(s['legacy_frozen']['registered']);self.assertEqual(s['legacy_frozen']['semantic']['denominator'],1)
        self.assertFalse(s['frozen']['registered']);self.assertTrue(all(v['native']['denominator']==0 for v in s['frozen']['levels'].values()))
    def test_learning_denominators_and_assistance_remain_identical(self):
        a=sample('a',True,True,when='2026-09-16T11:00:00Z');b=sample('b',False,True,when='2026-09-16T11:10:00Z')
        b['result']['stop_reason']='episode_step_budget';b['review']['termination_class']='budget_truncation'
        c=sample('c',True,False);c['review']['audited_task_success']=False
        s=self.score([a,b,c]);history=next(g for g in s['groups'] if g['period']=='history')
        self.assertEqual(history['assistance'],'assisted');self.assertEqual(history['semantic']['denominator'],2)
        self.assertEqual(s['current']['native']['numerator'],1);self.assertEqual(s['current']['semantic']['numerator'],0)
    def test_official_values_order_source_and_capture_time(self):
        from simple_six import official_baseline
        doc=json.loads((ROOT/'ref/SIMPLE_OFFICIAL_BASELINE_20260916.json').read_text())
        b=official_baseline(doc,list(SIX_TASKS));self.assertTrue(b['available'])
        self.assertEqual(b['task_order'],list(SIX_TASKS));self.assertEqual(len(b['rows']),9)
        self.assertEqual({r['method']:r['values'] for r in b['rows']},doc['baseline_rows'])
        self.assertEqual(b['source_url'],doc['source_url']);self.assertEqual(b['read_at'],doc['read_at'])
        self.assertEqual(b['rows'][-1]['values'][0],[10,10,5]) # current ACT, not README
        self.assertEqual(next(r for r in b['rows'] if r['method']=='DreamZero')['values'][0],[10,10,10])
    def test_malformed_baseline_and_hidden_fields_are_not_published(self):
        from simple_six import official_baseline
        d=json.loads((ROOT/'ref/SIMPLE_OFFICIAL_BASELINE_20260916.json').read_text());d['host_only']='POISON'
        self.assertNotIn('POISON',json.dumps(official_baseline(d,list(SIX_TASKS))))
        for change in ('wrong-order','bad-count','bad-url'):
            a=copy.deepcopy(d)
            if change=='wrong-order':a['task_order'].reverse()
            if change=='bad-count':a['baseline_rows']['ACT'][0][0]=11
            if change=='bad-url':a['source_url']='file:///etc/passwd'
            self.assertFalse(official_baseline(a,list(SIX_TASKS))['available'])
    def test_fixed_source_updates_on_next_projection_no_model_or_queue(self):
        tmp=tempfile.TemporaryDirectory(prefix='fixture-',dir=OUT);self.addCleanup(tmp.cleanup);root=Path(tmp.name);d=Dashboard(root)
        def write(rel,value):
            p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return p
        write('artifacts/architecture-review-20260916/six-task-focus/benchmark-mapping-evidence.json',{'mapping':SIX_TASKS})
        src=json.loads((ROOT/'ref/SIMPLE_OFFICIAL_BASELINE_20260916.json').read_text())
        write('ref/SIMPLE_OFFICIAL_BASELINE_20260916.json',src)
        with patch('subprocess.run') as noexec:
            a=d.snapshot(force=True)['tasks'][0];self.assertEqual(a['official_baseline']['read_at'],src['read_at'])
            src['read_at']='2026-09-16T14:00:00+00:00';write('ref/SIMPLE_OFFICIAL_BASELINE_20260916.json',src)
            with patch('dashboard.time.time',return_value=d.cached_at+5):b=d.snapshot()['tasks'][0]
            self.assertEqual(b['official_baseline']['read_at'],src['read_at']);noexec.assert_not_called()
            self.assertIsNone(b['last_action_at'])
        self.assertEqual(a['subtasks'][0]['scorecard']['groups'],b['subtasks'][0]['scorecard']['groups'])

if __name__=='__main__':unittest.main(verbosity=2)
