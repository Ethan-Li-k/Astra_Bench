"""Offline schema tests only; all fabricated successes remain isolated fixtures."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import ikea_gate as g
from test_ikea_gate import GateTests


class FrameSchemaTests(unittest.TestCase):
    def setUp(self):
        self.fixture=GateTests();self.fixture.setUp()
        self.f=self.fixture
        self.approval=g.read(g.ROOT/g.FRAME_APPROVAL)

    def make(self,index=1):
        f=self.f;e,r=f.make(index)
        r['schema']=2;r['provenance_review']={**g.COMMON_PROVENANCE,'original_physics':False,'reviewed_physics_revision':True}
        r['physics_revision']=g.frame_binding()
        r['runtime_source_sha256']['rsi/simple_door_collision.py']=self.approval['validation_evidence_sha256']['rsi/simple_door_collision.py']
        scene=g.read(e/'video/scene_setup.json');scene['frame_collision_override']=copy.deepcopy(self.approval['revision']);scene['reset_provenance']=copy.deepcopy(r['reset']);g.atomic_json(e/'video/scene_setup.json',scene)
        manifest=g.read(e/'video/render_manifest.json');manifest['runtime_source_sha256']=r['runtime_source_sha256'];g.atomic_json(e/'video/render_manifest.json',manifest)
        result=g.read(e/'result.json');result['account_route']='authorized_account_2';g.atomic_json(e/'result.json',result)
        g.atomic_json(e/'account_route_verified.json',{'model':'gpt-6-astra','effort':'xhigh','launcher':str(g.ROOT/'codex-account-2/run.sh'),'codex_home':str(g.ROOT/'codex-account-2/home')})
        stats=g.audit_trace(e/'video/robot_trace.jsonl',manifest['initial_render_state'],result['sim_s'])
        review={'audited_task_success':True,'actor_access':False,'unmodified_native_benchmark':False,'physics_revision':scene['frame_collision_override'],'reset':r['reset'],'recording_audit':stats,'evidence_sha256':{}}
        review.update(dict.fromkeys(['independent_reset_verified','full_turn_and_skill_update','single_action_writer','no_replay_or_diagnostic_initial_state'],True))
        g.atomic_json(e/'success_review.json',review)
        r['host_evidence'] += [{'path':str((e/n).relative_to(g.ROOT)),'sha256':g.digest(e/n)} for n in ['success_review.json','video/scene_setup.json']]
        self.seal(e,r);return e,r

    def seal(self,e,r):
        for item in r['host_evidence']: item['sha256']=g.digest(g.ROOT/item['path'])
        r['evidence_sha256']={n:g.digest(e/n) for n in (*g.REQUIRED,'turn_001.json','success_review.json','account_route_verified.json')}
        p=self.f.root/f'{e.name}-receipt.json';g.atomic_json(p,r)
        self.f.registry['episodes']=[x for x in self.f.registry['episodes'] if x['receipt']!=p.name]+[{'receipt':p.name,'sha256':g.digest(p)}]

    def physical(self):
        return g.evaluate_physical(self.f.registry,base=self.f.root,campaign=self.f.campaign,probe=self.f.probe)

    def reject(self):
        s=self.physical();self.assertEqual(s['audited_independent_successes'],0,s);self.assertFalse(s['physical_gate_passed']);self.assertTrue(s['rejected'])

    def test_01_unknown_override(self):
        e,r=self.make();r['physics_revision']['override_id']='unknown';self.seal(e,r);self.reject()

    def test_02_missing_binding_fields(self):
        for field in g.frame_binding():
            with self.subTest(field=field):
                self.f.registry['episodes']=[];e,r=self.make(10+len(list(self.f.campaign.iterdir())))
                del r['physics_revision'][field];self.seal(e,r);self.reject()

    def test_03_source_hash_changed(self):
        e,r=self.make();r['physics_revision']['source_mesh_sha256']='0'*64;self.seal(e,r);self.reject()

    def test_04_falsely_claims_original(self):
        e,r=self.make();r['provenance_review']['original_physics']=True;self.seal(e,r);self.reject()

    def test_05_repaired_scene_cannot_use_legacy_schema(self):
        e,r=self.make();r['schema']=1;r.pop('physics_revision');r['provenance_review']={**g.COMMON_PROVENANCE,'original_physics':True};self.seal(e,r);self.reject()

    def test_06_geometry_or_flags_changed(self):
        e,r=self.make();scene=g.read(e/'video/scene_setup.json');scene['frame_collision_override']['boxes_in_source_mesh_frame'][0]['half_size'][0]*=2;g.atomic_json(e/'video/scene_setup.json',scene);self.seal(e,r);self.reject()

    def test_07_runtime_collision_hash_changed(self):
        e,r=self.make();r['runtime_source_sha256']['rsi/simple_door_collision.py']='f'*64
        m=g.read(e/'video/render_manifest.json');m['runtime_source_sha256']=r['runtime_source_sha256'];g.atomic_json(e/'video/render_manifest.json',m);self.seal(e,r);self.reject()

    def test_08_reset_mismatch(self):
        e,r=self.make();r['reset']['reset_id']='different';self.seal(e,r);self.reject()

    def test_09_missing_host_review(self):
        e,r=self.make();r['evidence_sha256'].pop('success_review.json');p=self.f.root/f'{e.name}-receipt.json';g.atomic_json(p,r);self.f.registry['episodes'][0]['sha256']=g.digest(p);self.reject()

    def test_10_unsigned_template_cannot_enroll(self):
        e,r=self.make();r['data_kind']='unpopulated_template';self.seal(e,r);self.reject()

    def test_11_no_contact_still_rejected(self):
        e,r=self.make();p=e/'video/robot_trace.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()]
        for row in rows:row['host_render_state']['hand_door_contact']=False
        p.write_text(''.join(json.dumps(x)+'\n' for x in rows));self.seal(e,r);self.reject()

    def test_12_pinned_source_and_evidence_change(self):
        base=self.f.root/'isolated-pin-root'
        relatives=[g.FRAME_APPROVAL,*self.approval['validation_evidence_sha256'],str(Path(self.approval['revision']['source_mesh']).relative_to(g.ROOT))]
        for rel in relatives:
            p=base/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(g.ROOT/rel,p)
        scene={'frame_collision_override':self.approval['revision']};runtime={'rsi/simple_door_collision.py':self.approval['validation_evidence_sha256']['rsi/simple_door_collision.py']}
        self.assertEqual(g.audit_frame_revision(scene,runtime,g.frame_binding(),root=base)['physics_revision_id'],g.FRAME_OVERRIDE_ID)
        for rel in relatives:
            p=base/rel;old=p.read_bytes();p.write_bytes(old+b'CHANGED SYNTHETIC BYTES')
            with self.assertRaises((g.Rejected,ValueError)):g.audit_frame_revision(scene,runtime,g.frame_binding(),root=base)
            p.write_bytes(old)

    def test_13_missing_scene_override_field(self):
        e,r=self.make();s=g.read(e/'video/scene_setup.json');del s['frame_collision_override']['visual_geometry_unchanged'];g.atomic_json(e/'video/scene_setup.json',s);self.seal(e,r);self.reject()

    def test_14_unchanged_native_benchmark_claim_rejected(self):
        e,r=self.make();r['physics_revision']['unmodified_native_benchmark']=True;self.seal(e,r);self.reject()

    def test_15_short_video_still_rejected(self):
        self.make();self.f.probe=lambda _: {'nb_frames':'1','duration':'.04','r_frame_rate':'25/1'};self.reject()

    def test_16_incomplete_turn_still_rejected(self):
        e,r=self.make();g.atomic_json(e/'turn_001.json',{'status':'in_progress'});self.seal(e,r);self.reject()

    def test_17_duplicate_reset_or_launch_still_rejected(self):
        _,a=self.make();e,b=self.make(2);b['reset']=copy.deepcopy(a['reset']);b['reset']['seed']=2
        s=g.read(e/'video/scene_setup.json');s['reset_provenance']=b['reset'];g.atomic_json(e/'video/scene_setup.json',s)
        h=g.read(e/'success_review.json');h['reset']=b['reset'];g.atomic_json(e/'success_review.json',h);self.seal(e,b)
        self.assertEqual(self.physical()['audited_independent_successes'],1)

    def test_90_two_synthetic_successes_do_not_pass(self):
        self.make();self.make(2);s=self.physical();self.assertEqual(s['audited_independent_successes'],2);self.assertFalse(s['physical_gate_passed'])

    def test_91_three_synthetic_successes_register_only_no_budget_read(self):
        for i in range(1,4):self.make(i)
        original=g.read
        def restricted(path):
            if any(t in str(path) for t in ['api-configuration','api-budget','ledger']):raise AssertionError('physical audit must not inspect API/accounting')
            return original(path)
        with patch.object(g,'read',side_effect=restricted):s=self.physical()
        self.assertTrue(s['physical_gate_passed']);self.assertFalse(s['launch_performed']);self.assertEqual(s['model_calls'],0)
        self.assertTrue(all(x['physics_revision_id']==g.FRAME_OVERRIDE_ID and x['unmodified_native_benchmark'] is False for x in s['accepted']))


if __name__=='__main__':unittest.main(verbosity=2)
