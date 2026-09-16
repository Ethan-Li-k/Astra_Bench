"""Isolated public fixtures; no actors, delivery, production answers or model calls."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dashboard import Dashboard

OUT=Path(__file__).resolve().parent
FOCUS='artifacts/architecture-review-20260916/six-task-focus/'
AUDIT='artifacts/R019/campaign_audit.json'

class SixTaskTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));self.d=Dashboard(self.root);self.campaigns=[]
        self.mapping=json.loads((OUT/'public-source-snapshot/benchmark-mapping-evidence.json').read_text())
        self.write(FOCUS+'benchmark-mapping-evidence.json',self.mapping)
    def write(self,rel,data):
        p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
    def pause(self):
        d=json.loads((OUT/'public-source-snapshot/pause-status.json').read_text());self.write(FOCUS+'pause-status.json',d);return d
    def old_states(self):
        self.write('ikea/state.json',{'status':'continue','actor_running':True})
        self.write('ikea/actor-progress.json',{'episode':'apple-0002','phase':'inference_waiting','actions':43})
        self.write('ikea/web-progress.json',{'current_problem':'历史continue仍在等推理','next_step':'继续旧任务'})
        self.write('api-ground-to-table/actor-adapter/auxiliary-progress.json',{'episode':'episode-0005','state':'inference_waiting_no_deadline','actions':4,'current_problem':'HTTP 429：远端请求未知，不重发。'})
    def add(self,folder,task,assisted=False,actions=4,closed=True,scene_task=None):
        base='artifacts/R019/'+folder;ep='episode-0003';path=base+'/'+ep
        self.write(base+'/progress.json',{'task':task,'successes':1})
        self.write(path+'/video/scene_setup.json',{'env_id':scene_task or task,'human_feedback_used':assisted,'object_truth':'HIDDEN_OBJECT_SENTINEL'})
        result={'actions':actions,'native_outcome':'success','human_feedback_used':assisted,
                'human_feedback_sources':[{'path':str(self.root/'human-feedback/H001-user-feedback-004.json')}] if assisted else []}
        if closed:
            self.write(path+'/result.json',result)
            self.write(path+'/success_review.json',{'task':task,'audited_task_success':True,'human_feedback_used':assisted,'reset':{'reset_id':folder+'-reset'},'independent_reset_verified':True})
        else:self.write(path+'/rollout/episode/execution_0001.json',{'receipts':[{'command_id':'fixture','duration_s':1}] if actions else []})
        c={'campaign':base,'task':task,'physical_attempts':1 if actions else 0,'required_successes':1,'audited_task_successes':1 if closed else 0,
           'episodes':[{'episode_id':ep,'physical_attempt':actions>0,'actions':actions,'audited_task_success':closed,'task_audit_status':'passed' if closed else 'unknown','human_feedback_used':assisted}]}
        self.campaigns.append(c);self.write(AUDIT,{'campaigns':self.campaigns});return path
    def simple(self):return self.d.snapshot(force=True)['tasks'][0]
    def row(self,name):return next(x for x in self.simple()['subtasks'] if x['name']==name)

    def test_verified_pause_overrides_old_continue_but_keeps_evidence(self):
        self.old_states();self.pause();tasks={t['id']:t for t in self.d.snapshot(force=True)['tasks']}
        for key in ('ikea','ground'):
            d=tasks[key];self.assertEqual(d['state'],'paused');self.assertIn('用户已暂停',d['state_label'])
            self.assertEqual(d['pause_reason'],'user_requested_pause');self.assertIn('保留',d['next'])
            self.assertEqual(d['historical_status']['episode'],'apple-0002' if key=='ikea' else 'episode-0005')
        self.assertIn('HTTP 429',tasks['ground']['historical_status']['problem'])
        self.assertIn('EOF',tasks['ikea']['historical_status']['problem'])
        self.assertNotIn('raw_error_preserved',json.dumps(tasks))

    def test_zero_model_heartbeat_not_physics_and_marker_alone_not_verified_pause(self):
        self.old_states();d=self.pause();self.write('ikea/heartbeat.json',{'at':'2026-09-16T15:00:00Z','alive':True})
        ikea=self.d.snapshot(force=True)['tasks'][2];self.assertEqual(ikea['state'],'paused');self.assertIsNone(ikea['last_action_at'])
        self.assertIn('心跳',ikea['source_time_note'])
        for key in ('ikea','ground'):d[key].pop('actor_alive')
        self.write(FOCUS+'pause-status.json',d);tasks=Dashboard(self.root).snapshot()['tasks']
        self.assertNotEqual(tasks[1]['state'],'paused');self.assertNotEqual(tasks[2]['state'],'paused')

    def test_variants_do_not_count_as_bendpick_mp_or_between_tables(self):
        self.add('bendpick-campaign','simple/G1WholebodyBendPickTeleop-v0')
        self.add('mobilecheezit-campaign','simple/G1WholebodyMobilePickAndPlaceCheezitTeleop-v0')
        d=self.simple()
        for name in ('BendPick','Mobile P&P'):
            row=next(x for x in d['subtasks'] if x['name']==name)
            self.assertIsNone(row['success']);self.assertIsNone(row['actions']);self.assertIsNone(row['historical_audited_successes'])
            self.assertIn('未发现精确入口',row['problem'])
        self.assertIn('boxpick',[x['id'] for x in d['history_subtasks']]);self.assertIn('mobilecheezit',[x['id'] for x in d['history_subtasks']])

    def test_six_exact_ids_unknown_unstarted_and_no_name_based_match(self):
        self.add('grasp-campaign','simple/G1OtherGraspTeleop-v0')
        self.add('handover-campaign',self.mapping['mapping']['Handover'],actions=0)
        d=self.simple();self.assertEqual([x['name'] for x in d['subtasks']],list(self.mapping['mapping']))
        self.assertEqual([x['native_env_id'] for x in d['subtasks']],list(self.mapping['mapping'].values()))
        for row in d['subtasks']:
            self.assertIsNone(row['success']);self.assertIsNone(row['actions']);self.assertIn('未开始',row['state_label'])
        self.assertIn('待主管调度确认',d['scope_notice']);self.assertNotIn('优先推进推门',d['next'])

    def test_xmovepick_assisted_history_never_becomes_new_frozen_score(self):
        path=self.add('xmovepick-campaign',self.mapping['mapping']['XMovePick'],assisted=True)
        d=self.row('XMovePick');self.assertEqual(d['historical_audited_successes'],1)
        self.assertEqual(d['historical_assisted_successes'],1);self.assertEqual(d['historical_autonomous_successes'],0)
        self.assertIsNone(d['success']);self.assertNotEqual(d['state'],'complete')
        self.assertIn('H001-004',d['mode']);self.assertIn('新冻结测评',d['summary'])
        self.assertEqual(d['episode'],'episode-0003');self.assertNotIn('HIDDEN_OBJECT_SENTINEL',json.dumps(d))
        self.write(path+'/video/scene_setup.json',{'env_id':'simple/G1WholebodyXMovePickSimToRealTeleop-v0'})
        self.assertIsNone(self.row('XMovePick')['historical_audited_successes'])

    def test_explicit_owner_ack_requires_exact_mapping_and_does_not_claim_skill_loaded(self):
        source={'ack':'SIX-TASK-FOCUS-20260916 ACK','benchmark_mapping':self.mapping['mapping'],
                'current_problem':'核对MP入口控制兼容性','next_step':'完整回合后按精确入口适配'}
        self.write('codex-account-2/continuation/supervisor-state.json',source)
        d=self.simple();self.assertTrue(d['focus_acknowledged']);self.assertIn('核对MP',d['scope_notice'])
        self.assertNotIn('skill已加载',d['scope_notice'])
        source['benchmark_mapping']=dict(source['benchmark_mapping'],Grasp='simple/Other-v0');self.write('codex-account-2/continuation/supervisor-state.json',source)
        self.assertFalse(self.simple()['focus_acknowledged'])

    def test_get_projection_has_no_model_or_queue_and_keeps_media_functions(self):
        self.old_states();self.pause();self.add('xmovebendpick-campaign',self.mapping['mapping']['XMoveBendPick'],closed=False)
        with patch('subprocess.run') as calls:d=self.d.snapshot(force=True);calls.assert_not_called()
        row=next(x for x in d['tasks'][0]['subtasks'] if x['name']=='XMoveBendPick')
        self.assertEqual(row['episode'],'episode-0003');self.assertNotEqual(row['state'],'complete')

    def test_actual_current_scope_status_is_registered_but_not_ack_or_skill_load(self):
        self.write('codex-account-2/continuation/supervisor-state.json',{'status':'continue','current_scope':self.mapping['mapping']})
        d=self.simple();self.assertTrue(d['focus_scope_registered']);self.assertFalse(d['focus_acknowledged'])
        self.assertIn('主管公开状态已登记',d['scope_notice']);self.assertIn('加载仍未上报',d['scope_notice'])

if __name__=='__main__':unittest.main(verbosity=2)
