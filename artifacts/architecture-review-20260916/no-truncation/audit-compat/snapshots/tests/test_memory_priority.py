"""Exercise actual SkillMemory and audit projection on isolated file fixtures."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TREE=ROOT/os.environ.get('MEMORY_PRIORITY_TREE','candidate')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

memory_module=load('review_memory',TREE/'rsi/skill_learning.py')
audit=load('review_audit',TREE/'tools/audit_simple_campaigns.py')
SKILL='---\nname: loco-manip-direct\ndescription: fixture\n---\nRead current public evidence.\n'
NATIVE='native_simple_criterion'
PLACEMENT='acquired-lift-then-released-container-support-v1'


class MemoryPriorityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'tests')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'boxplace-campaign';self.root.mkdir()
        self.skill=self.root/'SKILL.md';self.skill.write_text(SKILL)
        self.memory=memory_module.SkillMemory(self.root/'memory',self.skill,
            success_review=audit.memory_success_review(self.root,NATIVE))

    def add(self, number, *, native='in_progress', verdict=None, complete=True,
            contract=None, error=None, feedback=False):
        ep=self.root/f'episode-{number:04d}';(ep/'rollout').mkdir(parents=True)
        evidence=ep/'rollout/public.json';evidence.write_text('{}')
        self.memory.update(SKILL,f'Public lesson {number}',[evidence],ep/'rollout',ep.name,native)
        result={'success':native=='success','native_outcome':native,'actions':2,
                'skill_updated':complete,'error':error,'human_feedback_used':feedback,
                'human_demonstration_used':False,'completion_contract':contract}
        (ep/'result.json').write_text(json.dumps(result))
        (ep/'turn_001.json').write_text(json.dumps({'status':'completed' if complete else 'inProgress'}))
        if verdict is not None:self.review(number,verdict)
        return ep

    def review(self, number, verdict):
        ep=self.root/f'episode-{number:04d}'
        (ep/'success_review.json').write_text(json.dumps({
            'audited_task_success':verdict,'actor_access':False,
            'private_contact':'HOST_SECRET_CONTACT','object_pose':'HOST_SECRET_POSE',
            'why_failed':'HOST_SECRET_EXPLANATION','reward':987.654321}))

    def later(self, start=2):
        for i in range(start,start+5):self.add(i)

    def ids(self):return [r['version'] for r in self.memory.read()['experiences']]

    def test_real_native_success_rejected_record_is_not_pinned(self):
        ep=self.add(1,native='success',verdict=False)
        real=json.loads((ROOT/'evidence/public-experience-0001.json').read_text())
        # Keep the exact original public row, including its native success.
        self.memory.journal.write_text(json.dumps(real)+'\n')
        (ep/'success_review.json').write_bytes((ROOT/'evidence/host-only/success_review.json').read_bytes())
        self.later();self.assertEqual(self.ids(),[3,4,5,6])
        raw=json.loads(self.memory.journal.read_text().splitlines()[0]);self.assertEqual(raw,real)
        full=self.memory.read(version=1)['experiences'][0]
        self.assertEqual(full['native_outcome'],'success')
        self.assertEqual(full['retrieval']['task_audit_status'],'rejected')
        self.assertFalse(full['retrieval']['success_priority_eligible'])

    def test_audited_matching_completed_success_is_pinned(self):
        self.add(1,native='success',verdict=True);self.later()
        self.assertEqual(self.ids(),[1,4,5,6])
        self.assertTrue(self.memory.read()['experiences'][0]['retrieval']['success_priority_eligible'])

    def test_rejected_oldest_does_not_hide_later_audited_success(self):
        self.add(1,native='success',verdict=False)
        self.add(2,native='success',verdict=True);self.later(start=3)
        self.assertEqual(self.ids(),[2,5,6,7])

    def test_historical_unreviewed_success_is_unknown_not_pinned(self):
        self.add(1,native='success');self.later()
        self.assertEqual(self.ids(),[3,4,5,6])
        self.assertEqual(self.memory.read(version=1)['experiences'][0]['retrieval']['task_audit_status'],'unknown')

    def test_no_review_provider_is_conservative(self):
        self.add(1,native='success',verdict=True);self.later()
        legacy=memory_module.SkillMemory(self.memory.root,self.skill)
        self.assertEqual([r['version'] for r in legacy.read()['experiences']],[3,4,5,6])
        self.assertEqual(legacy.read(version=1)['experiences'][0]['retrieval']['task_audit_status'],'unknown')

    def test_audit_published_after_update_changes_next_read_without_rewrite(self):
        self.add(1,native='success');self.later()
        before={str(p.relative_to(self.memory.root)):p.read_bytes() for p in self.memory.root.rglob('*') if p.is_file()}
        skill_before=self.skill.read_bytes()
        self.assertEqual(self.ids(),[3,4,5,6])
        self.review(1,True);self.assertEqual(self.ids(),[1,4,5,6])
        self.review(1,False);self.assertEqual(self.ids(),[3,4,5,6])
        self.assertEqual(before,{str(p.relative_to(self.memory.root)):p.read_bytes() for p in self.memory.root.rglob('*') if p.is_file()})
        self.assertEqual(skill_before,self.skill.read_bytes())

    def test_rejected_recent_and_explicit_version_remain_retrievable(self):
        self.add(1,native='success',verdict=False)
        self.assertEqual(self.ids(),[1])
        self.assertFalse(self.memory.read()['experiences'][0]['retrieval']['success_priority_eligible'])
        self.assertEqual(self.memory.read(version=1)['experiences'][0]['lesson'],'Public lesson 1')

    def test_ordinary_failure_never_pinned_even_with_bad_positive_review(self):
        self.add(1,native='failure',verdict=True);self.later()
        self.assertEqual(self.ids(),[3,4,5,6])
        self.assertFalse(self.memory.read(version=1)['experiences'][0]['retrieval']['success_priority_eligible'])

    def test_incomplete_or_errored_result_never_pinned(self):
        self.add(1,native='success',verdict=True,complete=False)
        self.add(2,native='success',verdict=True,error='execution_fault')
        self.later(start=3);self.assertEqual(self.ids(),[4,5,6,7])

    def test_changed_completion_contract_is_not_pinned(self):
        self.add(1,native='success',verdict=True);self.later()
        self.memory.success_review=audit.memory_success_review(self.root,PLACEMENT)
        self.assertEqual(self.ids(),[3,4,5,6])
        label=self.memory.read(version=1)['experiences'][0]['retrieval']
        self.assertEqual(label['task_audit_status'],'passed')
        self.assertIs(label['completion_contract_matches'],False)

    def test_new_result_completion_contract_is_used_without_scene_copy(self):
        self.add(1,native='success',verdict=True,contract={'id':PLACEMENT});self.later()
        self.memory.success_review=audit.memory_success_review(self.root,PLACEMENT)
        self.assertEqual(self.ids(),[1,4,5,6])

    def test_missing_or_invalid_current_contract_does_not_establish_compatibility(self):
        self.add(1,native='success',verdict=True,contract={'id':None});self.later()
        for contract in [None,'',False]:
            self.memory.success_review=audit.memory_success_review(self.root,contract)
            self.assertEqual(self.ids(),[3,4,5,6])

    def test_original_scene_contract_and_door_fallback_still_work(self):
        ep=self.add(1,native='success',verdict=True)
        (ep/'video').mkdir();(ep/'video/scene_setup.json').write_text(json.dumps({'completion_contract':{'id':PLACEMENT}}))
        self.memory.success_review=audit.memory_success_review(self.root,PLACEMENT)
        self.assertTrue(self.memory.read()['experiences'][0]['retrieval']['success_priority_eligible'])
        # Existing door auditor contract is reused; no invented second identity.
        door=self.root.parent/'door-campaign';door.mkdir()
        dep=door/'episode-0001';dep.mkdir()
        for name in ['result.json','turn_001.json','success_review.json']:(dep/name).write_bytes((ep/name).read_bytes())
        label=audit.memory_success_review(door,'door-push-contact30deg-dwell1s-standing')('episode-0001')
        self.assertTrue(label['audited_task_success'] and label['completion_contract_matches'])

    def test_host_payload_is_absent_and_feedback_fields_are_not_retagged(self):
        ep=self.add(1,native='success',verdict=True,feedback=True)
        row=json.loads(self.memory.journal.read_text());row.update(human_feedback_used=True,human_demonstration_used=False)
        self.memory.journal.write_text(json.dumps(row)+'\n')
        for packet in [self.memory.read(),self.memory.read(version=1)]:
            output=json.dumps(packet)
            for token in ['HOST_SECRET','987.654321','success_review.json','object_pose','private_contact']:
                self.assertNotIn(token,output)
            item=packet['experiences'][0]
            self.assertIs(item['human_feedback_used'],True);self.assertIs(item['human_demonstration_used'],False)
        # Old missing fields stay missing rather than becoming false/autonomous.
        row.pop('human_feedback_used');row.pop('human_demonstration_used')
        self.memory.journal.write_text(json.dumps(row)+'\n')
        self.assertNotIn('human_feedback_used',self.memory.read(version=1)['experiences'][0])

    def test_extra_callback_payload_is_not_copied(self):
        self.add(1,native='success')
        self.memory.success_review=lambda _:dict(task_audit_status='passed',completion_contract_matches=True,
            audited_task_success=True,raw_audit='HOST_SECRET',audit_path='/host/private')
        packet=json.dumps(self.memory.read());self.assertNotIn('HOST_SECRET',packet);self.assertNotIn('/host/private',packet)

    def test_partial_audit_is_unknown_then_valid_review_is_seen(self):
        ep=self.add(1,native='success',verdict=True);self.later()
        (ep/'success_review.json').write_text('{')
        self.assertEqual(self.ids(),[3,4,5,6])
        self.assertEqual(self.memory.read(version=1)['experiences'][0]['retrieval']['task_audit_status'],'unknown')
        self.review(1,True);self.assertEqual(self.ids(),[1,4,5,6])

    def test_episode_path_escape_does_not_read_another_campaign(self):
        callback=audit.memory_success_review(self.root,NATIVE)
        self.assertEqual(callback('../episode-0001'),{})
        self.assertEqual(callback('/private/episode-0001'),{})

    def test_actual_runner_constructor_hooks_supply_the_current_contract(self):
        for name,is_door in [('learn_simple_task.py',False),('learn_door_skill.py',True)]:
            tree=ast.parse((TREE/'tools'/name).read_text())
            call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='SkillMemory')
            expression=ast.Expression(call);ast.fix_missing_locations(expression)
            for configured,expected in [({},'door-push-contact30deg-dwell1s-standing' if is_door else NATIVE),({'completion_contract':{'id':PLACEMENT}},PLACEMENT)]:
                seen=[]
                def probe(root,contract):seen.append((root,contract));return lambda _:{}
                eval(compile(expression,name,'eval'),dict(SkillMemory=memory_module.SkillMemory,
                     memory_success_review=probe,root=self.root,skill=self.skill,ROOT=self.root,
                     specification=configured)) if not is_door else self.eval_door(expression,name,configured,probe)
                self.assertEqual(seen,[(self.root,expected)])

    def eval_door(self,expression,name,configured,probe):
        skill=self.root/'skills/loco-manip-simple/SKILL.md';skill.parent.mkdir(parents=True,exist_ok=True);skill.write_text(SKILL)
        return eval(compile(expression,name,'eval'),dict(SkillMemory=memory_module.SkillMemory,
            memory_success_review=probe,root=self.root,ROOT=self.root,specification=configured))


if __name__=='__main__':unittest.main(verbosity=2)
