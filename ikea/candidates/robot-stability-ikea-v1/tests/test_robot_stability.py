"""Offline fixtures only: never construct MjModel, LiveSim, ONNX or an environment."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from scipy.spatial.transform import Rotation

TASK = Path(__file__).resolve().parents[1]
REPO = Path('/home/galbot/lizekai/RSI')
class PreservedTemporaryDirectory:
    def __init__(self, suffix=None, prefix=None, dir=None, **kwargs):
        self.path = tempfile.mkdtemp(suffix=suffix or '', prefix=prefix or 'preserved-fixture-', dir=str(TASK/'evidence'))
    def __enter__(self):return self.path
    def __exit__(self, *args):return False
tempfile.TemporaryDirectory = PreservedTemporaryDirectory
SOURCE = TASK / os.environ.get('STABILITY_SOURCE', 'candidate')
sys.path[:0] = [str(SOURCE), '/home/galbot/lizekai/Loco_manip/locomanip/src']

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

live = load('rsi.live', SOURCE/'rsi/live.py')
ph = load('rsi.policy_harness', SOURCE/'rsi/policy_harness.py')
oldtests = load('stability_existing_harness_tests', TASK/'snapshots/tests/test_policy_harness.py')
from rsi.four_point import FOUR_POINT_NAMES, FourPointPose

SENTINEL = 'POISON_object_contact_reward_evaluator_host_audit'
ROOT_KEYS = {'body_name', 'frame', 'height_world_m', 'quaternion_wxyz', 'tilt_deg'}

def fixture(tilt=17., height=.71):
    s = live.LiveSim.__new__(live.LiveSim)
    # World=0; object freejoint/body comes FIRST. Robot root is body 2,
    # qpos address 7. Its inertial-frame height is deliberately different.
    s.model = SimpleNamespace(body=lambda name: SimpleNamespace(id={'pelvis':2}[name]),
                              body_parentid=np.array([0,0,0,2,2,2,2]))
    quat_xyzw = Rotation.from_euler('xyz', [tilt, 0, 31], degrees=True).as_quat()
    quat = quat_xyzw[[3,0,1,2]]
    pos = np.zeros((7,3)); pos[1]=[91,92,93]; pos[2]=[.4,-.2,height]
    quats = np.tile([1.,0,0,0], (7,1)); quats[2]=quat
    mats=np.tile(np.eye(3).reshape(9), (7,1)); mats[2]=Rotation.from_quat(quat_xyzw).as_matrix().reshape(9)
    qpos=np.zeros(16); qpos[:7]=[91,92,93,1,0,0,0]; qpos[7:14]=[.4,-.2,height,*quat]
    s.data=SimpleNamespace(time=2.,xpos=pos,xquat=quats,xmat=mats,qpos=qpos,
                           xipos=pos+[0,0,-.08],contact=SENTINEL,reward=SENTINEL)
    s.adapter=SimpleNamespace(body_ids=np.array([2,3,4,5,6]),
        metadata={'joint_names':['robot_joint']},_policy_qpos_adr=np.array([14]))
    s.four=np.array([1,2,3,4]);s.wrist=2;s.sequence=0;s.fingers=['robot_finger'];s.fq=np.array([15])
    s.grips={'left':0.,'right':0.};s.reason=None;s.continuous_chunks_enabled=False
    s.translation_limit_m_by_link={n:.03 for n in FOUR_POINT_NAMES}
    s.reference_pose_at=lambda t: FourPointPose(pos[[3,4,5,6]],quats[[3,4,5,6]])
    s.reference_at=lambda t: pos[4].copy()
    s.gripper_command_at=lambda t: dict(s.grips)
    s.status=lambda: {'status':'idle'}
    s.host_audit=SENTINEL;s.object_truth=SENTINEL;s._native_task_reward=SENTINEL
    return s

class ObserveTests(unittest.TestCase):
    def test_missing_root_field_red_reproduction(self):
        self.assertIn('robot_root', fixture().observe())

    def test_named_nonidentity_root_and_exact_safety_tilt(self):
        s=fixture(); p=s.observe(); r=p['robot_root']
        self.assertEqual(set(r), ROOT_KEYS)
        self.assertEqual(r['body_name'],'pelvis');self.assertEqual(r['frame'],'world')
        self.assertAlmostEqual(r['height_world_m'],.71)
        self.assertNotEqual(r['height_world_m'],s.data.qpos[2])
        self.assertNotEqual(r['height_world_m'],s.data.xipos[2,2])
        np.testing.assert_allclose(r['quaternion_wxyz'],s.data.qpos[10:14])
        expected=np.rad2deg(np.arccos(np.clip(s.data.xmat[s.adapter.body_ids[0]].reshape(3,3)[2,2],-1,1)))
        self.assertEqual(r['tilt_deg'],expected)
        self.assertAlmostEqual(r['tilt_deg'],17.)
        self.assertEqual(p['sim_s'],2.)
        self.assertNotIn('margin',json.dumps(r))

    def test_missing_mismatched_and_nonfinite_are_unavailable(self):
        for mut in ('missing','wrong_body','not_root','nan_height','inf_quat','nan_matrix','zero_quat'):
            with self.subTest(mut=mut):
                s=fixture()
                if mut=='missing': s.model.body=lambda n: (_ for _ in ()).throw(KeyError(n))
                if mut=='wrong_body': s.adapter.body_ids[0]=1
                if mut=='not_root': s.model.body_parentid[2]=1
                if mut=='nan_height': s.data.xpos[2,2]=float('nan')
                if mut=='inf_quat': s.data.xquat[2,0]=float('inf')
                if mut=='nan_matrix': s.data.xmat[2,8]=float('nan')
                if mut=='zero_quat': s.data.xquat[2]=0
                self.assertIsNone(s.observe()['robot_root'])

    def test_public_observe_recursive_allowlist_and_poison(self):
        p=fixture().observe()
        allowed={'observation_id','sim_s','captured_monotonic_s','localization_source','wrist_world_m',
            'wrist_reference_world_m','wrist_tracking_error_world_m','four_point_world','four_point_reference_world',
            'translation_limit_m_by_link','four_point_position_error_world_m','joint_names','joint_position_rad',
            'finger_names','finger_position_rad','gripper_commanded_closure','gripper_goal_closure','command_status',
            'stop_reason','robot_root'}
        self.assertEqual(set(p),allowed)
        self.assertEqual(set(p['robot_root']),ROOT_KEYS)
        for name in ('four_point_world','four_point_reference_world'):
            self.assertEqual(set(p[name]),set(FOUR_POINT_NAMES))
            for v in p[name].values(): self.assertEqual(set(v),{'position_world_m','quaternion_wxyz'})
        self.assertEqual(set(p['command_status']),{'status'})
        self.assertEqual(set(p['gripper_goal_closure']),{'left','right'})
        self.assertNotIn(SENTINEL,json.dumps(p,allow_nan=False))
        self.assertEqual(p['joint_position_rad'],[0.])

class RecordedBackend(oldtests.FakeBackend):
    continuous_chunks_enabled=True
    def __init__(self, frames):
        super().__init__();self.frames=frames;self.i=0;self.ticks=0
    def observe(self):
        p=fixture().observe()
        t,h,tilt=self.frames[self.i]
        p['sim_s']=t;p['observation_id']=f'fixture-{self.count}'
        self.count+=1
        p.setdefault('robot_root', {'body_name':'pelvis','frame':'world','height_world_m':.71,
            'tilt_deg':17.,'quaternion_wxyz':fixture().data.xquat[2].tolist()})
        p['robot_root'].update(height_world_m=h,tilt_deg=tilt,object_truth=SENTINEL,
                                contacts={'reward':SENTINEL},evaluator=SENTINEL)
        if h is None: p['robot_root']=None
        return p
    def move_four_point_sequence(self,observation_id,command_id,waypoints):
        self.state='executing'
        return {'command_id':command_id,'status':'executing','duration_s':1.}
    def tick(self):
        self.ticks+=1;self.i=min(self.i+1,len(self.frames)-1)
        if self.i==len(self.frames)-1:self.state='target_reached'

def episode(frames):
    with tempfile.TemporaryDirectory(dir=TASK/'evidence') as tmp:
        backend=RecordedBackend(frames)
        h=ph.LocalFourPointHarness(backend,Path(tmp)/'episode')
        first=h.start('offline interface fixture')
        action=oldtests.response();action['trajectory']*=2
        result=h.scalebfm_act(first['observation_path'],action)
        summary=result['execution'][0]['robot_motion_summary']
        rows=[json.loads(line) for line in Path(summary['trace_path']).read_text().splitlines()]
        return first,result,summary,rows,backend.ticks

class MotionTests(unittest.TestCase):
    def test_motion_missing_root_red_reproduction(self):
        first,result,summary,rows,ticks=episode([(2.,.72,10.),(2.02,.70,12.)])
        self.assertIn('robot_root',rows[0])
        self.assertIn('robot_root_summary',summary)

    def test_real_caller_copies_only_public_root_and_measured_trend(self):
        first,result,summary,rows,ticks=episode([(2.,.72,10.),(2.02,.70,12.),(2.04,.71,11.)])
        self.assertEqual(ticks,2)
        self.assertEqual(len(rows),3)
        root=summary['robot_root_summary']
        self.assertEqual(root['status'],'sampled')
        self.assertAlmostEqual(root['height_change_m'],-.01)
        self.assertAlmostEqual(root['tilt_change_deg'],1.)
        self.assertEqual(root['min_height_world_m'],.70);self.assertEqual(root['max_tilt_deg'],12.)
        self.assertEqual(root['start_sim_s'],2.);self.assertEqual(root['end_sim_s'],2.04)
        for row in rows:
            self.assertEqual(set(row),{'sim_s','positions_world_m','quaternions_wxyz','joint_position_rad',
                'commanded_joint_target_rad','observation_id','episode_id','robot_root'})
            self.assertEqual(set(row['robot_root']),ROOT_KEYS)
            self.assertEqual(row['episode_id'],first['observation']['episode_id'])
        self.assertEqual(set(first['observation']['robot_root']),ROOT_KEYS)
        self.assertNotIn(SENTINEL,json.dumps([first,result,rows],allow_nan=False))

    def test_reset_duplicate_time_missing_and_nonfinite_disable_trend(self):
        for frames in ([(2.,.72,10.),(0.,.5,20.)],[(2.,.72,10.),(2.,.7,20.)],
                       [(2.,.72,10.),(2.02,None,20.)],[(2.,.72,10.),(2.02,float('nan'),20.)],
                       [(2.,.72,10.),(float('nan'),.7,20.)]):
            with self.subTest(frames=frames):
                root=episode(frames)[2]['robot_root_summary']
                self.assertEqual(root['status'],'unavailable')
                self.assertNotIn('height_change_m',root)

    def test_first_sample_has_no_zero_delta(self):
        row={'sim_s':0.,'episode_id':'new-reset','observation_id':'obs-1','robot_root':fixture().observe()['robot_root']}
        result=ph._robot_root_summary([row])
        self.assertEqual(result['status'],'insufficient_samples')
        self.assertNotIn('height_change_m',result)

    def test_changed_episode_or_missing_identity_disables_trend(self):
        root=fixture().observe()['robot_root']
        a={'sim_s':0.,'episode_id':'one','observation_id':'obs-1','robot_root':root}
        for b in ({**a,'sim_s':.02,'episode_id':'two'}, {**a,'sim_s':.02,'observation_id':None}):
            self.assertEqual(ph._robot_root_summary([a,b])['status'],'unavailable')

    def test_new_episode_never_uses_previous_samples(self):
        a=episode([(8.,.7,10.),(8.02,.6,20.)])
        b=episode([(0.,.8,2.),(.02,.79,3.)])
        self.assertNotEqual(a[3][0]['episode_id'],b[3][0]['episode_id'])
        self.assertAlmostEqual(b[2]['robot_root_summary']['height_change_m'],-.01)

    def test_nested_numeric_poison_is_rejected(self):
        p=fixture().observe()
        for field in ('height_world_m','tilt_deg','quaternion_wxyz'):
            bad={**p,'robot_root':{**p['robot_root'],field:{'reward':SENTINEL}}}
            self.assertIsNone(ph._public_robot_root(bad))

if __name__=='__main__':
    # If accidentally invoked, all physics/model entry points fail before work.
    with patch.object(live.LiveSim,'__init__',side_effect=AssertionError('physics prohibited')), \
         patch.object(live.mujoco,'mj_step',side_effect=AssertionError('physics prohibited')), \
         patch.object(live,'Model38000',side_effect=AssertionError('model prohibited')):
        unittest.main()
