"""Source-sync fixtures only. No queue delivery, model, robot or production feedback."""
import json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dashboard import Dashboard,RSI,OVEN_TASK
OUT=RSI/'human-feedback/dashboard-upgrade/publisher-sync'
PUB='artifacts/R019/instruction-cap-integration/status.json'
AUDIT='artifacts/R019/campaign_audit.json'
class PublisherSyncTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));self.d=Dashboard(self.root)
    def write(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
    def fixture_publisher(self):
        self.write('artifacts/architecture-review-20260916/no-truncation/progress.json',{'updated_utc':100,'candidate_applied':False,'state':'bounded_review_completed_candidate_delivered','summary':'旧候选全未部署','tests_passed':18})
        self.write(PUB,{'updated_utc':200,'applied':['ARCH-REVIEW-20260916-V1','ARCH-MEMORY-PRIORITY-20260916-V1','mujoco-render-frustum-v1'],'NT-20260916-v1':{'accepted_and_applied':'Unbounded turn/start ACK wait and uncertain-submit guard','pending':'Automatic confirmed-closed network turn continuation'},'shared_core_changed':False,'complete_physical_validation':{'door':{'episode':str(self.root/'artifacts/R019/door-campaign/episode-0016'),'audited_task_success':True,'host_review':'HOST_PRIVATE_SENTINEL','host_payload':'DO_NOT_PUBLISH'},'faucet':{'episode':str(self.root/'artifacts/R019/faucet-campaign/episode-0008'),'audited_task_success':True}}})
    def oven(self,actions=14):
        base='artifacts/R019/oven-campaign/episode-0001';self.write(base+'/result.json',{'actions':actions,'success':True,'native_outcome':'success','stop_reason':'native_success'});return base
    def test_publisher_overrides_old_candidate_without_all_complete(self):
        self.fixture_publisher();d=self.d.framework();body=json.dumps(d,ensure_ascii=False)
        self.assertIn('SIMPLE 分项已上线',d['state_label']);self.assertIn('NT 部分上线',d['state_label']);self.assertNotEqual(d['state'],'complete');self.assertNotIn('旧候选全未部署',body)
        for name in ['ARCH 组合长度','MEMORY-PRIORITY 检索','相机标定','未晋升','自动续接仍待审计兼容']:self.assertIn(name,body)
        self.assertIn('门16、水龙头8',body);self.assertIn('不能证明单项收益或泛化',body)
        self.assertEqual(d['source_at'],200)
    def test_nested_host_audit_and_source_payload_never_projected(self):
        self.fixture_publisher()
        with patch('subprocess.run') as run:body=json.dumps(self.d.framework());run.assert_not_called()
        for secret in ['HOST_PRIVATE_SENTINEL','DO_NOT_PUBLISH','host_review','source_sha256']:self.assertNotIn(secret,body)
    def test_compat_candidate_does_not_publish_network_continuation(self):
        self.fixture_publisher();self.write('artifacts/architecture-review-20260916/no-truncation/audit-compat/result.json',{'state':'complete_candidate_only','candidate_deployed':False,'tests_passed':12})
        d=self.d.framework();body=json.dumps(d,ensure_ascii=False);self.assertIn('完整自动网络续接未上线',body);self.assertIn('兼容候选已离线交付，待发布者审查',body);self.assertIn('NT 部分上线',d['state_label'])
    def test_permission_fix_is_next_boundary_only(self):
        self.fixture_publisher();self.write('artifacts/R019/recovery-20260916/permission-contract-fix.json',{'updated_utc':300,'status':'published_for_next_reset; actual model-free handshake verified','in_flight_unchanged':['door17']})
        d=self.d.framework();self.assertIn('供下一新 reset',json.dumps(d,ensure_ascii=False));self.assertIn('不热改',json.dumps(d,ensure_ascii=False));self.assertEqual(d['source_at'],300)
    def test_missing_publisher_and_unknown_flags_stay_unknown(self):
        self.assertEqual(self.d.framework()['state'],'unknown')
        self.write(PUB,{'updated_utc':200,'status':'unknown','applied':[]});self.assertNotIn('已上线',self.d.framework()['state_label'])
    def test_oven_requires_physical_attempt_and_keeps_five_order(self):
        expected=['door','apple','faucet','boxpick','boxplace']
        (self.root/'artifacts/R019/oven-campaign/episode-0001').mkdir(parents=True)
        self.assertEqual([x['id'] for x in self.d.simple()['subtasks']],expected)
        self.oven(0);self.assertEqual([x['id'] for x in self.d.simple()['subtasks']],expected)
        self.oven(14);rows=self.d.simple()['subtasks'];self.assertEqual([x['id'] for x in rows],expected+['oven']);row=rows[-1]
        self.assertEqual(row['actions'],14);self.assertIsNone(row['success']);self.assertNotEqual(row['state'],'complete');self.assertIn('烤箱',row['name'])
    def test_native_success_pending_audit_not_scored_or_waiting(self):
        base=self.oven();self.write(base+'/public-progress.json',{'state':'inference_waiting','current_problem':'仍在生成陈旧标记','next_step':'继续执行旧动作'})
        self.write(AUDIT,{'campaigns':[{'campaign':'artifacts/R019/oven-campaign','task':OVEN_TASK,'audited_task_successes':0,'episodes':[{'episode_id':'episode-0001','state':'finished','native_outcome':'success','task_audit_status':'unknown'}]}]})
        d=self.d.simple()['subtasks'][-1];self.assertEqual(d['success'],0);self.assertEqual(d['state'],'review');self.assertNotIn('仍在生成',d['problem']);self.assertNotIn('继续执行旧动作',d['next']);self.assertIn('尚未确认',d['problem'])
    def test_audit_path_and_task_mismatch_do_not_inject_rows_or_scores(self):
        self.oven();rows=[{'campaign':'artifacts/R019/oven-campaign/../../outside','task':OVEN_TASK,'audited_task_successes':99},
            {'campaign':'/etc','task':OVEN_TASK,'audited_task_successes':99},
            {'campaign':'artifacts/R019/oven-campaign','task':'wrong-task','audited_task_successes':99},
            {'campaign':'artifacts/R019/never-attempted-campaign','task':'simple/G1NeverAttempted-v0','audited_task_successes':99}]
        self.write(AUDIT,{'campaigns':rows});d=self.d.simple();self.assertEqual(len(d['subtasks']),6);self.assertIsNone(d['subtasks'][-1]['success']);self.assertIsNone(self.d.media_file('/media/../../api.json'))
    def test_oven_symlink_not_allowed(self):
        outside=self.root/'unlisted';outside.mkdir();(self.root/'artifacts/R019').mkdir(parents=True);(self.root/'artifacts/R019/oven-campaign').symlink_to(outside)
        self.write('unlisted/episode-0001/result.json',{'actions':14,'success':True});self.assertEqual(len(self.d.simple()['subtasks']),5)
    def test_oven_media_seal_cache_newest_and_case_binding(self):
        base=self.oven();video=self.root/base/'video/episode.mp4';video.parent.mkdir(parents=True);shutil.copyfile(RSI/'ikea/diagnostics/door-v1-001/video/episode.mp4',video)
        self.write(base+'/result.json',{'actions':14,'stop_reason':'native_success'});row=self.d.simple()['subtasks'][-1];self.assertEqual(len(row['videos']),1);self.assertIsNotNone(self.d.media_file(row['videos'][0]['url']));self.assertIn('oven-campaign',row['videos'][0]['source'])
        with patch('dashboard.subprocess.run') as run:self.d.simple();run.assert_not_called()
        rid='simple/oven/episode-0001';ev=self.d.case_media(rid);self.assertEqual(ev['folder'],self.root/base)
        fresh='artifacts/R019/oven-campaign/episode-0002';new=self.root/fresh/'video/episode.mp4';new.parent.mkdir(parents=True);new.write_bytes(b'open mp4');self.write(fresh+'/rollout/episode/execution_0001.json',{'public':'action'})
        with patch('dashboard.subprocess.run') as run:row=self.d.simple()['subtasks'][-1];run.assert_not_called()
        self.assertEqual(row['episode'],'episode-0002');self.assertEqual(row['videos'][0]['episode'],'episode-0001')
        self.write(fresh+'/result.json',{'actions':1});row=self.d.simple()['subtasks'][-1];self.assertEqual(row['videos'][0]['episode'],'episode-0001')
    def test_public_campaign_and_progress_fields_same_episode_only(self):
        base=self.root/'artifacts/R019/oven-campaign/episode-0001';self.write(str(base.relative_to(self.root)/'rollout/episode/execution_0002.json'),{'action':'public'})
        self.write(AUDIT,{'campaigns':[{'campaign':'artifacts/R019/oven-campaign','task':OVEN_TASK,'current_problem':'公开任务卡点','next_step':'公开下一步'}]})
        d=self.d.simple()['subtasks'][-1];self.assertEqual(d['problem'],'公开任务卡点');self.assertEqual(d['next'],'公开下一步')
        self.write(AUDIT,{'campaigns':[]});p=self.root/'artifacts/R019/PROGRESS.md';p.write_text('- oven-campaign：审计成功 0/1；episode-0001，等待模型/工具；物理暂停，2动作；终态分类 running。最近物理日志 2026-09-16T10:20:00+00:00。\n')
        d=self.d.simple()['subtasks'][-1];self.assertIn('负责人进展摘要',d['problem']);self.assertIn('存活未独立核验',d['problem']);self.assertEqual(d['state'],'active-unknown')
        p.write_text(p.read_text().replace('episode-0001','episode-0000'));self.assertNotIn('负责人进展摘要',self.d.simple()['subtasks'][-1]['problem'])
if __name__=='__main__':unittest.main(verbosity=2)
