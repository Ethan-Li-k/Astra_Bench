"""Exercise the unchanged frozen execute loop with a tick counter, no physics."""
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
FROZEN=ROOT.parent/'codex-account-2/workspace/ground-to-table/provenance/episodes/episode-0007'
sys.path[:0]=[str(FROZEN),str(ROOT/'actor-adapter')]
from rsi.policy_harness import LocalFourPointHarness, FOUR_POINT_NAMES
from actor import physical_preflight


class FrozenLoopBound(unittest.TestCase):
    def test_single_and_continuous_loop_match_preflight_without_physics(self):
        for durations in ([.5],[3.],[.6]*5,[.7,.8,1.]):
            with self.subTest(durations=durations),tempfile.TemporaryDirectory(dir=ROOT) as directory:
                points={name:{'position_world_m':[0.,0.,0.],
                    'quaternion_wxyz':[1.,0.,0.,0.]} for name in FOUR_POINT_NAMES}
                backend=NS(data=NS(time=5.),physics_substeps=5,model=NS(opt=NS(timestep=.004)),
                    continuous_chunks_enabled=True,active=None)
                ticks=[]
                def tick(): ticks.append(True);backend.data.time+=.02
                backend.tick=tick
                backend.observe=lambda:{'observation_id':'fake','sim_s':backend.data.time,
                    'four_point_world':points,'joint_names':[]}
                backend.move_four_points=lambda *a,**kw:{'duration_s':durations[0]}
                backend.move_four_point_sequence=lambda *a,**kw:{'duration_s':min(3.,math.fsum(durations))}
                backend.set_grippers=lambda *a,**kw:None
                backend.status=lambda:{'status':'executing'}  # Force maximum loop, no early arrival.
                harness=LocalFourPointHarness(backend,Path(directory))
                harness._require_latest=lambda p:None
                harness._write_json=lambda *a:None
                harness._capture=lambda:{}
                host=NS(backend=backend,finished=False,episode_start_sim_s=5.,max_episode_steps=9000)
                expected=physical_preflight(host,{'trajectory':[{'duration_s':d} for d in durations]})
                action={'request_id':'offline-fake','trajectory':[{'duration_s':d,
                    'target':NS(to_mapping=lambda:points),'active':{'position':[],'orientation':[]},
                    'grippers':{'left':0.,'right':0.}} for d in durations]}
                with patch('rsi.policy_harness.validate_response',return_value=action):
                    harness.scalebfm_act('fake',{})
                self.assertEqual(len(ticks),expected['maximum_action_steps'])
                self.assertAlmostEqual(backend.data.time-5.,expected['maximum_action_s'])


if __name__=='__main__':unittest.main()
