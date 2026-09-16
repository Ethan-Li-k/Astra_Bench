"""Host-only comparison of recorded contacts with source mesh and convex hull."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from rsi.simple_environment import create_closed_door_backend
from rsi.simple_recording import restore_named_render_state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--episode', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.episode/'video/robot_trace.jsonl'
    raw = source.read_bytes()
    raw = raw[:raw.rfind(b'\n')+1]
    rows = [json.loads(line) for line in raw.splitlines()]
    candidates = []
    for row in rows:
        contacts = row['host_render_state'].get('external_robot_contacts_host_only', [])
        force = max((c['normal_force_n'] for c in contacts
                     if c['other_body'] == 'link_0'), default=0.)
        if force > 0:
            candidates.append((force, row))
    if not candidates:
        raise ValueError('No recorded fixed-frame contact to audit')
    force, row = max(candidates, key=lambda pair: pair[0])
    b = create_closed_door_backend(seed=args.seed, pd_profile='checkpoint', push_open=True)
    try:
        m, d = b.model, b.data
        restore_named_render_state(m, d, row['host_render_state'])
        geom = m.geom('link_0_collision').id
        mid = int(m.geom_dataid[geom])
        va, vn = int(m.mesh_vertadr[mid]), int(m.mesh_vertnum[mid])
        fa, fn = int(m.mesh_faceadr[mid]), int(m.mesh_facenum[mid])
        vertices = (m.mesh_vert[va:va+vn] @ d.geom_xmat[geom].reshape(3, 3).T
                    + d.geom_xpos[geom])
        mesh = trimesh.Trimesh(vertices=vertices, faces=m.mesh_face[fa:fa+fn], process=False)
        hull = mesh.convex_hull
        samples = []
        for c in d.contact:
            if geom not in (c.geom1, c.geom2):
                continue
            other = int(c.geom2 if c.geom1 == geom else c.geom1)
            if 'hand_' not in m.body(int(m.geom_bodyid[other])).name:
                continue
            point = np.asarray(c.pos).copy()
            _, original_distance, _ = trimesh.proximity.closest_point_naive(mesh, [point])
            _, hull_distance, _ = trimesh.proximity.closest_point_naive(hull, [point])
            origin = point - np.array([.25, 0., 0.])
            def intersections(surface):
                locations, _, _ = surface.ray.intersects_location([origin], [[1., 0., 0.]])
                return sorted(float(x) for x in locations[:, 0])
            samples.append({'robot_body': m.body(int(m.geom_bodyid[other])).name,
                'contact_position_world_m': point.tolist(),
                'collision_distance_m': float(c.dist),
                'distance_to_original_triangle_surface_m': float(original_distance[0]),
                'distance_to_convex_hull_surface_m': float(hull_distance[0]),
                'ray_origin_world_m': origin.tolist(), 'ray_direction': [1., 0., 0.],
                'original_mesh_ray_intersections_x_m': intersections(mesh),
                'convex_hull_ray_intersections_x_m': intersections(hull)})
        result = {'actor_access': False, 'state_reconstruction_only': True,
            'physical_attempt_credit': False, 'task_success_credit': False,
            'source_trace': str(source.resolve()), 'source_prefix_sha256': hashlib.sha256(raw).hexdigest(),
            'source_prefix_samples': len(rows), 'selected_sim_s': row['sim_s'],
            'recorded_max_frame_force_n': force, 'mesh_name': m.mesh(mid).name,
            'mesh_vertices': vn, 'mesh_faces': fn,
            'original_mesh_volume_m3': float(mesh.volume),
            'convex_hull_volume_m3': float(hull.volume),
            'moving_hinge_body': m.body(int(m.jnt_bodyid[m.joint('articulate_joint_1').id])).name,
            'contact_samples': samples,
            'limitation': 'Recorded qpos reconstruction; contact forces use the original recording, not reconstruction. No actor input or altered physical rollout.'}
        (args.output/'selected_recorded_state.json').write_text(json.dumps(row, indent=2)+'\n')
        (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    finally:
        b.close()


if __name__ == '__main__':
    main()
