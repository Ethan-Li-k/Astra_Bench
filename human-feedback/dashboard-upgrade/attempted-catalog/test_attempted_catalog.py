"""Isolated source/media fixtures; no production feedback, queue, models or actors."""
import copy,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dashboard import Dashboard,RSI,CAMPAIGNS,OVEN_TASK
from feedback_board import FeedbackBoard
from store import digest,immutable
OUT=RSI/'human-feedback/dashboard-upgrade/attempted-catalog'
AUDIT='artifacts/R019/campaign_audit.json'
NT='artifacts/R019/nt-audit-integration-20260916/status.json'
BUDGET='artifacts/R019/door-campaign/episode-0019/policy_instruction_budget.json'
class AttemptedCatalogTests(unittest.TestCase):
    def setUp(self):self.root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));self.d=Dashboard(self.root);self.campaigns=[]
    def write(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
    def audit(self):self.write(AUDIT,{'campaigns':self.campaigns})
    def add(self,key,task=None,actions=2,closed=True,score=None):
        task=task or 'simple/G1'+key.title()+'Teleop-v0';base=f'artifacts/R019/{key}-campaign';ep='episode-0001'
        if closed:self.write(base+'/'+ep+'/result.json',{'actions':actions,'success':True,'native_outcome':'success'})
        else:self.write(base+'/'+ep+'/rollout/episode/execution_0001.json',{'receipts':[{'command_id':'fixture','duration_s':1}] if actions else []})
        c={'campaign':base,'task':task,'physical_attempts':1 if actions else 0,'required_successes':1,'episodes':[{'episode_id':ep,'physical_attempt':actions>0,'actions':actions}]}
        if score is not None:c['audited_task_successes']=score
        self.campaigns.append(c);self.audit();return c
    def rows(self):return self.d.simple()['subtasks']
    def test_three_new_tasks_and_original_six_order_scores(self):
        for key,(_,folder,goal) in CAMPAIGNS.items():
            task=OVEN_TASK if key=='oven' else 'simple/G1Fixture-v0'
            self.write(f'artifacts/R019/{folder}/progress.json',{'task':task,'successes':1,'required_successes':goal});self.write(f'artifacts/R019/{folder}/episode-0001/result.json',{'actions':1})
        self.add('trashcan','simple/G1WholebodyOpenTrashCanTeleop-v0',score=1)
        self.add('chair','simple/G1WholebodyPushOfficeChairTeleop-v0',closed=False,score=0)
        self.add('xmovebendpick','simple/G1WholebodyXMoveBendPickTeleop-v0',closed=False,score=0)
        rows=self.rows();self.assertEqual([x['id'] for x in rows[:6]],list(CAMPAIGNS));self.assertEqual([x['success'] for x in rows[:6]],[1]*6)
        self.assertEqual({x['id'] for x in rows[6:]},{'trashcan','chair','xmovebendpick'});self.assertEqual(next(x for x in rows if x['id']=='chair')['name'],'办公椅')
    def test_normal_poll_discovers_future_name_without_code_or_restart(self):
        self.d.snapshot();task='simple/G1FutureMechanismTeleop-v2';self.add('future',task)
        rows=self.d.snapshot(force=True)['tasks'][0]['subtasks'];row=next(x for x in rows if x['id']=='future');self.assertEqual(row['name'],task);self.assertIsNone(row['success']);self.assertNotEqual(row['state'],'complete')
    def test_preflight_empty_reset_or_counter_without_actions_rejected(self):
        self.add('preflight',actions=0);self.add('emptyreset',actions=0,closed=False)
        c=self.add('claimed',closed=False);self.write(c['campaign']+'/episode-0001/rollout/episode/execution_0001.json',{'receipts':[]})
        self.assertEqual(len(self.rows()),5)
        self.write(c['campaign']+'/episode-0001/rollout/episode/execution_0001.json',{'receipts':[{'command_id':'admitted','duration_s':0}]});self.assertEqual(len(self.rows()),5)
    def test_invalid_noncanonical_external_and_nested_paths_rejected(self):
        template=self.add('safe');base=template['campaign'];self.campaigns=[]
        for path in ['../safe-campaign','artifacts/R019/../R019/safe-campaign','artifacts/R019//safe-campaign','artifacts/R019/./safe-campaign','artifacts/R019/safe-campaign/child','/etc/safe-campaign',str(self.root/'elsewhere/safe-campaign'),'artifacts/R019/UPPER-campaign','artifacts/R019/foo_bar-campaign','artifacts/R019/safe-campaign/']:
            self.campaigns.append(dict(template,campaign=path))
        self.audit();self.assertEqual(len(self.rows()),5)
        self.campaigns=[dict(template,campaign=str(self.root/base))];self.audit();self.assertIn('safe',[x['id'] for x in self.rows()])
    def test_symlink_campaign_episode_and_receipt_rejected(self):
        c=self.add('linked');p=self.root/c['campaign'];destination=self.root/'elsewhere';p.rename(destination);p.symlink_to(destination);self.assertEqual(len(self.rows()),5)
        self.campaigns=[];c=self.add('episode-link');p=self.root/c['campaign']/'episode-0001';dest=self.root/'elsewhere-episode';p.rename(dest);p.symlink_to(dest);self.assertEqual(len(self.rows()),5)
        self.campaigns=[];c=self.add('receipt-link');p=self.root/c['campaign']/'episode-0001/result.json';dest=self.root/'elsewhere-result.json';p.rename(dest);p.symlink_to(dest);self.assertEqual(len(self.rows()),5)
    def test_task_mismatch_and_id_collision_rejected_unknown_goal_preserved(self):
        c=self.add('mismatch');self.write(c['campaign']+'/progress.json',{'task':'simple/G1Different-v0'})
        c=self.add('shellname','simple/G1Task$(touch_command)-v0');self.add('boxpick')
        c=self.add('unknown-goal');c.pop('required_successes');self.audit();rows=self.rows();self.assertEqual([x['id'] for x in rows[5:]],['unknown-goal']);self.assertIsNone(rows[-1]['goal']);self.assertIsNone(rows[-1]['success'])
    def test_closed_result_overrides_wait_and_manifest_media_not_followed(self):
        c=self.add('finished');self.write(c['campaign']+'/episode-0001/public-progress.json',{'state':'inference_waiting','current_problem':'stale waiting','next_step':'replay old action'})
        c['episodes'][0].update(video='/etc/passwd',result_path='../api.json');self.audit();d=self.rows()[-1];self.assertEqual(d['state'],'review');self.assertNotIn('stale',d['problem']);self.assertNotIn('replay',d['next']);self.assertEqual(d['videos'],[])
    def test_dynamic_case_media_cold_start_and_cross_episode_rejection(self):
        task='simple/G1FutureMechanism-v0';c=self.add('newmechanism',task);c['episodes']=[]
        case={'case_id':'HC-dynamic-fixture','task_id':'simple','title':'合成问题','mechanism':'fixture-mechanism','control_version':'fixture-v1','question':'哪个公开画面支持包夹？','choices':['A','B'],'facts':'合成事实','hypothesis':'合成假设','already_tried':'三次独立reset','unresolved':True,'attempts':[]}
        for i in range(1,4):
            ep=f'episode-{i:04d}';base=Path(c['campaign'])/ep;v=self.root/base/'video/episode.mp4';v.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(RSI/'ikea/diagnostics/door-v1-001/video/episode.mp4',v)
            p=self.write(str(base/'result.json'),{'actions':2,'terminal_kind':'physical_failure','human_feedback_used':False})
            self.write(str(base/'failure_review.json'),{'reset':{'reset_id':f'reset-{i}'},'independent_reset_verified':True,'no_replay_or_diagnostic_initial_state':True,'mechanism':'fixture-mechanism','control_version':'fixture-v1'})
            frame=self.root/base/'rollout/episode/observations/0001/head_stereo_left.png';frame.parent.mkdir(parents=True);frame.write_bytes(b'\x89PNG\r\n\x1a\n'+b'fixture'*20+b'\x00\x00\x00\x00IEND\xaeB`\x82');os.utime(frame,ns=(1789550000000000000,1789550000000000000));self.write(str(base/'rollout/episode/observations/0001/observation.json'),{'sim_s':1})
            c['episodes'].append({'episode_id':ep,'physical_attempt':True,'actions':2})
        self.audit();self.d.snapshot()
        for i in range(1,4):
            rid=f'simple/newmechanism/episode-{i:04d}';e=self.d.case_media(rid);rec=self.d.records[rid];case['attempts'].append({'record_id':rid,'result_sha256':rec['result_sha256'],'reset_id':rec['reset_id'],'video_url':e['video']['url'],'keyframe_url':e['preview']['url'],'timestamps':[1],'change':'synthetic','outcome':'failed'})
        cold=Dashboard(self.root);cold.snapshot();b=FeedbackBoard(cold,self.root/'feedback',fixture=True)
        self.assertIsNone(cold.media_file(case['attempts'][0]['video_url']));immutable(b.root/'cases'/(case['case_id']+'.json'),case);self.assertEqual(b.cases()['eligible_count'],1)
        for field in ('video_url','keyframe_url'):
            wrong=copy.deepcopy(case);wrong['attempts'][0][field]=case['attempts'][1][field]
            with self.assertRaisesRegex(ValueError,'another episode'):b.validate_case(wrong)
        with patch('subprocess.run') as call:cold.snapshot(force=True);call.assert_not_called()
    def nt(self,recovered=False):
        self.write(NT,{'candidate':'NT-AUDIT-20260916-v1','state':'published_tests_passed_pending_formal_boundary','publisher_tests_passed':63,'physical_network_recovery_verified':recovered,'files':[{'path':p,'after_sha256':'a'*64} for p in ('rsi/codex_app_server.py','tools/learn_grasp_skill.py','tools/audit_simple_campaigns.py')]})
    def load(self):self.write(BUDGET,{'contract':'skill-plus-runtime-v1','network_continuation':'Observe; next_call: ','developer_instructions_sha256':'b'*64})
    def test_new_publisher_overrides_old_partial_and_candidate(self):
        self.write('artifacts/architecture-review-20260916/no-truncation/progress.json',{'state':'complete_candidate_only','candidate_applied':False,'summary':'OLD_CANDIDATE'})
        self.write('artifacts/R019/instruction-cap-integration/status.json',{'applied':['ARCH-REVIEW-20260916-V1'],'NT-20260916-v1':{'accepted_and_applied':'Unbounded turn/start ACK wait and uncertain-submit guard'},'shared_core_changed':False})
        self.nt();self.load();d=self.d.framework();self.assertEqual(d['state_label'],'续接审计已发布；门19已加载；真实断线恢复尚未验证');body=json.dumps(d,ensure_ascii=False)
        self.assertNotIn('待中间回执与逐 turn 审计兼容',body);self.assertNotIn('完整自动网络续接未上线',body);self.assertIn('63项通过',body);self.assertIn('未晋升',body);self.assertNotEqual(d['state'],'complete')
    def test_published_loaded_and_recovery_independent(self):
        self.nt();d=self.d.framework();self.assertTrue(d['nt_publication']['published']);self.assertFalse(d['nt_publication']['door19_loaded']);self.assertIn('加载尚未确认',d['state_label'])
        self.load();self.write('artifacts/R019/door-campaign/episode-0019/result.json',{'actions':99,'success':True});d=self.d.framework();self.assertTrue(d['nt_publication']['door19_loaded']);self.assertFalse(d['nt_publication']['physical_network_recovery_verified'])
        self.nt(True);d=self.d.framework();self.assertTrue(d['nt_publication']['physical_network_recovery_verified']);self.assertIn('发布者已报告',d['state_label'])
        self.nt(None);self.assertIn('验证未上报',self.d.framework()['state_label'])
    def test_missing_or_wrong_loading_contract_not_invented(self):
        self.nt();self.write(BUDGET,{'contract':'old','network_continuation':'x','developer_instructions_sha256':'b'*64});self.assertFalse(self.d.framework()['nt_publication']['door19_loaded'])
        self.write(NT,{'candidate':'NT-AUDIT-20260916-v1','state':'candidate_only','publisher_tests_passed':63});self.load();self.assertNotIn('nt_publication',self.d.framework())
    def test_permission_formal_physical_evidence_is_separate_and_public_only(self):
        self.write('artifacts/R019/recovery-20260916/permission-contract-fix.json',{'status':'published_and_verified_on_formal_physical_actions'})
        p='artifacts/R019/recovery-20260916/permission-physical-route-verification.json';self.write(p,[{'first_physical_action_observed':True,'observed_actions':2,'sandbox':{'type':'workspaceWrite'},'approvalPolicy':'on-request','approvalsReviewer':'auto_review','boot_id':'PRIVATE_BOOT_SENTINEL','codex_home':'PRIVATE_AUTH_PATH'}])
        with patch('subprocess.run') as run:d=self.d.framework();run.assert_not_called()
        body=json.dumps(d,ensure_ascii=False);self.assertIn('已在正式物理动作验证；1份公开路由回执',body);self.assertNotIn('PRIVATE_BOOT_SENTINEL',body);self.assertNotIn('PRIVATE_AUTH_PATH',body)
if __name__=='__main__':unittest.main(verbosity=2)
