"""Bounded root review regressions. Isolated RSI fixtures; queue subprocess is stubbed."""
import copy,json,os,shutil,subprocess,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from dashboard import Dashboard,RSI,hash_json
from feedback_board import FeedbackBoard,OWNERS
from store import digest,immutable

OUT=RSI/'human-feedback/dashboard-upgrade/root-review'
class RootReviewTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));self.d=Dashboard(self.root)
    def write(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
    def door(self):return self.d.simple()['subtasks'][0]
    def test_unknown_does_not_infer_wait_death_or_next_reset(self):
        self.write('artifacts/R019/door-campaign/episode-0015/public-progress.json',{})
        row=self.door();self.assertEqual(row['state'],'active-unknown');self.assertIn('终态和执行状态未确认',row['problem']);self.assertIn('同回合续接',row['next']);self.assertNotIn('下一回合',row['next'])
    def test_handoff_is_labeled_and_newer_owner_overrides(self):
        path='artifacts/R019/door-campaign/episode-0015/public-progress.json'
        self.write(path,{'updated_at':100,'state':'inference_waiting'})
        self.write('human-feedback/dashboard-upgrade/root-simple-recovery-handoff.json',{'at':200,'state':'infrastructure_error','current_problem':'主机重启，原进程已失去。'})
        row=self.door();self.assertEqual(row['state'],'infraerror');self.assertIn('负责人报告',row['problem']);self.assertIn('主机重启',row['problem'])
        self.write(path,{'updated_at':300,'state':'action_executing','current_problem':'新负责人确认的状态','next_step':'同回合状态已核对'})
        row=self.door();self.assertEqual(row['state'],'physicsrunning');self.assertEqual(row['problem'],'新负责人确认的状态');self.assertEqual(row['next'],'同回合状态已核对')
    def test_new_episode_not_contaminated_by_old_interruption(self):
        self.write('artifacts/R019/door-campaign/episode-0016/public-progress.json',{})
        self.write('human-feedback/dashboard-upgrade/root-simple-recovery-handoff.json',{'at':200,'state':'infrastructure_error','current_problem':'旧门15重启中断'})
        self.write('artifacts/R019/recovery-20260916/door15-interruption.json',{'reviewed_utc':300,'termination_class':'infrastructure_interruption','last_ack':{'stop_reason':'episode_step_budget'}})
        row=self.door();self.assertEqual(row['state'],'active-unknown');self.assertIn('最后物理回执已到预算边界',row['recovery_note']);self.assertNotIn('重启中断',row['problem'])
    def test_budget_terminal_overrides_stale_public_inference(self):
        base='artifacts/R019/door-campaign/episode-0015/'
        self.write(base+'public-progress.json',{'state':'inference_waiting','current_problem':'预算后的公开分析','next_step':'只审查结果'})
        self.write(base+'result.json',{'stop_reason':'episode_step_budget'})
        self.assertEqual(self.door()['state'],'budgetstop')
    def test_public_short_fields_ground_ikea_and_framework(self):
        self.write('api-ground-to-table/actor-adapter/auxiliary-progress.json',{'current_problem':'搬运卡点','next_step':'搬运下一步'})
        self.write('ikea/web-progress.json',{'current_problem':'IKEA卡点','next_step':'IKEA下一步'})
        self.write('artifacts/architecture-review-20260916/no-truncation/progress.json',{'current_problem':'框架卡点','next_step':'框架下一步'})
        for row,label in [(self.d.ground(),'搬运'),(self.d.ikea(),'IKEA'),(self.d.framework(),'框架')]:
            self.assertEqual(row['problem'],label+'卡点');self.assertEqual(row['next'],label+'下一步')
        self.assertNotIn('待主控确认',self.d.ground()['delivery_note'])
    def test_ground_stale_wait_keeps_last_stage_but_liveness_unknown(self):
        self.write('api-ground-to-table/actor-adapter/auxiliary-progress.json',{'state':'inference_waiting_no_deadline','updated_at_unix':100,'run_id':'api-ground-002','episode':'episode-0002'})
        row=self.d.ground();self.assertEqual(row['state'],'modelwaiting');self.assertIn('当前存活未独立核验',row['problem'])
        self.write('api-ground-to-table/actor-adapter/auxiliary-progress.json',{'state':'infrastructure_error','stop_reason':'host_reboot_infrastructure_interruption','recovery_note':'负责人确认系统中断，未知调用不重发'})
        row=self.d.ground();self.assertEqual(row['state'],'infraerror');self.assertEqual(row['problem'],'负责人确认系统中断，未知调用不重发')
    def test_framework_newer_result_and_progress_replace_old_status(self):
        base='artifacts/architecture-review-20260916/no-truncation/'
        self.write(base+'status.json',{'updated_utc':100,'state':'reviewing','summary':'正在审查'})
        self.write(base+'result.json',{'completed_utc':200,'state':'complete_candidate_only','checks':{'focused':10,'existing_adapter':7,'actual_caller_fake_transport_backend':1},'delivery':{'queued':3,'acknowledged':0,'integrated':False}})
        self.write(base+'progress.json',{'updated_utc':300,'state':'bounded_review_completed_candidate_delivered','summary':'18项离线验证通过，候选已交付','candidate_applied':False,'tests_passed':18})
        row=self.d.framework();self.assertIn('待集成与物理验证',row['state_label']);self.assertNotIn('正在审查',row['summary']);self.assertNotEqual(row['state'],'complete');self.assertEqual(row['source_at'],300)
        self.assertIn('18项通过',json.dumps(row,ensure_ascii=False));self.assertIn('3个已排队；0个确认',json.dumps(row,ensure_ascii=False));self.assertTrue(any(x['path'].endswith('/result.json') for x in row['sources']))
    def test_prerequisite_separate_unknown_not_zero(self):
        self.assertIsNone(self.d.simple()['prerequisite_note'])
        self.write('artifacts/architecture-review-20260916/status-evidence.json',{'tasks':{'table_cube':{'verified':10,'physical_attempts':15,'endpoint_retained':5}}})
        row=self.d.simple();self.assertEqual(row['prerequisite_note'],'前置桌面抓取：10次原生成功（终态仍持有5次），学习成绩');self.assertEqual(len(row['subtasks']),5);self.assertIsNone(row['subtasks'][0]['success'])
    def ground_payload(self,board):
        task={'id':'ground','sources':[],'summary':'isolated fixture'};task['version']=hash_json(task);board.publish_packages([task])
        return {'request_id':'fixture_ground_owner','task_id':'ground','case_id':None,'source_version':task['version'],'text':'isolated synthetic text, never real user feedback','choice':'','user_timestamp':'2026-09-16T00:00:00Z','correction_of':None}
    def test_new_owner_provider_stub_and_no_historical_redelivery(self):
        self.assertEqual(OWNERS['ground'],'01a0a982-cec5-71c0-b771-091c31df61f2')
        b=FeedbackBoard(self.d,self.root/'feedback',fixture=False);payload=self.ground_payload(b)
        with patch('feedback_board.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'Queued fixture')) as call:
            answer=b.submit(payload)
            for _ in range(200):
                if (b.root/'delivery'/(answer['feedback_id']+'-result.json')).exists():break
                time.sleep(.01)
            argv=call.call_args.args[0];self.assertEqual(argv[argv.index('--thread')+1],OWNERS['ground']);self.assertIn('model_provider="openai"',argv);self.assertIn('model_reasoning_effort="xhigh"',argv);self.assertEqual(argv[1],'queue');self.assertNotIn('resume',argv);self.assertNotIn(payload['text'],argv[-1]);self.assertNotIn('shell',call.call_args.kwargs)
            self.assertIsNone(b.status(answer)['owner_ack']);b=FeedbackBoard(self.d,b.root,fixture=False);self.assertTrue(b.submit(payload)['duplicate']);self.assertEqual(call.call_count,1)
    def test_old_ack_stays_bound_to_saved_original_recipient(self):
        b=FeedbackBoard(self.d,self.root/'feedback',fixture=True);answer=b.submit(self.ground_payload(b));aid=answer['feedback_id'];sha=digest((b.root/'answers'/(aid+'.json')).read_bytes());old='01a0a948-10bb-7d03-8f1d-b1eeda7cb93c'
        immutable(b.root/'delivery'/(aid+'-message.json'),{'owner':old,'answer_sha256':sha})
        immutable(b.root/'acks'/(aid+'-old.json'),{'feedback_id':aid,'owner':old,'answer_sha256':sha,'stage':'owner_ack','note':'historical fixture'})
        with patch('feedback_board.subprocess.run') as call:self.assertIsNotNone(b.status(answer)['owner_ack']);call.assert_not_called()
    def case_fixture(self):
        c={'case_id':'HC-cold-fixture','task_id':'simple','title':'合成问题','mechanism':'grasp','control_version':'fixture-v1','question':'哪一帧包夹成立？','choices':['A','B'],'facts':'合成事实','hypothesis':'合成假说','already_tried':'三次独立物理尝试','unresolved':True,'attempts':[]}
        for i in range(1,4):
            base=f'artifacts/R019/apple-campaign/episode-{i:04d}';v=self.root/base/'video/episode.mp4';v.parent.mkdir(parents=True);shutil.copyfile(RSI/'ikea/diagnostics/door-v1-001/video/episode.mp4',v)
            frame=self.root/base/'rollout/episode/observations/0001/head_stereo_left.png';frame.parent.mkdir(parents=True);frame.write_bytes(b'\x89PNG\r\n\x1a\n'+b'fixture'*20+b'\x00\x00\x00\x00IEND\xaeB`\x82')
            os.utime(frame,ns=(1789550000000000000,1789550000000000000))
            self.write(base+'/rollout/episode/observations/0001/observation.json',{'sim_s':1})
            rp=self.write(base+'/result.json',{'terminal_kind':'physical_failure','actions':1,'human_feedback_used':False})
            self.write(base+'/failure_review.json',{'reset':{'reset_id':f'reset-{i}'},'independent_reset_verified':True,'no_replay_or_diagnostic_initial_state':True,'control_version':'fixture-v1','mechanism':'grasp'})
        self.d.snapshot()
        for i in range(1,4):
            rid=f'simple/apple/episode-{i:04d}';ev=self.d.case_media(rid);rec=self.d.records[rid]
            c['attempts'].append({'record_id':rid,'result_sha256':rec['result_sha256'],'reset_id':rec['reset_id'],'video_url':ev['video']['url'],'keyframe_url':ev['preview']['url'],'timestamps':[1],'change':'fixture','outcome':'failed'})
        return c
    def test_cold_start_publishes_three_bound_episode_media(self):
        c=self.case_fixture();cold=Dashboard(self.root);cold.snapshot();b=FeedbackBoard(cold,self.root/'feedback',fixture=True)
        self.assertIsNone(cold.media_file(c['attempts'][0]['video_url']));self.assertIsNone(cold.media_file(c['attempts'][0]['keyframe_url']))
        immutable(b.root/'cases'/(c['case_id']+'.json'),c)
        self.assertEqual(b.cases()['eligible_count'],1)
        for a in c['attempts']:
            self.assertIsNotNone(cold.media_file(a['video_url']));self.assertIsNotNone(cold.media_file(a['keyframe_url']))
    def test_registered_but_different_episode_media_rejected(self):
        c=self.case_fixture();b=FeedbackBoard(self.d,self.root/'feedback',fixture=True)
        for field in ('video_url','keyframe_url'):
            wrong=copy.deepcopy(c);wrong['attempts'][0][field]=c['attempts'][1][field]
            with self.assertRaisesRegex(ValueError,'another episode'):b.validate_case(wrong)

if __name__=='__main__':unittest.main(verbosity=2)
