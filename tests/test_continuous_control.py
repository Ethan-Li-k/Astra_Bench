import copy
from types import SimpleNamespace
import time
import unittest

import numpy as np

from rsi.four_point import FOUR_POINT_NAMES, FourPointPose
from rsi.live import LiveSim


class ContinuousControlTests(unittest.TestCase):
    def setUp(self):
        self.sim=LiveSim.__new__(LiveSim)
        self.pose=FourPointPose(np.zeros((4,3)),np.tile([1.,0,0,0],(4,1)))
        s=self.sim
        s.continuous_chunks_enabled=True;s.commands={};s.active=s.reason=None
        s.observations={'fresh':{'captured_monotonic_s':time.monotonic(),
                                'four_point_world':self.pose.to_mapping()}}
        s.data=SimpleNamespace(time=0.)
        s.pos0=self.pose.positions.copy();s.four=np.arange(4);s.workspace_radius_m=2.
        s._reference_sequence=None;s._start_pose=self.pose.copy();s._goal_pose=self.pose.copy()
        self.rows=[]
        for x,z in ((.06,.2),(.12,0.)):
            p=self.pose.copy();p.positions[2]=[x,0,z]
            self.rows.append({'target':p,'duration_s':.5,
                'active':{'position':list(FOUR_POINT_NAMES),'orientation':[]},
                'grippers':{'left':0.,'right':0.}})

    def test_full_chunk_preflight_and_idempotency(self):
        bad=copy.deepcopy(self.rows);bad[-1]['target'].positions[0,0]=.5
        with self.assertRaises(ValueError):self.sim.move_four_point_sequence('fresh','bad',bad)
        self.assertIsNone(self.sim.active);self.assertEqual(self.sim.commands,{})
        receipt=self.sim.move_four_point_sequence('fresh','ok',self.rows)
        self.assertEqual(receipt['knot_sim_s'],[0.,.5,1.])
        self.assertGreater(self.sim.reference_pose_at(.6).positions[2,0],.06)
        self.assertIs(self.sim.move_four_point_sequence('fresh','ok',self.rows),receipt)
        changed=copy.deepcopy(self.rows);changed[-1]['duration_s']=.6
        with self.assertRaises(ValueError):self.sim.move_four_point_sequence('fresh','ok',changed)

    def test_default_disabled_and_stale_observation_rejected(self):
        self.sim.continuous_chunks_enabled=False
        with self.assertRaises(ValueError):self.sim.move_four_point_sequence('fresh','a',self.rows)
        self.sim.continuous_chunks_enabled=True
        self.sim.observations['fresh']['captured_monotonic_s']-=1.
        with self.assertRaises(ValueError):self.sim.move_four_point_sequence('fresh','b',self.rows)
        self.assertIsNone(self.sim.active)

    def test_three_second_chunk_gripper_ramp_at_nonzero_clock(self):
        # Actual faucet failure: four valid segments accepted motion then the
        # rounded absolute-time subtraction made set_grippers reject the ramp.
        s=self.sim;s.data.time=9.404999999999872
        s.grip_duration=0.;s.grips={'left':0.,'right':0.}
        s.grip_start=dict(s.grips);s.grip_t0=s.data.time
        rows=[copy.deepcopy(self.rows[0]) for _ in range(4)]
        for row,duration in zip(rows,(.6,.8,.8,.8)):
            row['duration_s']=duration
        receipt=s.move_four_point_sequence('fresh','boundary',rows)
        s.set_grippers(0.,0.,duration=receipt['duration_s'])
        self.assertEqual(receipt['duration_s'],3.)
        self.assertEqual(receipt['gripper_ramp']['duration_s'],3.)
        np.testing.assert_allclose(s.reference_pose_at(s.data.time+3.).positions,
                                   rows[-1]['target'].positions,atol=1e-12)


if __name__=='__main__':unittest.main()
