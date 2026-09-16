"""Read-only USD structure audit using the already installed Isaac USD library."""
import argparse
import hashlib
import json
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics


def inspect(path):
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError('USD stage did not open: '+str(path))
    bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    rows = []
    for prim in stage.Traverse():
        row = {'path': str(prim.GetPath()), 'type': prim.GetTypeName(),
               'schemas': list(prim.GetAppliedSchemas())}
        if prim.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get()
            row['vertices'] = len(points) if points is not None else 0
            counts = mesh.GetFaceVertexCountsAttr().Get()
            row['faces'] = len(counts) if counts is not None else 0
            bounds = bbox.ComputeWorldBound(prim).ComputeAlignedRange()
            if not bounds.IsEmpty():
                row['world_bounds_stage_units'] = [list(bounds.GetMin()), list(bounds.GetMax())]
        if prim.IsA(UsdPhysics.Joint):
            joint = UsdPhysics.Joint(prim)
            row['joint_bodies'] = [list(map(str, joint.GetBody0Rel().GetTargets())),
                                   list(map(str, joint.GetBody1Rel().GetTargets()))]
        rows.append(row)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    return {'path': str(path), 'sha256': before, 'source_unchanged': True,
            'up_axis': str(UsdGeom.GetStageUpAxis(stage)),
            'meters_per_unit': UsdGeom.GetStageMetersPerUnit(stage),
            'default_prim': str(stage.GetDefaultPrim().GetPath()),
            'used_layers': [x.identifier for x in stage.GetUsedLayers()],
            'prims': rows}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result={'usd_version':Usd.GetVersion(),'actor_access':False,'new_physics_attempts':0,
            'new_task_successes':0,'assets':[inspect(x) for x in a.asset]}
    a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps({'output':str(a.output),'assets':len(result['assets']),
                      'prims':[len(x['prims']) for x in result['assets']]}))
