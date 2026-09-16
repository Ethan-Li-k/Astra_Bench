"""Validate robot-only hand surface sidecar in a native SIMPLE instance."""
import argparse
import json
from pathlib import Path

import numpy as np

from rsi.simple_environment import create_native_task_backend
from rsi.simple_hand_geometry import HandGeometryProvider, hand_collision_model
from rsi.simple_recording import simple_video


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    b=create_native_task_backend('simple/G1WholebodyBendPickTeleop-v0',seed=5)
    video=None
    try:
        video=simple_video(b,args.output/'video',label='Robot geometry verification | no task credit')
        provider=HandGeometryProvider(args.output/'public')
        first=provider(b);before=hand_collision_model(b)
        b.set_grippers(left=0.,right=.25,duration=.5)
        for _ in range(50):
            b.tick();video.record_tick('diagnostic_only')
        second=provider(b);after=hand_collision_model(b)
        assert first['hand_collision_model']['sha256']==second['hand_collision_model']['sha256']
        assert set(before['bodies'])==set(after['bodies'])
        errors=[]
        for name in before['bodies']:
            assert name.startswith(('left_wrist_','right_wrist_','left_hand_','right_hand_'))
            for a,c in zip(before['bodies'][name],after['bodies'][name]):
                if a['kind']=='convex_mesh':
                    aa=np.array(a['vertices_body_m']);cc=np.array(c['vertices_body_m'])
                    errors.append(float(np.max(np.abs(aa-cc))))
        assert max(errors)<1e-7
        (args.output/'public/initial_geometry_observation.json').write_text(json.dumps(first,indent=2)+'\n')
        (args.output/'public/final_geometry_observation.json').write_text(json.dumps(second,indent=2)+'\n')
        result={'actor_access_to_host_data':False,'gpt_calls':0,'task_success_credit':False,
                'body_count':len(before['bodies']),
                'collision_geom_count':sum(map(len,before['bodies'].values())),
                'sidecar_bytes':provider.path.stat().st_size,
                'max_body_local_vertex_difference_after_closure_m':max(errors),
                'body_pose_changed':first['hand_collision_model']['body_poses_world']!=second['hand_collision_model']['body_poses_world'],
                'stop_reason':b.reason,'sim_s':1.,'scope':'Only own robot hand geometry/poses. No object positions, contact or reward fields exposed.'}
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:
        if video:video.close()
        b.close()


if __name__=='__main__':main()
