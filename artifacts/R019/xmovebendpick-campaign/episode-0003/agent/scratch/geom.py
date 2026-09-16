from control import *
def meshes(o,side):
 g=json.load(open(o['finger_geometry']['hand_collision_model']['path'])); poses=o['finger_geometry']['hand_collision_model']['body_poses_world'];out={}
 for name,geoms in g['bodies'].items():
  if not name.startswith(side):continue
  pts=[]
  for geom in geoms:
   if geom['kind']=='convex_mesh':v=np.array(geom['vertices_body_m'])
   elif geom['kind']=='box':
    import itertools
    v=np.array(list(itertools.product([-1,1],repeat=3)))*geom['size_m'];v=v@np.array(geom['rotation_body_from_geom']).T+geom['position_body_m']
   else:raise ValueError(geom['kind'])
   po=poses[name];pts.extend(rotation(po['quaternion_wxyz']).apply(v)+po['position_world_m'])
  out[name]=np.array(pts)
 return out
if __name__=='__main__':
 _,o=obs()
 for side in ['left','right']:
  for n,v in meshes(o,side).items():print(n,np.round(v.min(0),4),np.round(v.max(0),4))
