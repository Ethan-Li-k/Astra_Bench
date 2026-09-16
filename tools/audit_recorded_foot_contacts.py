"""Recompute contact geometry from recorded states; no physical trial credit."""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import restore_named_render_state


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--door-frame-override',action='store_true')
    args=p.parse_args()
    rows=[json.loads(s) for s in args.trace.read_text().splitlines()]
    times=np.array([r['sim_s'] for r in rows])
    assert len(rows)>1 and np.allclose(np.diff(times),.02,atol=1e-9)
    b=create_closed_door_backend(seed=args.seed,pd_profile='checkpoint',push_open=True,
                                door_frame_override=args.door_frame_override)
    try:
        m,d=b.model,b.data
        feet=[]
        for name in ('left_ankle_roll_link','right_ankle_roll_link'):
            root=m.body(name).id
            # Independent ancestor traversal per geom, rather than forward body scan.
            geoms=set()
            for gid,body in enumerate(m.geom_bodyid):
                while body:
                    if body==root:geoms.add(gid);break
                    body=int(m.body_parentid[body])
            feet.append(geoms)
        planes={g for g in range(m.ngeom) if m.geom_type[g]==mujoco.mjtGeom.mjGEOM_PLANE}
        intervals=[[],[]];start=[None,None];max_tilt=0.;min_height=float('inf')
        for row in rows:
            restore_named_render_state(m,d,row['host_render_state'])
            pelvis=m.body('pelvis').id
            min_height=min(min_height,float(d.xpos[pelvis,2]))
            max_tilt=max(max_tilt,float(np.degrees(np.arccos(np.clip(d.xmat[pelvis].reshape(3,3)[2,2],-1,1)))))
            pairs=[{int(c.geom1),int(c.geom2)} for c in d.contact if c.dist<=.0001]
            for side,geoms in enumerate(feet):
                touching=any(pair&geoms and pair&planes for pair in pairs)
                if not touching and start[side] is None:start[side]=row['sim_s']
                if touching and start[side] is not None:
                    intervals[side].append([start[side],row['sim_s']]);start[side]=None
        for side in range(2):
            if start[side] is not None:intervals[side].append([start[side],times[-1]+.02])
        result={'actor_access':False,'state_reconstruction_only':True,'physical_attempt_credit':False,
                'task_success_credit':False,'source_trace':str(args.trace.resolve()),
                'samples':len(rows),'sample_dt_s':.02,'air_intervals_sim_s':intervals,
                'max_no_plane_contact_s':[max([end-begin for begin,end in spans],default=0.) for spans in intervals],
                'min_pelvis_height_m':min_height,'max_pelvis_tilt_deg':max_tilt,
                'standing_bounds_satisfied':min_height>=.55 and max_tilt<=25.,
                'limitation':'Contact geometry at 50Hz saved states; not a second physical trial or continuous-time proof.'}
        args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:b.close()


if __name__=='__main__':main()
