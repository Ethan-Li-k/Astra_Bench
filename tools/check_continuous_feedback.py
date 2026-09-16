"""Exercise public continuous-motion feedback, no GPT or task success credit."""
import argparse
import json
from pathlib import Path

import numpy as np

from rsi.four_point import FOUR_POINT_NAMES, FourPointPose
from rsi.policy_harness import LocalFourPointHarness
from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import simple_video


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    b=create_closed_door_backend(seed=0,pd_profile='checkpoint',push_open=True)
    video=None
    try:
        b.continuous_chunks_enabled=True
        video=simple_video(b,args.output/'video',label='Continuous feedback contract test | no task credit')
        harness=LocalFourPointHarness(b,args.output/'rollout',image_capture=video)
        start=harness.start('Robot-only continuous feedback test; not a task attempt')
        pose=FourPointPose.from_mapping(start['observation']['four_point_world'])
        raised=pose.copy();raised.positions[2,2]+=.02
        response={'request_id':'feedback-test','mode':'four_point','reason':'Check public intra-chunk recording',
            'trajectory':[{'target':p.to_mapping(),'duration_s':.5,
                           'active':{'position':list(FOUR_POINT_NAMES),'orientation':[]},
                           'grippers':{'left':0.,'right':0.}} for p in (raised,pose)]}
        packet=harness.scalebfm_act(start['observation_path'],response)
        summary=packet['execution'][0]['robot_motion_summary']
        rows=[json.loads(s) for s in Path(summary['trace_path']).read_text().splitlines()]
        assert len(rows)==summary['samples'] and len(rows)>10
        assert all(set(r)=={'sim_s','positions_world_m','quaternions_wxyz',
                            'joint_position_rad','commanded_joint_target_rad'} for r in rows)
        assert len(summary['joint_names'])==29
        assert all(len(r['joint_position_rad'])==len(r['commanded_joint_target_rad'])==29 for r in rows)
        np.testing.assert_allclose(np.diff([r['sim_s'] for r in rows]),.02,atol=1e-9)
        np.testing.assert_array_equal(rows[-1]['positions_world_m'],
            FourPointPose.from_mapping(packet['observation']['four_point_world']).positions)
        np.testing.assert_array_equal(rows[-1]['commanded_joint_target_rad'],
                                      packet['observation']['commanded_joint_target_rad'])
        result={'passed':True,'gpt_calls':0,'task_success_credit':False,
                'sim_s':rows[-1]['sim_s']-rows[0]['sim_s'],
                'samples':len(rows),'robot_only_allowlist_verified':True,
                'sample_dt_s':.02,'last_sample_matches_final_observation':True,
                'stop_reason':b.reason}
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:
        if video:video.close()
        b.close()


if __name__=='__main__':main()
