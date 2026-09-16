"""Isolated public-source fixtures. No model, actor, queue or production writes."""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'human-feedback/tools'))
from dashboard import Dashboard, SIX_TASKS

class LiveProgress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fixture-', dir=Path(__file__).parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.d = Dashboard(self.root)
        self.write('artifacts/architecture-review-20260916/six-task-focus/benchmark-mapping-evidence.json', {'mapping': SIX_TASKS})
        self.catalog = []
        self.native = SIX_TASKS['XMovePick']
        self.old = self.episode('xmovepick', 4, self.native, 48, sealed=True)
        self.declare('xmovepick', self.native, [4])
        self.write('artifacts/R019/xmovepick-campaign/progress.json', {'task':self.native, 'successes':1, 'episodes':{'episode-0004':{'actions':48}}})
        # Video validation is independently covered; this fixture pins selection to a closed result.
        self.addCleanup(patch.stopall)
        patch.object(Dashboard, 'completed_video', lambda d,p,k,ref,label: {'episode':p.name,'url':'/media/'+k+'-'+p.name+'.mp4','at':ref['at']} if ref else None).start()

    def write(self, rel, value, at=1789564000):
        p=self.root/rel; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(value));os.utime(p,(at,at));return p

    def declare(self, key, native, ids):
        self.catalog.append({'campaign':'artifacts/R019/'+key+'-campaign','task':native,'physical_attempts':len(ids),
          'episodes':[{'episode_id':f'episode-{n:04d}','physical_attempt':True,'actions':1,'completion_contract':'native_simple_criterion'} for n in ids]})
        self.write('artifacts/R019/campaign_audit.json',{'campaigns':self.catalog})

    def episode(self, key, n, native, actions, sealed=False):
        rel=f'artifacts/R019/{key}-campaign/episode-{n:04d}'
        self.write(rel+'/video/scene_setup.json',{'env_id':native,'variant':'native','pd_profile':'checkpoint','human_feedback_used':False,
          'reset_provenance':{'method':'fresh_environment_reset','reset_id':key+str(n),'recorded_utc':'2026-09-16T13:00:00Z'}},1789564000+n)
        self.write(rel+'/policy_instruction_budget.json',{'skill_sha256':'a'*64,'runtime_sha256':'b'*64})
        if actions:self.action(rel,actions,1789564100+n)
        if sealed:
            self.write(rel+'/result.json',{'actions':actions,'native_outcome':'success','stop_reason':'native_success','starting_skill_sha256':'a'*64,'human_feedback_used':False,'completion_contract':'native_simple_criterion'})
            self.write(rel+'/success_review.json',{'task':native,'audited_task_success':False,'full_turn_and_skill_update':True,'turn_record_integrity':'complete_terminal_sequence'})
        return rel

    def action(self, rel, n, at):
        self.write(rel+f'/rollout/episode/execution_{n:04d}.json',{'receipts':[{'command_id':'fixture-'+str(n),'duration_s':1,'status':'target_reached'}]},at)
        obs=rel+f'/rollout/episode/observations/{n:04d}'
        self.write(obs+'/observation.json',{'sim_s':n},at)
        p=self.root/obs/'head_cam.png';p.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB9kAAAAASUVORK5CYII='));os.utime(p,(at,at))

    def target(self,name='XMovePick'):
        return next(t for t in self.d.simple()['subtasks'] if t['name']==name)

    def test_stale_summary_cannot_hide_new_episode_or_new_action(self):
        new=self.episode('xmovepick',5,self.native,15)
        t=self.target();self.assertEqual(t['episode'],'episode-0005');self.assertEqual(t['actions'],15)
        self.assertEqual(t['preview']['action'],15);self.assertIn('episode-0005',t['preview']['url'])
        self.assertEqual(t['videos'][0]['episode'],'episode-0004');self.assertEqual(t['scorecard']['dispositions']['inflight'],1)
        self.assertEqual(t['scorecard']['current']['native']['denominator'],1)
        self.action(new,16,1789564300);t=self.target();self.assertEqual(t['actions'],16);self.assertEqual(t['last_action_at'],1789564300)
        self.assertEqual(t['preview']['action'],16);self.assertFalse(t['scorecard']['stability']['registered'])

    def test_empty_reset_invalid_receipt_and_conflicting_native_excluded(self):
        self.episode('xmovepick',5,self.native,15)
        self.episode('xmovepick',6,self.native,0)
        self.write('artifacts/R019/xmovepick-campaign/episode-0006/rollout/episode/execution_0099.json',{'response':'not execution'},1789569999)
        self.episode('xmovepick',7,SIX_TASKS['Handover'],5)
        self.assertEqual(self.target()['episode'],'episode-0005')

    def test_latest_physical_receipt_not_invalid_higher_filename(self):
        new=self.episode('xmovepick',5,self.native,15)
        self.write(new+'/rollout/episode/execution_0999.json',{'receipts':[]},1789569999)
        self.assertEqual(self.target()['actions'],15)

    def test_mobile_exact_entry_and_owner_ack_first_attempt(self):
        self.declare('mobilecheezit','simple/G1WholebodyLocomotionPickCheezitTeleop-v0',[1])
        self.episode('mobilecheezit',1,'simple/G1WholebodyLocomotionPickCheezitTeleop-v0',5,True)
        self.assertIsNone(self.target('Mobile P&P')['episode'])
        self.write('artifacts/R019/six-task-focus/supervisor-ack.json',{'ack':'SIX-TASK-FOCUS-20260916 ACK','mapping':SIX_TASKS,'owner_thread':'01a0a867-d7aa-71f2-8547-e264d6d09ede','campaign_families':{'mobiletables-campaign':'Mobile P&P'}})
        self.episode('mobiletables',1,SIX_TASKS['Mobile P&P'],23)
        t=self.target('Mobile P&P');self.assertEqual(t['episode'],'episode-0001');self.assertEqual(t['actions'],23)
        self.assertEqual(t['scorecard']['current']['native']['denominator'],0)

    def test_public_phase_must_follow_action_and_terminal_wins(self):
        new=self.episode('xmovepick',5,self.native,15)
        self.write(new+'/public-progress.json',{'native_env_id':self.native,'state':'inference_waiting','current_problem':'旧等待'},1789564000)
        t=self.target();self.assertEqual(t['state'],'active-unknown');self.assertNotEqual(t['problem'],'旧等待')
        self.write(new+'/public-progress.json',{'native_env_id':self.native,'state':'inference_waiting','current_problem':'等待同回合完整推理','next_step':'收到当前回复后继续'},1789564200)
        t=self.target();self.assertEqual(t['state'],'modelwaiting');self.assertEqual(t['problem'],'等待同回合完整推理')
        self.episode('xmovepick',5,self.native,15,True)
        self.assertEqual(self.target()['state'],'review')

    def test_handover_native_success_is_not_complete_success(self):
        native=SIX_TASKS['Handover'];self.declare('handover',native,[1]);e=self.episode('handover',1,native,47,True)
        self.write(e+'/success_review.json',{'task':native,'audited_task_success':False,'native_success':True,'full_turn_and_skill_update':True,'turn_record_integrity':'complete_terminal_sequence',
          'classification':'native_success_rejected_by_task_audit','independently_verified_stages':{'right_unsupported_hold':{'samples':75},'giver_clear_left_unsupported_hold':{'samples':76},'release_and_supported_destination_placement':False},'host_only_question':'POISON'})
        self.episode('handover',2,native,6)
        t=self.target('Handover');self.assertIn('未完成释放放置',t['recent_audit_note']);self.assertEqual(t['scorecard']['current']['native']['numerator'],1)
        self.assertEqual(t['scorecard']['current']['semantic']['numerator'],0);self.assertNotIn('POISON',json.dumps(t))

    def test_central_publication_separate_from_physical_load(self):
        base='artifacts/architecture-review-20260916/central-skill-publication/'
        self.write(base+'progress.json',{'published':False,'first_load_confirmed':False})
        self.write(base+'publication-receipt.json',{'status':'published','pointer':{'release_id':'central-test-v1','manifest_sha256':'c'*64},'shared_runner_integrated':True,'first_physical_load_confirmed':False})
        self.write(base+'runtime-integration-receipt.json',{'status':'integrated_for_next_launch','first_physical_load_confirmed':False})
        self.write(base+'first-load-status.json',{'release_sha256':'c'*64,'actual_actor_load_confirmed':False,'status':'pending_supervisor_natural_boundary'})
        d=self.d.simple()['benchmark_plan']['learning_runtime'];self.assertTrue(d['source_published']);self.assertFalse(d['physical_load_confirmed']);self.assertIn('待确认',d['note'])
        self.write(base+'first-load-status.json',{'release_sha256':'d'*64,'actual_actor_load_confirmed':True})
        self.assertIsNone(self.d.simple()['benchmark_plan']['learning_runtime']['physical_load_confirmed'])

    def test_campaign_and_episode_symlinks_rejected(self):
        e=self.root/'artifacts/R019/xmovepick-campaign/episode-0005';e.symlink_to(self.root/self.old,target_is_directory=True)
        self.assertEqual(self.target()['episode'],'episode-0004')
        (self.root/'artifacts/R019/mobiletables-campaign').symlink_to(self.root/'artifacts/R019/xmovepick-campaign',target_is_directory=True)
        self.write('artifacts/R019/six-task-focus/supervisor-ack.json',{'ack':'SIX-TASK-FOCUS-20260916 ACK','mapping':SIX_TASKS,'owner_thread':'01a0a867-d7aa-71f2-8547-e264d6d09ede',
          'campaign_families':{'mobiletables-campaign':'Mobile P&P','../outside-campaign':'Mobile P&P','/tmp/outside-campaign':'Mobile P&P','bad-campaign':{}}})
        self.assertIsNone(self.target('Mobile P&P')['episode'])

if __name__=='__main__': unittest.main(verbosity=2)
