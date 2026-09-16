"""Offline 120-turn bounds and action preflight. No physics, network or credentials."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import actor
from history_bound import PublicHistory, encode
from test_actor import Budget, decision, payload, response
from test_conclude_gate import ConcludeHost


def host_at(root, remaining):
    host = ConcludeHost(root)
    host.episode_start_sim_s = 5.
    host.max_episode_steps = 9000
    host.backend.data = NS(time=5+(9000-remaining)*.02)
    host.backend.continuous_chunks_enabled = True
    host.backend.physics_substeps = 5
    host.backend.model = NS(opt=NS(timestep=.004))
    return host


def action(durations):
    return {'trajectory': [{'duration_s': v} for v in durations]}


class Batch002Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def test_120_calls_require_registered_run_and_stop_exactly(self):
        with self.assertRaises(ValueError):
            actor.ResponsesSession(self.root/'wrong', Budget(), lambda p: response(),
                                   'api-ground-001', max_calls=120)
        sent = []
        session = actor.ResponsesSession(self.root/'calls', Budget(),
            lambda p: sent.append(True) or response(), 'api-ground-002', max_calls=120)
        for _ in range(120): session.call(payload())
        with self.assertRaises(ValueError): session.call(payload())
        self.assertEqual(len(sent), 120)
        self.assertEqual(actor.terminal_kind('in_progress', None, False, False, 120,
                                            max_calls=120), 'budget_limited_incomplete')

    def test_authorization_run_episode_and_hash_pins(self):
        hook = actor.load_module(actor.ROOT.parent/'empirical_hook.py', 'hook_test002')
        path = actor.ROOT/'authorization-002.json'
        _, count, skill = actor.validate_authorization(path,'api-ground-002','episode-0002',hook)
        self.assertEqual(count,120)
        content = skill.read_text()+'\n'+actor.INSTRUCTIONS
        self.assertLessEqual(len(content),6250)
        self.assertLessEqual(len(content.split()),831)
        for auth,run,ep in [(actor.ROOT/'authorization.json','api-ground-002','episode-0002'),
                            (path,'api-ground-002','episode-0001'),(path,'api-ground-001','episode-0001')]:
            with self.assertRaises(ValueError): actor.validate_authorization(auth,run,ep,hook)
        with self.assertRaises(ValueError): hook.route('../api-ground-002')

    def test_arrival_wait_and_exact_execution_loop_budget(self):
        for durations in ([.5],[3.],[.6]*5,[.7, .8, 1.]):
            duration = min(3.,__import__('math').fsum(durations))
            upper = int((duration+2.1)/.02)
            host = host_at(self.root,upper)
            self.assertTrue(actor.physical_preflight(host,action(durations))['accepted'])
            host.backend.data.time += .02
            self.assertFalse(actor.physical_preflight(host,action(durations))['accepted'])
            self.assertGreater(upper, duration/.02)
        host = host_at(self.root,300)
        host.backend.continuous_chunks_enabled = False
        self.assertFalse(actor.physical_preflight(host,action([1.,1.]))['accepted'])

    def test_boundary_rejects_before_any_host_action(self):
        host = host_at(self.root,150)  # 3s references fit; arrival wait does not.
        gate = actor.Gate(host,physical_guard=True)
        result = gate.dispatch('scalebfm_act',{'response':action([3.]),'public_decision':decision()})
        self.assertEqual(host.calls,[])
        self.assertEqual(host.actions,3)
        self.assertTrue(result['no_execution'])
        self.assertEqual(host.stop_reason,'episode_step_budget')
        self.assertEqual(actor.terminal_kind('in_progress',None,False,False,9,
            stop_reason=host.stop_reason,max_calls=120),'budget_limited_incomplete')

    def test_read_and_geometry_do_not_advance_physics_or_apply_action_guard(self):
        host = host_at(self.root,0)
        gate = actor.Gate(host,physical_guard=True)
        gate.register({'path':str(host.harness.latest_path)})
        before = host.backend.data.time
        for name in ('four_point_translate','four_point_rotate','image_pixel_to_world_plane',
                     'four_point_place_local_point','experience_read'):
            gate.schemas[name] = ({'properties':{'public_decision':{}},'required':['public_decision']},'fake geometry')
            gate.dispatch(name,{'public_decision':decision()})
        gate.dispatch('read_public_evidence',{'path':str(host.harness.latest_path),'public_decision':decision()})
        self.assertEqual(host.backend.data.time,before)
        self.assertFalse(host.finished)
        self.assertEqual(host.actions,3)

    def test_timing_mismatch_and_nonfinite_rejected(self):
        host = host_at(self.root,9000)
        for durations in ([float('nan')],[3.1],[.4],[1.]*4):
            with self.assertRaises(ValueError): actor.physical_preflight(host,action(durations))
        host.backend.physics_substeps=4
        with self.assertRaises(ValueError): actor.physical_preflight(host,action([1.]))

    def test_120_large_turns_bounded_coherent_latest_and_public_only_index(self):
        prefix='PINNED TASK AND SKILL'
        history=PublicHistory(prefix,{'task':'floor pickup'},[{'type':'input_text','text':'initial'}])
        # Realistic repeated robot sample structure, labelled synthetic images/encryption.
        sample={'sim_s':1.,'four_point_world':{str(i):{'position_world_m':[.1,.2,.3],
            'quaternion_wxyz':[1.,0.,0.,0.]} for i in range(4)},'joint_position_rad':[.001*i for i in range(40)]}
        huge={'samples':[sample]*250,'returned_sample_indices':list(range(250)),
              'sampling_notice':'SYNTHETIC repeated robot data; no physics'}
        maximum=0
        for i in range(120):
            call={'type':'function_call','call_id':f'c{i}','name':'read_public_evidence',
                  'arguments':json.dumps({'public_decision':decision(),'path':f'issued/{i}.json'})}
            packet=copy.deepcopy(huge)|{'observation_path':f'issued/{i}.json','step_id':i}
            content=[{'type':'input_image','image_url':f'data:image/png;base64,SYNTHETIC-{i}-{cam}-'+'a'*150_000}
                     for cam in ('head','wrist')]
            history.append([{'type':'reasoning','encrypted_content':'PRIVATE-IN-MEMORY-'+'x'*60_000},call],
                           call,packet,content,{'path':f'issued/result-{i}.json','sha256':'a'*64})
            result=history.payload(payload()|{'tools':[]},actor.MAX_BODY)
            maximum=max(maximum,len(encode(result)))
            items=result['input']; self.assertEqual(items[0]['content'],prefix)
            calls=[v['call_id'] for v in items if v.get('type')=='function_call']
            outputs=[v['call_id'] for v in items if v.get('type')=='function_call_output']
            self.assertEqual(calls,outputs)
            self.assertEqual(calls[-1],f'c{i}')
            pictures=[c['image_url'] for v in items if isinstance(v.get('content'),list)
                      for c in v['content'] if c.get('type')=='input_image']
            self.assertLessEqual(len(pictures),4)
            self.assertTrue(all(any(f'SYNTHETIC-{k}-' in p for k in (i-1,i)) for p in pictures))
            self.assertNotIn('PRIVATE',json.dumps(history.index))
            self.assertEqual(len(history.index),i+1)
        self.assertLessEqual(maximum,actor.MAX_BODY)
        print('120-turn maximum request bytes:',maximum)

    def test_history_refuses_unfinished_exchange_and_oversized_latest(self):
        history=PublicHistory('skill',{},[{'type':'input_text','text':'x'*2_000_001}])
        with self.assertRaises(ValueError): history.payload(payload(),actor.MAX_BODY)
        with self.assertRaises(ValueError): history.append([],{'call_id':'unfinished'},{},[],{})


if __name__ == '__main__': unittest.main()
