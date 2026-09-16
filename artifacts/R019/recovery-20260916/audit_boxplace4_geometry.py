"""Host-only reconstruction of saved states; never a new policy attempt."""
from pathlib import Path
import json
import hashlib
import mujoco
import numpy as np
from scipy.spatial import ConvexHull
from rsi.simple_environment import create_native_task_backend
from rsi.simple_recording import restore_named_render_state

root=Path('/home/galbot/lizekai/RSI')
ep=root/'artifacts/R019/boxplace-campaign/episode-0004'
out=root/'artifacts/R019/recovery-20260916/boxplace4-geometry'
out.mkdir()
rows=[json.loads(s) for s in (ep/'video/robot_trace.jsonl').read_text().splitlines()]
manifest=json.loads((ep/'video/render_manifest.json').read_text())
backend=create_native_task_backend('simple/G1WholebodyBendPickAndPlaceTeleop-v0',seed=4)
try:
    model,data=backend.model,backend.data
    target=model.body('cracker_box').id; container=model.body('brasket').id
    geoms={}
    for label,bid in [('box',target),('basket',container)]:
        parts=[]
        for g in range(model.ngeom):
            if model.geom_bodyid[g]!=bid or not (model.geom_contype[g] or model.geom_conaffinity[g]):continue
            assert model.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH
            mesh=int(model.geom_dataid[g]);start=int(model.mesh_vertadr[mesh]);n=int(model.mesh_vertnum[mesh])
            parts.append((g,model.mesh_vert[start:start+n].copy()))
        assert parts
        geoms[label]=parts
    indices=[0,next(i for i,r in enumerate(rows) if r['host_render_state'].get('placement_completion_host_only',{}).get('acquired')),
             max(range(len(rows)),key=lambda i:rows[i]['host_render_state']['qpos_by_joint']['cracker_box_joint'][2]),len(rows)-1]
    results=[]
    for i in indices:
        row=rows[i];restore_named_render_state(model,data,row['host_render_state'])
        vertices={label:np.concatenate([v@data.geom_xmat[g].reshape(3,3).T+data.geom_xpos[g] for g,v in parts]) for label,parts in geoms.items()}
        hull=ConvexHull(vertices['basket'][:,:2]);center=data.xipos[target,:2]
        outside=float((hull.equations[:,:2]@center+hull.equations[:,2]).max())
        contacts=[]
        for c in data.contact:
            a,b=[int(model.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
            if target in (a,b) and c.dist<=.0001:
                contacts.append({'other_body':model.body(b if a==target else a).name,'distance_m':float(c.dist)})
        results.append({'index':i,'sim_s':row['sim_s'],'bounds_world_m':{k:[v.min(0).tolist(),v.max(0).tolist()] for k,v in vertices.items()},
                        'box_com_xy_inside_basket_convex_footprint':outside<=0,'footprint_signed_margin_m':outside,
                        'geometry_contacts_only':contacts,'box_com_world_m':data.xipos[target].tolist()})
    assert results[-1]['box_com_xy_inside_basket_convex_footprint']
    assert results[-1]['geometry_contacts_only']
    assert all(c['other_body']=='brasket' for c in results[-1]['geometry_contacts_only'])
    # The recorded scene's native asset configurations are unchanged; restoration
    # validates all joint names/widths. No old action or tracker history is replayed.
    report={'actor_access':False,'diagnostic_only':True,'new_attempt_credit':False,
            'additional_physics_after_backend_initialization':0,
            'method':'Fresh geometry backend, named saved qpos restore and mj_forward only. Backend initialization settles the diagnostic copy; no policy or old actions replayed.',
            'trace_sha256':hashlib.sha256((ep/'video/robot_trace.jsonl').read_bytes()).hexdigest(),
            'samples':results,'limitations':'Convex footprint tests horizontal support containment, not full interior-volume containment. Contacts are reconstructed geometry, not new force evidence. Original recorder carries force/temporal evidence.'}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
finally:
    backend.close()
