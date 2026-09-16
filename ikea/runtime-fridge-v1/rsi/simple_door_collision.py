"""RSI-only exact rectangular-frame collision override for SIMPLE asset003.

The source frame is a rectangular ring. One MuJoCo mesh convexifies its hole.
Four boxes reproduce the ring solid, retaining the original visual/inertial geom.
"""
import hashlib
from pathlib import Path

import mujoco
import numpy as np
import trimesh

FRAME_SHA256 = 'bd01dac54cb36a782dcb5d589cc7b8e4faaaffff6ecd4ade70358ee8a50679a1'
OVERRIDE_ID = 'asset003-exact-frame-four-boxes-v1'


def frame_boxes(source):
    source = Path(source)
    if hashlib.sha256(source.read_bytes()).hexdigest() != FRAME_SHA256:
        raise ValueError('Unreviewed asset003 frame source; refuse collision override')
    mesh = trimesh.load(source, process=True)
    vertices = np.unique(mesh.vertices, axis=0)
    axes = [np.unique(vertices[:, i]) for i in range(3)]
    if [len(a) for a in axes] != [4, 4, 2] or len(vertices) != 16:
        raise ValueError('Expected audited rectangular frame vertex topology')
    x, y, z = axes
    lo, hi = z
    bounds = [([x[0], y[0], lo], [x[1], y[3], hi]),
              ([x[2], y[0], lo], [x[3], y[3], hi]),
              ([x[1], y[0], lo], [x[2], y[1], hi]),
              ([x[1], y[2], lo], [x[2], y[3], hi])]
    return [{'position': ((np.array(a)+b)/2).tolist(),
             'half_size': ((np.array(b)-a)/2).tolist()} for a, b in bounds]


def apply_frame_override(spec, source):
    boxes = frame_boxes(source)
    old = spec.geom('link_0_collision')
    if old.meshname != 'collision_original-1':
        raise ValueError('Unexpected frame collision mesh')
    if not (np.allclose(old.pos, 0) and np.allclose(old.quat, [1, 0, 0, 0])):
        raise ValueError('Frame mesh transform differs from audited source')
    contact = {name: getattr(old, name) for name in
               ('contype', 'conaffinity', 'condim', 'group', 'priority',
                'friction', 'solref', 'solimp', 'solmix', 'margin', 'gap')}
    for i, box in enumerate(boxes):
        spec.body('link_0').add_geom(name=f'rsi_door_frame_bar_{i}',
            type=mujoco.mjtGeom.mjGEOM_BOX, pos=box['position'], size=box['half_size'],
            mass=0., density=0., **contact)
    # Keep its mass/inertia contribution and source geometry; only disable the
    # invalid solid convex collision hull. The fixed frame remains collidable.
    old.contype = old.conaffinity = 0
    return {'id': OVERRIDE_ID, 'source_mesh_sha256': FRAME_SHA256,
            'source_mesh': str(Path(source).resolve()), 'boxes_in_source_mesh_frame': boxes,
            'original_asset_files_modified': False,
            'visual_geometry_unchanged': True, 'moving_leaf_and_handle_unchanged': True,
            'original_convex_hull_disabled': True,
            'scope': 'Fixed-frame collision hole repair; explicitly different collision representation from original MuJoCo mesh.'}


def install_frame_override(env):
    engine = env.unwrapped.mujoco
    original = engine._build_articulated_object
    def build(spec, world, actor):
        original(spec, world, actor)
        source = Path(actor.asset.mjcf_path).parent/'meshes/textured_objs/original-1.stl'
        engine.rsi_frame_collision_override = apply_frame_override(spec, source)
    engine._build_articulated_object = build
