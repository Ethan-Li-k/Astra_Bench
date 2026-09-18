"""Bounded reads of the exact robot-hand geometry issued in the latest observation."""
import hashlib
import json
import math
import re
from pathlib import Path

LIMIT = 200000


def encoded(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


def local_bounds(part):
    if part['kind'] == 'convex_mesh':
        vertices = part['vertices_body_m']
        return [min(v[i] for v in vertices) for i in range(3)], [max(v[i] for v in vertices) for i in range(3)]
    center, rotation, size = part['position_body_m'], part['rotation_body_from_geom'], part['size_m']
    extent = []
    for row in rotation:
        kind = part['kind']
        if kind == 'box': e = sum(abs(row[i])*size[i] for i in range(3))
        elif kind == 'sphere': e = size[0]
        elif kind == 'capsule': e = size[0]+abs(row[2])*size[1]
        elif kind == 'cylinder': e = size[0]*math.hypot(row[0], row[1])+abs(row[2])*size[1]
        elif kind == 'ellipsoid': e = math.sqrt(sum((row[i]*size[i])**2 for i in range(3)))
        else: raise ValueError('Unsupported hand primitive')
        extent.append(e)
    return [center[i]-extent[i] for i in range(3)], [center[i]+extent[i] for i in range(3)]


def read_hand_geometry(latest_path, arguments):
    """Return None for other paths; never authorize an unissued file."""
    observation = json.loads(Path(latest_path).read_text())
    reference = observation.get('finger_geometry', {}).get('hand_collision_model', {})
    if arguments.get('path') != reference.get('path') or not reference.get('path'):
        return None
    def reject(reason):
        return dict(read_rejected=reason, no_physical_action=True)
    if set(arguments)-{'path', 'body', 'part'}:
        return reject('Only path, one named body, and optional part index are supported.')
    path = Path(reference['path']); latest = Path(latest_path).resolve()
    # Geometry lives beside this episode's observation directory, not in a
    # caller-selected root. Reject symlink traversal before reading bytes.
    if (path.name != 'hand_collision_model.json' or latest.parent.parent.name != 'observations'
            or path.parent != latest.parents[2]):
        return reject('Geometry must belong to this observation episode.')
    if any(p.is_symlink() for p in (path, *path.parents)) or path.stat().st_size > 8000000:
        return reject('Invalid geometry source path or size.')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference.get('sha256'):
        return reject('Geometry SHA does not match the current public observation.')
    document = json.loads(raw)
    allowed = re.compile(r'(left|right)_(wrist_yaw_link|hand_(thumb_[012]|index_[01]|middle_[01])_link)')
    if (document.get('source') != 'robot-only native collision geometry'
            or document.get('contains_object_or_contact_state') is not False
            or not document.get('bodies')
            or any(not allowed.fullmatch(b) for b in document['bodies'])):
        return reject('Only the issued robot-hand geometry schema is permitted.')
    part_keys = {'name', 'position_body_m', 'rotation_body_from_geom', 'kind', 'size_m', 'vertices_body_m', 'triangles'}
    if any(set(p)-part_keys for parts in document['bodies'].values() for p in parts):
        return reject('Unexpected fields in robot-hand geometry.')
    result = dict(path=str(path), source_sha256=reference['sha256'], coordinates=document['coordinates'],
                  limits='Local bounds are not contact surfaces. Geometry never certifies contact or retention.')
    if 'body' in arguments:
        body = arguments['body']
        if not isinstance(body, str) or body not in document['bodies']:
            return reject('Select one body named in the issued bounds index.')
        parts = document['bodies'][body]
        if 'part' in arguments:
            index = arguments['part']
            if type(index) is not int or not 0 <= index < len(parts):
                return reject('Select an issued integer part index for this body.')
            parts = [parts[index]]
        result.update(body=body, geometry=parts, primitive_size_contract=document['primitive_size_contract'])
    else:
        if 'part' in arguments: return reject('A part index requires its named body.')
        bodies = {}
        for body, parts in document['bodies'].items():
            rows = []
            for index, part in enumerate(parts):
                low, high = local_bounds(part)
                rows.append(dict(part=index, name=part['name'], kind=part['kind'],
                    bounds_min_body_m=low, bounds_max_body_m=high,
                    vertex_count=len(part.get('vertices_body_m', [])),
                    part_sha256=hashlib.sha256(encoded(part)).hexdigest(),
                    raw_bytes=len(encoded(part))))
            bodies[body] = rows
        result.update(bodies=bodies, usage='Add body for unchanged raw geometry; optional part selects one indexed part. Each response is capped at 200000 bytes.')
    if len(encoded(result)) > LIMIT:
        return reject('Named geometry exceeds 200000 bytes; use one smaller indexed part or the bounds index. Original mesh is unchanged.')
    return result
