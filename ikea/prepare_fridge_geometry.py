"""Host-only source geometry analysis. No physics stepping or actor access."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parent
SCENE = ROOT / 'scenes/usd-aligned-door-west-no-latch-v3/scene.xml'
SHIFT = np.array([-3.105, 3.02, 0.])
OUT = ROOT / 'engineering-evidence/fridge-source-geometry-v1'


def source_mesh(xml, index):
    item = xml.find(f"./asset/mesh[@name='mesh{index}']")
    vertices = np.fromstring(item.get('vertex'), sep=' ').reshape(-1, 3)
    faces = np.fromstring(item.get('face'), sep=' ', dtype=int).reshape(-1, 3)
    return vertices, faces


def contains(points, triangles):
    """Positive x ray parity; query yz values stay off the vertex grid."""
    values = []
    for point in points:
        hits = []
        for tri in triangles:
            if np.ptp(tri[:, 0]) > 1e-7:
                continue  # All source faces are axis aligned.
            x = tri[0, 0]
            if x <= point[0]:
                continue
            a, b, c = tri[:, 1:]
            det = np.linalg.det(np.column_stack((b-a, c-a)))
            if abs(det) < 1e-12:
                continue
            uv = np.linalg.solve(np.column_stack((b-a, c-a)), point[1:]-a)
            if min(uv) >= -1e-10 and sum(uv) <= 1+1e-10:
                hits.append(round(float(x), 7))
        values.append(bool(len(set(hits)) % 2))
    return np.array(values, dtype=bool)


def merge_cells(grid, occupied):
    """Exact disjoint union of occupied rectangular cells; deterministic."""
    remaining = {tuple(v) for v in np.argwhere(occupied)}
    boxes = []
    while remaining:
        low = np.array(min(remaining)); high = low+1
        for axis in (2, 1, 0):
            while high[axis] < occupied.shape[axis]:
                slab_low = low.copy(); slab_low[axis] = high[axis]
                slab_high = high.copy(); slab_high[axis] += 1
                cells = [tuple(slab_low+v) for v in np.ndindex(tuple(slab_high-slab_low))]
                if not all(c in remaining for c in cells):
                    break
                high[axis] += 1
        cells = [tuple(low+v) for v in np.ndindex(tuple(high-low))]
        remaining.difference_update(cells)
        boxes.append((np.array([grid[a][low[a]] for a in range(3)]),
                      np.array([grid[a][high[a]] for a in range(3)])))
    return boxes


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    xml = ET.parse(SCENE).getroot()
    pieces = [source_mesh(xml, n) for n in (124, 125)]
    # FBX converted coordinates differ by sub-micrometre export noise.
    triangles = np.concatenate([v[f] for v, f in pieces])
    rounded = np.round(triangles, 5)
    tolerance_error = float(abs(rounded-triangles).max())
    assert tolerance_error < 3e-6
    assert all(any(np.ptp(tri[:, a]) < 1e-10 for a in range(3)) for tri in rounded)
    edges = Counter()
    for tri in rounded:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((tuple(tri[a]), tuple(tri[b]))))] += 1
    assert set(edges.values()) == {2}, 'Source case must be a closed manifold after tolerance weld'
    grid = [np.unique(rounded[:, :, a]) for a in range(3)]
    shape = tuple(len(g)-1 for g in grid)
    cells = list(np.ndindex(shape))
    samples = np.array([[grid[a][i[a]]+.371*(grid[a][i[a]+1]-grid[a][i[a]])
                         for a in range(3)] for i in cells])
    occupied = contains(samples, rounded).reshape(shape)
    boxes = merge_cells(grid, occupied)
    # Independently sample a different interior point of every source grid cell.
    alternate = np.array([[grid[a][i[a]]+(.617,.413,.283)[a]*(grid[a][i[a]+1]-grid[a][i[a]])
                           for a in range(3)] for i in cells])
    union = np.array([any(np.all(p > lo) and np.all(p < hi) for lo, hi in boxes) for p in alternate])
    source = contains(alternate, rounded)
    assert np.array_equal(source, union)
    assert np.array_equal(source, occupied.ravel())
    # Three source inner surfaces, no invented shelf.
    cavities = [([.235,-6.43,.08],[.685,-5.68,.465]),
                ([.235,-6.43,.515],[.685,-5.68,.825]),
                ([.155,-6.408,.89],[.685,-5.702,1.785])]
    assert not contains(np.array([(np.array(lo)+hi)/2 for lo,hi in cavities]), rounded).any()
    doors = []
    for n, name, sign in ((126,'Door_Top_L',-1),(127,'Door_Top_R',1)):
        v,f = source_mesh(xml,n); lo=v.min(0); hi=v.max(0)
        hinge=np.array([lo[0],lo[1] if n==126 else hi[1],lo[2]])
        doors.append(dict(source_mesh=f'mesh{n}',source_node=name,vertices=len(v),triangles=len(f),
            bounds_usd_m=[(lo+SHIFT).tolist(),(hi+SHIFT).tolist()],
            source_geometry='Plain rectangular slab; no distinct protruding handle in this source node',
            proposed_hinge_usd_m=(hinge+SHIFT).tolist(),proposed_opening_sign=sign,
            hinge_status='Engineering hypothesis at outer rear edge; source stage authors no joint'))
    report=dict(actor_access=False,kind='static_source_analysis',physical_attempts=0,success_credit=0,
        source_scene=str(SCENE),source_scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
        usd_metadata='source-usd-audit/report.json',source_meshes=[124,125],source_triangles=len(triangles),
        welded_edge_incidence=dict(Counter(edges.values())),snap_tolerance_m=1e-5,
        maximum_source_vertex_change_m=tolerance_error,source_grid_shape=shape,
        occupied_cells=int(occupied.sum()),unoccupied_cells=int((~occupied).sum()),
        partition_checks='All source grid cells checked at two distinct interior sample positions',
        collision_boxes_usd_m=[dict(min=(lo+SHIFT).tolist(),max=(hi+SHIFT).tolist()) for lo,hi in boxes],
        source_inner_cavities_usd_m=[dict(min=(np.array(lo)+SHIFT).tolist(),max=(np.array(hi)+SHIFT).tolist()) for lo,hi in cavities],
        doors=doors,notes=['Source visual mesh stays unmodified; only future collision partition snaps export noise.',
            'Current apple/door scenes and actor have not been changed.',
            'Inner surfaces exist in the source; original convex case collision fills them and must be replaced for placement.',
            'No source hinge, mass, gasket or opening torque has been validated; next candidate must declare these.',
            'No independent handle is added; opening must use the visible door edge in this geometry.'])
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('kind','source_grid_shape','occupied_cells','unoccupied_cells','maximum_source_vertex_change_m')}))
    print(json.dumps(dict(collision_boxes=len(boxes),doors=doors)))


if __name__ == '__main__':
    main()
