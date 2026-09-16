"""Robot-only native Dex3 mesh bounds; never object pose or contact information."""
import mujoco
import numpy as np
import hashlib
import json
from pathlib import Path


def finger_geometry(backend):
    model, data = backend.model, backend.data
    result = {}
    for side in ('left', 'right'):
        wrist = model.body(f'{side}_wrist_yaw_link').id
        origin = data.xpos[wrist];rotation = data.xmat[wrist].reshape(3, 3)
        result[side] = {}
        for finger, segment in (('thumb', 2), ('index', 1), ('middle', 1)):
            body = model.body(f'{side}_hand_{finger}_{segment}_link').id
            surfaces = []
            for gid in np.flatnonzero(model.geom_bodyid == body):
                if not (model.geom_contype[gid] or model.geom_conaffinity[gid]):
                    continue
                if model.geom_type[gid] != mujoco.mjtGeom.mjGEOM_MESH:
                    raise ValueError('Expected native distal finger collision mesh')
                mesh = model.geom_dataid[gid];start = model.mesh_vertadr[mesh]
                vertices = model.mesh_vert[start:start+model.mesh_vertnum[mesh]]
                world = vertices@data.geom_xmat[gid].reshape(3, 3).T+data.geom_xpos[gid]
                surfaces.append((world-origin)@rotation)
            if not surfaces:
                raise ValueError('Native distal finger collision geometry missing')
            points = np.concatenate(surfaces)
            result[side][finger] = {
                'geometry_kind': 'mesh_bounds_not_contact_surface_or_calibrated_TCP',
                'bounds_min_wrist_m': points.min(axis=0).tolist(),
                'bounds_max_wrist_m': points.max(axis=0).tolist(),
                'link_origin_wrist_m': ((data.xpos[body]-origin)@rotation).tolist()}
    return result


def hand_collision_model(backend):
    """Static body-local collision surfaces, restricted to the robot's hands."""
    import trimesh
    model, data = backend.model, backend.data
    selected = {model.body(f'{s}_wrist_yaw_link').id for s in ('left', 'right')}
    for body in range(model.nbody):
        if int(model.body_parentid[body]) in selected:
            selected.add(body)
    bodies = {}
    for body in sorted(selected):
        origin = data.xpos[body];rotation = data.xmat[body].reshape(3, 3)
        geoms = []
        for gid in np.flatnonzero(model.geom_bodyid == body):
            if not (model.geom_contype[gid] or model.geom_conaffinity[gid]):
                continue
            geom_rotation = data.geom_xmat[gid].reshape(3, 3)
            offset = (data.geom_xpos[gid]-origin)@rotation
            local_rotation = rotation.T@geom_rotation
            kind = int(model.geom_type[gid])
            item = {'name': model.geom(int(gid)).name,
                    'position_body_m': offset.tolist(),
                    'rotation_body_from_geom': local_rotation.tolist()}
            if kind == mujoco.mjtGeom.mjGEOM_MESH:
                mesh = int(model.geom_dataid[gid]);start = int(model.mesh_vertadr[mesh])
                vertices = model.mesh_vert[start:start+model.mesh_vertnum[mesh]]
                # MuJoCo's mesh contact uses a convex hull, not the potentially
                # concave visual/source triangle surface.
                hull = trimesh.convex.convex_hull(vertices)
                item.update(kind='convex_mesh',
                    vertices_body_m=(hull.vertices@local_rotation.T+offset).tolist(),
                    triangles=hull.faces.tolist())
            else:
                names = {int(mujoco.mjtGeom.mjGEOM_BOX): 'box',
                         int(mujoco.mjtGeom.mjGEOM_SPHERE): 'sphere',
                         int(mujoco.mjtGeom.mjGEOM_CAPSULE): 'capsule',
                         int(mujoco.mjtGeom.mjGEOM_CYLINDER): 'cylinder',
                         int(mujoco.mjtGeom.mjGEOM_ELLIPSOID): 'ellipsoid'}
                if kind not in names:
                    raise ValueError('Unsupported robot hand collision geometry')
                item.update(kind=names[kind], size_m=model.geom_size[gid].tolist())
            geoms.append(item)
        if geoms:
            bodies[model.body(body).name] = geoms
    return {'schema': 1, 'source': 'robot-only native collision geometry',
            'coordinates': 'Body-local metres. convex_mesh vertices already include geom transform; primitive sizes use MuJoCo half-size/radius/half-length convention.',
            'primitive_size_contract': {'box': 'three half extents along geom axes',
                'sphere': 'size[0] radius', 'capsule': 'size[0] radius, size[1] half straight segment along geom Z, spherical ends additional',
                'cylinder': 'size[0] radius, size[1] half length along geom Z',
                'ellipsoid': 'three semi-axis lengths'},
            'contains_object_or_contact_state': False, 'bodies': bodies,
            'limits': 'Geometric collision surfaces, not pressure/force, calibrated TCP or a grasp recipe. Combine with achieved body poses and current RGB; geometry does not certify contact or future tracking.'}


class HandGeometryProvider:
    """Persist geometry once in public rollout; refresh only robot link poses."""
    def __init__(self, output_dir):
        self.path = Path(output_dir)/'hand_collision_model.json'
        self.body_names = None

    def __call__(self, backend):
        result = finger_geometry(backend)
        if self.body_names is None:
            model = hand_collision_model(backend)
            raw = (json.dumps(model, separators=(',', ':'))+'\n').encode()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.read_bytes() != raw:
                raise ValueError('Refuse to overwrite different public hand geometry')
            self.path.write_bytes(raw)
            self.sha256 = hashlib.sha256(raw).hexdigest()
            self.body_names = tuple(model['bodies'])
        result['hand_collision_model'] = {
            'path': str(self.path.resolve()), 'sha256': self.sha256,
            'body_poses_world': {name: {
                'position_world_m': backend.data.xpos[backend.model.body(name).id].tolist(),
                'quaternion_wxyz': backend.data.xquat[backend.model.body(name).id].tolist()}
                for name in self.body_names},
            'scope': 'Own hand/palm/proximal/distal collision geometry and achieved robot poses only; no contact or object truth.'}
        return result
