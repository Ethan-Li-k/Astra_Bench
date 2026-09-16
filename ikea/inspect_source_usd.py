"""One bounded read-only compatibility audit with an isolated usd-core install."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'compat-usd'))
from pxr import Usd,UsdGeom,UsdPhysics

ROOT=Path(__file__).resolve().parent
SOURCE=Path('/home/galbot/Downloads/APA/IKEA_LivingRoom_Mesh_0915')
def inspect(path):
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    stage=Usd.Stage.Open(str(path))
    if stage is None:raise RuntimeError('Stage did not open')
    cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy'])
    rows=[]
    for prim in stage.Traverse():
        p=str(prim.GetPath());row=dict(path=p,type=prim.GetTypeName(),schemas=list(prim.GetAppliedSchemas()))
        attrs={}
        for a in prim.GetAttributes():
            name=a.GetName()
            if a.HasAuthoredValueOpinion() and (name.startswith(('physics:','physx','drive:','limit:'))):
                val=a.Get();attrs[name]=val if isinstance(val,(int,float,str,bool,type(None))) else str(val)
        if attrs:row['authored_physics']=attrs
        if prim.IsA(UsdPhysics.Joint):
            row['joint_bodies']={r.GetName():list(map(str,r.GetTargets())) for r in prim.GetRelationships()}
        if any(t in p.lower() for t in ('door','handle','drawer','apple','refrigerator','bath')):
            if prim.IsA(UsdGeom.Boundable):
                bound=cache.ComputeWorldBound(prim).ComputeAlignedRange()
                if not bound.IsEmpty():row['world_bounds_stage_units']=[list(bound.GetMin()),list(bound.GetMax())]
            if prim.IsA(UsdGeom.Xformable):
                x=UsdGeom.Xformable(prim)
                row['world_transform']=str(x.ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        rows.append(row)
    unchanged=before==hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(path=str(path),sha256=before,source_unchanged=unchanged,up_axis=str(UsdGeom.GetStageUpAxis(stage)),
        meters_per_unit=UsdGeom.GetStageMetersPerUnit(stage),used_layers=[l.identifier for l in stage.GetUsedLayers()],
        prim_count=len(rows),joint_count=sum('joint_bodies' in r for r in rows),
        physics_prim_count=sum(bool(r['schemas']) or 'authored_physics' in r for r in rows),prims=rows)

def main():
    out=ROOT/'source-usd-audit';out.mkdir(exist_ok=False)
    result=dict(usd_version=Usd.GetVersion(),backend='USD read-only metadata audit, no Isaac execution',assets=[],errors=[],actor_access=False)
    for relative in ['IKEA_LivingRoom_Mesh_0915.usd','IKEA_LivingRoom_Mesh_0915_Props.usd',
                     'IKEA_LivingRoom_Mesh_0915_Props_Flatten.usd','Props/apple/apple.usd']:
        try:
            asset=inspect(SOURCE/relative);result['assets'].append(asset)
            print(json.dumps({k:asset[k] for k in ('path','prim_count','joint_count','physics_prim_count','meters_per_unit','up_axis')}),flush=True)
        except Exception as e:
            error=dict(path=relative,error_type=type(e).__name__,error=str(e));result['errors'].append(error);print(json.dumps(error),flush=True)
        (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
