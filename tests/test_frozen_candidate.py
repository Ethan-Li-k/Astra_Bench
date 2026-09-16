"""Full public input pinning and ordered admission; no model or physics calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rsi.skill_learning import SkillMemory
from rsi.frozen_skill import (snapshot_sources, seal_candidate, verify_candidate,
    claim_episode, file_hashes, record_episode_audit)

ROOT=Path(__file__).resolve().parents[1]
SKILL='---\nname: loco-manip-direct\ndescription: fixture\n---\nRead current RGB.\n'

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'artifacts/R018/tmp')
        self.root=Path(self.temp.name)
        skill=self.root/'SKILL.md';skill.write_text(SKILL)
        self.memory=SkillMemory(self.root/'memory',skill)
        self.candidate=self.root/'candidate';self.candidate.mkdir()
        self.code=self.root/'runtime.py';self.code.write_text('# fixed fixture\n')
        self.options={'continuous_chunks':True}
    def tearDown(self):self.temp.cleanup()
    def seal(self):
        snapshot_sources(self.memory,{'task_current_skill':{'path':str(self.memory.skill)}},self.candidate/'public')
        deps={k:[self.code] for k in ('runtime','retrieval','assets','controller','camera','task','model_route')}
        return seal_candidate(self.candidate,task_id='exact',task_specification={'env_id':'exact'},
            task_text='fixture task',options=self.options,dependencies=deps,
            stability_seeds=list(range(5)),evaluation_seeds=list(range(20,30)),
            audit_contract={'native':'native criterion','independent':'retained grasp','terminal_hold':'no invented post-stop dwell'})
    def claim(self,**kwargs):
        args=dict(task_id='exact',options=self.options,phase='stability',seed=0,episode=self.root/'episode-0001')
        return claim_episode(self.candidate,**(args|kwargs))
    def test_snapshot_rewrites_local_evidence_and_excludes_audit(self):
        rollout=self.root/'episode-0000/rollout';rollout.mkdir(parents=True)
        proof=rollout/'history.jsonl';proof.write_text('{}\n')
        (rollout.parent/'success_review.json').write_text('{"hidden": true}')
        self.memory.update(SKILL,'lesson',[proof],rollout,'episode-0000','failure')
        sources={'task_current_skill':{'path':str(self.memory.skill)},'task_experience':{'path':str(self.memory.journal)}}
        pinned=snapshot_sources(self.memory,sources,self.candidate/'public')
        self.assertNotIn(str(proof),(self.candidate/'public/local/memory/experience.jsonl').read_text())
        row=json.loads((self.candidate/'public/local/memory/experience.jsonl').read_text())
        self.assertTrue(Path(row['evidence_paths'][0]).is_file())
        self.assertIn(str(self.candidate/'public'),pinned['task_current_skill']['path'])
        self.assertFalse(list((self.candidate/'public').rglob('success_review.json')))
    def test_added_evaluation_lesson_or_changed_runtime_rejects_before_claim(self):
        self.seal();self.code.write_text('# drift\n')
        with self.assertRaisesRegex(ValueError,'dependency changed'):self.claim()
        self.assertFalse((self.candidate/'registrations').exists())
        self.code.write_text('# fixed fixture\n')
        (self.candidate/'public/new_evaluation_lesson.md').write_text('leak')
        with self.assertRaisesRegex(ValueError,'read set'):self.claim()
    def test_wrong_exact_task_option_or_seed_rejected(self):
        self.seal()
        for arguments in ({'task_id':'nearby'},{'options':{'continuous_chunks':False}},{'seed':1}):
            with self.subTest(arguments=arguments),self.assertRaises(ValueError):self.claim(**arguments)
    def test_order_is_exclusive_and_cannot_skip_unresolved_episode(self):
        manifest=self.seal();row=self.claim()
        self.assertEqual(row['candidate_sha256'],manifest['candidate_sha256'])
        with self.assertRaisesRegex(ValueError,'unresolved'):self.claim(seed=1,episode=self.root/'episode-0002')
        self.assertEqual(len(list((self.candidate/'registrations').glob('*.json'))),1)
    def test_evaluation_before_five_and_manifest_tamper_rejected(self):
        self.seal()
        with self.assertRaisesRegex(ValueError,'Five consecutive'):self.claim(phase='evaluation',seed=20)
        path=self.candidate/'manifest.json';data=json.loads(path.read_text());data['task_id']='nearby';path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'manifest was modified'):verify_candidate(self.candidate)
    def test_empty_dependency_category_rejected(self):
        snapshot_sources(self.memory,{},self.candidate/'public')
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            seal_candidate(self.candidate,task_id='exact',task_specification={'env_id':'exact'},task_text='x',options={},dependencies={},stability_seeds=[0],evaluation_seeds=list(range(20,30)),audit_contract={})
    def complete_fixture(self,registration,reset_id):
        episode=Path(registration['episode']);(episode/'video').mkdir(parents=True)
        (episode/'protocol-registration.json').write_text(json.dumps(registration))
        (episode/'result.json').write_text(json.dumps({'protocol_registration':registration,'error':None}))
        (episode/'video/scene_setup.json').write_text(json.dumps({'env_id':'exact','reset_provenance':{
            'method':'fresh_environment_reset','seed':registration['seed'],'reset_id':reset_id,'recorded_utc':'2099-01-01T00:00:00+00:00'}}))
        (episode/'frozen-input-verification.json').write_text(json.dumps({'candidate_sha256':registration['candidate_sha256'],'unchanged_after_turn':True}))
        status=dict(host_success_complete=True,task_audit_status='passed',full_turn_completed=True,
            skill_updated=True,reset_id=reset_id,physical_attempt=True,native_outcome='success',
            audited_task_success=True,termination_class='native_success')
        with patch('tools.audit_simple_campaigns.episode_status',return_value=status):
            return record_episode_audit(self.candidate,episode)
    def test_legal_five_bound_outcomes_admit_only_first_evaluation_seed(self):
        self.seal()
        for i in range(5):
            row=self.claim(seed=i,episode=self.root/f'episode-{i:04d}')
            self.complete_fixture(row,f'unique-reset-{i}')
        with self.assertRaisesRegex(ValueError,'order'):self.claim(phase='evaluation',seed=21,episode=self.root/'evaluation')
        row=self.claim(phase='evaluation',seed=20,episode=self.root/'evaluation')
        self.assertEqual(row['phase'],'evaluation')
    def test_reused_physical_reset_cannot_be_recorded_twice(self):
        self.seal();self.complete_fixture(self.claim(),'reset1')
        row=self.claim(seed=1,episode=self.root/'episode-0002')
        with self.assertRaisesRegex(ValueError,'Repeated physical reset'):self.complete_fixture(row,'reset1')
    def test_modified_audited_evidence_blocks_next_admission(self):
        self.seal();row=self.claim();self.complete_fixture(row,'reset1')
        (Path(row['episode'])/'result.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.claim(seed=1,episode=self.root/'episode-0002')

if __name__=='__main__':unittest.main()
