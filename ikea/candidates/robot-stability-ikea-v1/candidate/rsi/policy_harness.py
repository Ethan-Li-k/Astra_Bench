"""GPT-as-Policy-style tool boundary for the local UMI-4 simulation."""
import json
from pathlib import Path
from typing import Protocol

import numpy as np
from scipy.spatial.transform import Rotation

from rsi.four_point import FOUR_POINT_NAMES, FourPointPose


class FourPointBackend(Protocol):
    """Contract that the local MuJoCo and future SIMPLE backends must implement."""

    def observe(self): ...
    def move_four_points(self, observation_id, command_id, targets, duration=1.,
                         position_names=FOUR_POINT_NAMES,
                         orientation_names=FOUR_POINT_NAMES): ...
    def set_grippers(self, left, right, duration=0.): ...
    def tick(self): ...
    def status(self): ...


class Pi05Provider(Protocol):
    """A task-trained policy must return the same direct-response contract."""

    def audit(self): ...
    def infer(self, observation, task): ...


def _object(properties):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(properties)}


def direct_response_schema():
    number = {'type': 'number'}
    vector3 = {'type': 'array', 'items': number, 'minItems': 3, 'maxItems': 3}
    vector4 = {'type': 'array', 'items': number, 'minItems': 4, 'maxItems': 4}
    point = _object({'position_world_m': vector3, 'quaternion_wxyz': vector4})
    target = _object({name: point for name in FOUR_POINT_NAMES})
    names = {'type': 'array',
             'items': {'type': 'string', 'enum': list(FOUR_POINT_NAMES)},
             'uniqueItems': True, 'minItems': 0, 'maxItems': 4}
    waypoint = _object({'target': target,
                        'active': _object({'position': names, 'orientation': names}),
                        'duration_s': {'type': 'number', 'minimum': .5, 'maximum': 3.},
                        'grippers': _object({'left': {'type': 'number', 'minimum': 0, 'maximum': 1},
                                             'right': {'type': 'number', 'minimum': 0, 'maximum': 1}})})
    return _object({'request_id': {'type': 'string'},
                    'mode': {'type': 'string', 'enum': ['four_point']},
                    'trajectory': {'type': 'array', 'items': waypoint, 'minItems': 1, 'maxItems': 5},
                    'reason': {'type': 'string'}})


def tool_specs(method='direct'):
    string = {'type': 'string'}
    number = {'type': 'number'}
    vector2 = {'type': 'array', 'items': number, 'minItems': 2, 'maxItems': 2}
    vector3 = {'type': 'array', 'items': number, 'minItems': 3, 'maxItems': 3}
    names = {'type': 'array',
             'items': {'type': 'string', 'enum': list(FOUR_POINT_NAMES)},
             'uniqueItems': True, 'minItems': 1, 'maxItems': 4}
    start = {'type': 'function', 'name': 'loco_start',
             'description': 'Start one recorded loco-manip episode and return fresh RGB/proprio.',
             'inputSchema': _object({'task': string, 'output_dir': string})}
    translate = {'type': 'function', 'name': 'four_point_translate',
                 'description': 'Compile a named world-frame xyz translation from the latest observation; do not execute it.',
                 'inputSchema': _object({'observation_path': string, 'names': names,
                                         'delta_world_m': vector3, 'output_dir': string})}
    rotate = {'type': 'function', 'name': 'four_point_rotate',
              'description': 'Compile a named world-frame axis-angle rotation about a pivot; do not execute it.',
              'inputSchema': _object({'observation_path': string, 'names': names,
                                      'rotation_vector_world_rad': vector3,
                                      'pivot_world_m': vector3, 'output_dir': string})}
    project = {'type': 'function', 'name': 'image_pixel_to_world_plane',
               'description': 'Project one visible image pixel onto an explicitly declared calibrated horizontal work plane; do not detect objects or execute motion.',
               'inputSchema': _object({
                   'observation_path': string, 'camera': string,
                   'pixel_xy': vector2, 'horizontal_plane_z_m': number,
                   'output_dir': string})}
    place = {'type': 'function', 'name': 'four_point_place_local_point',
             'description': 'Compile a wrist position that places one explicitly declared link-local point at a world point; this is not a calibrated TCP and does not execute.',
             'inputSchema': _object({
                 'observation_path': string,
                 'link_name': {'type': 'string', 'enum': list(FOUR_POINT_NAMES[:2])},
                 'point_position_world_m': vector3,
                 'point_offset_link_m': vector3,
                 'output_dir': string})}
    act = {'type': 'function', 'name': 'scalebfm_act',
           'description': 'Execute one reviewed 1-5 waypoint UMI-4 chunk, then return fresh RGB/proprio and outcome.',
           'inputSchema': _object({'observation_path': string,
                                   'response': direct_response_schema(), 'output_dir': string})}
    if method == 'direct':
        return [start, translate, rotate, project, place, act]
    if method != 'pi05_plus_gpt':
        raise ValueError('method must be direct or pi05_plus_gpt')
    infer = {'type': 'function', 'name': 'pi05_infer',
             'description': 'Infer one fresh task-trained humanoid pi0.5 four-point proposal without executing it.',
             'inputSchema': _object({'observation_path': string, 'output_dir': string})}
    execute = {'type': 'function', 'name': 'loco_execute',
               'description': 'Validate and execute the GPT-reviewed final four-point chunk for one fresh pi0.5 proposal.',
               'inputSchema': _object({'proposal_path': string,
                                       'response': direct_response_schema(),
                                       'output_dir': string})}
    return [start, translate, rotate, project, place, infer, execute]


def _strict(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label} must contain exactly {tuple(keys)}')


def validate_response(response):
    """Validate and normalize one direct or pi0.5-authored UMI-4 chunk."""
    _strict(response, ('request_id', 'mode', 'trajectory', 'reason'), 'response')
    if not isinstance(response['request_id'], str) or not response['request_id']:
        raise ValueError('request_id must be a nonempty string')
    if response['mode'] != 'four_point':
        raise ValueError('mode must be four_point')
    if not isinstance(response['reason'], str):
        raise ValueError('reason must be a string')
    rows = response['trajectory']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
        raise ValueError('trajectory must contain 1..5 waypoints')
    normalized = []
    for i, row in enumerate(rows):
        _strict(row, ('target', 'active', 'duration_s', 'grippers'), f'trajectory[{i}]')
        target = FourPointPose.from_mapping(row['target'])
        _strict(row['active'], ('position', 'orientation'), 'active')
        active = {}
        for component in ('position', 'orientation'):
            names = row['active'][component]
            if (not isinstance(names, list) or len(names) != len(set(names))
                    or not set(names) <= set(FOUR_POINT_NAMES)):
                raise ValueError(f'active {component} names must be unique known four-point links')
            active[component] = tuple(names)
        duration = float(row['duration_s'])
        if not np.isfinite(duration) or not .5 <= duration <= 3.:
            raise ValueError('duration_s must be within [0.5,3.0]')
        _strict(row['grippers'], ('left', 'right'), 'grippers')
        grippers = {name: float(row['grippers'][name]) for name in ('left', 'right')}
        if not all(np.isfinite(v) and 0 <= v <= 1 for v in grippers.values()):
            raise ValueError('gripper closure must be finite within [0,1]')
        normalized.append(dict(target=target, active=active,
                               duration_s=duration, grippers=grippers))
    return dict(request_id=response['request_id'], mode='four_point',
                trajectory=normalized, reason=response['reason'])


def validate_pi05_capability(value):
    """Require a vision-enabled, task-trained humanoid student before Hybrid."""
    keys = ('status', 'policy_role', 'task_skill_id', 'observation_contract',
            'action_contract', 'vision_inputs', 'checkpoint_sha256',
            'normalizer_sha256')
    try:
        _strict(value, keys, 'pi0.5 capability')
    except ValueError as error:
        raise ValueError(f'pi0.5 capability rejected: {error}') from error
    expected = {
        'status': 'ready',
        'policy_role': 'task_trained_humanoid_pi05',
        'observation_contract': 'rgb_plus_named_robot_state',
        'action_contract': 'umi4_se3_plus_bimanual_gripper',
    }
    for key, required in expected.items():
        if value[key] != required:
            raise ValueError(f'pi0.5 capability rejected: {key} must be {required!r}')
    if not isinstance(value['task_skill_id'], str) or not value['task_skill_id']:
        raise ValueError('pi0.5 capability rejected: task_skill_id is required')
    cameras = value['vision_inputs']
    if (not isinstance(cameras, list) or not cameras
            or len(cameras) != len(set(cameras))
            or not all(isinstance(name, str) and name for name in cameras)
            or 'head_rgb' not in cameras):
        raise ValueError('pi0.5 capability rejected: head_rgb must be enabled')
    for key in ('checkpoint_sha256', 'normalizer_sha256'):
        digest = value[key]
        try:
            valid = isinstance(digest, str) and len(digest) == 64
            int(digest, 16)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError(f'pi0.5 capability rejected: {key} must be sha256')
    return dict(value)


def translate_target(observation, delta_world_m, *, names=FOUR_POINT_NAMES):
    """Compile a named world translation from a fresh actor observation."""
    return FourPointPose.from_mapping(observation['four_point_world']).translated(
        delta_world_m, names=names).to_mapping()


def rotate_target(observation, rotation_vector_world_rad, pivot_world_m, *, names=FOUR_POINT_NAMES):
    """Compile a named world rotation about a world-frame pivot."""
    return FourPointPose.from_mapping(observation['four_point_world']).rotated(
        rotation_vector_world_rad, pivot_world_m, names=names).to_mapping()


def wrist_pose_for_local_point(point_position_world_m, wrist_quaternion_wxyz,
                               point_offset_wrist_m):
    """Compile a wrist pose that places one declared wrist-local point in world."""
    point = np.asarray(point_position_world_m, dtype=float)
    quat = np.asarray(wrist_quaternion_wxyz, dtype=float)
    offset = np.asarray(point_offset_wrist_m, dtype=float)
    if point.shape != (3,) or offset.shape != (3,) or quat.shape != (4,):
        raise ValueError('point/offset must be xyz and wrist quaternion must be wxyz')
    if not np.isfinite(np.r_[point, quat, offset]).all() or not np.isclose(
            np.linalg.norm(quat), 1., atol=1e-4):
        raise ValueError('local-point transform must be finite with a unit quaternion')
    quat = quat/np.linalg.norm(quat)
    rotation = Rotation.from_quat(quat[[1, 2, 3, 0]])
    return {'position_world_m': (point-rotation.apply(offset)).tolist(),
            'quaternion_wxyz': quat.tolist()}


def pixel_to_horizontal_plane(calibration, pixel_xy, horizontal_plane_z_m):
    """Intersect a calibrated RGB ray with a declared world-Z work plane."""
    keys = ('width_px', 'height_px', 'fovy_deg', 'position_world_m',
            'rotation_camera_to_world_row_major', 'optical_convention')
    if 'render_intrinsics' in calibration:
        keys += ('render_intrinsics',)
    _strict(calibration, keys, 'camera calibration')
    width, height = calibration['width_px'], calibration['height_px']
    if (type(width) is not int or type(height) is not int
            or width <= 0 or height <= 0):
        raise ValueError('camera image dimensions must be positive integers')
    fovy = float(calibration['fovy_deg'])
    position = np.asarray(calibration['position_world_m'], dtype=float)
    rotation = np.asarray(
        calibration['rotation_camera_to_world_row_major'], dtype=float)
    pixel = np.asarray(pixel_xy, dtype=float)
    plane_z = float(horizontal_plane_z_m)
    if (position.shape != (3,) or rotation.shape != (9,) or pixel.shape != (2,)
            or not np.isfinite(np.r_[position, rotation, pixel, fovy, plane_z]).all()
            or not 0 < fovy < 180
            or not (0 <= pixel[0] < width and 0 <= pixel[1] < height)):
        raise ValueError('invalid finite camera, pixel, or plane values')
    if calibration['optical_convention'] != 'x_right_y_up_minus_z_forward':
        raise ValueError('unsupported camera optical convention')
    rotation = rotation.reshape(3, 3)
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5):
        raise ValueError('camera rotation must be orthonormal')
    intrinsics = calibration.get('render_intrinsics')
    if intrinsics is not None:
        fx, fy, cx, cy = [float(intrinsics[k]) for k in ('fx', 'fy', 'cx', 'cy')]
        if not np.isfinite([fx, fy, cx, cy]).all() or min(fx, fy) <= 0:
            raise ValueError('Invalid render intrinsics')
    else:
        fx = fy = height / (2 * np.tan(np.deg2rad(fovy)/2))
        cx, cy = width / 2, height / 2
    direction_camera = np.array([(pixel[0]+.5-cx)/fx,
                                 (cy-pixel[1]-.5)/fy, -1.])
    direction_world = rotation @ direction_camera
    if abs(direction_world[2]) < 1e-8:
        raise ValueError('camera ray is parallel to horizontal plane')
    distance = (plane_z-position[2])/direction_world[2]
    if distance <= 0:
        raise ValueError('horizontal plane lies behind the camera ray')
    return (position + distance*direction_world).tolist()


def _public_robot_root(packet):
    """Copy only finite, named robot BODY feedback; never merge backend extras."""
    value = packet.get('robot_root')
    if (not isinstance(value, dict) or value.get('body_name') != 'pelvis'
            or value.get('frame') != 'world'):
        return None
    height, tilt = value.get('height_world_m'), value.get('tilt_deg')
    quat = value.get('quaternion_wxyz')
    numeric = lambda x: type(x) in (int, float) and np.isfinite(x)
    if (not numeric(height) or not numeric(tilt) or not 0 <= tilt <= 180
            or not isinstance(quat, list) or len(quat) != 4
            or not all(numeric(x) for x in quat)
            or not np.isclose(np.linalg.norm(quat), 1., atol=1e-6)):
        return None
    return {'body_name': 'pelvis', 'frame': 'world', 'height_world_m': float(height),
            'quaternion_wxyz': list(quat), 'tilt_deg': float(tilt)}


def _robot_root_summary(samples):
    # Local to this executed chunk. Never cache a previous episode/sample.
    unavailable = {'status': 'unavailable'}
    if not samples:
        return unavailable
    roots = [_public_robot_root(row) for row in samples]
    times = [row.get('sim_s') for row in samples]
    episode = samples[0].get('episode_id')
    if (not isinstance(episode, str) or not episode or any(r is None for r in roots)
            or any(type(t) not in (int, float) or not np.isfinite(t) for t in times)
            or any(row.get('episode_id') != episode
                   or not isinstance(row.get('observation_id'), str)
                   or not row['observation_id'] for row in samples)
            or any(b <= a for a, b in zip(times, times[1:]))):
        return unavailable
    if len(samples) < 2:
        return {'status': 'insufficient_samples'}
    return {'status': 'sampled', 'episode_id': episode, 'samples': len(samples),
            'start_sim_s': times[0], 'end_sim_s': times[-1],
            'height_change_m': roots[-1]['height_world_m'] - roots[0]['height_world_m'],
            'tilt_change_deg': roots[-1]['tilt_deg'] - roots[0]['tilt_deg'],
            'min_height_world_m': min(r['height_world_m'] for r in roots),
            'max_tilt_deg': max(r['tilt_deg'] for r in roots),
            'limitation': 'Measured samples only; extrema between samples are unknown.'}


class LocalFourPointHarness:
    """Blocking recorded rollout. The caller owns any policy/model invocation."""

    def __init__(self, backend: FourPointBackend, output_dir, *, pi05: Pi05Provider | None = None,
                 image_capture=None, evaluator=None):
        self.backend = backend
        self.output_dir = Path(output_dir)
        self.pi05 = pi05
        self.image_capture = image_capture
        self.evaluator = evaluator
        self.task = None
        self.latest_path = None
        self.pending_proposal_path = None
        self.pending_proposal_observation_path = None
        self.pi05_capability = None
        self.index = 0

    def _write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2))

    def _capture(self):
        observation = self.backend.observe()
        if 'robot_root' in observation:
            observation['robot_root'] = _public_robot_root(observation)
            observation['episode_id'] = str(self.output_dir.resolve())
        directory = self.output_dir/'observations'/f'{self.index:04d}'
        directory.mkdir(parents=True, exist_ok=True)
        observation['images'] = self.image_capture(directory) if self.image_capture else []
        path = directory/'observation.json'
        self._write_json(path, observation)
        self.latest_path = path.resolve()
        self.index += 1
        return dict(observation_path=str(self.latest_path), observation=observation,
                    native_outcome=(self.evaluator.outcome(self.backend)
                                    if self.evaluator else 'not_configured'),
                    next_call='scalebfm_act or pi05_infer')

    def start(self, task):
        if self.task is not None:
            raise ValueError('Episode already started')
        if not isinstance(task, str) or not task.strip():
            raise ValueError('task must be a nonempty string')
        if self.pi05 is not None:
            audit = getattr(self.pi05, 'audit', None)
            if not callable(audit):
                raise ValueError('pi0.5 capability rejected: audit() is required')
            self.pi05_capability = validate_pi05_capability(audit())
        self.task = task
        self.output_dir.mkdir(parents=True, exist_ok=False)
        if self.evaluator:
            self.evaluator.reset(self.backend)
        self._write_json(self.output_dir/'manifest.json', {
            'task': task, 'backend': type(self.backend).__name__, 'tracker_mode': 'UMI-4',
            'four_point_names': list(FOUR_POINT_NAMES),
            'pi05': 'connected' if self.pi05 else 'not_connected',
            'llm_calls': None, 'llm_accounting_owner': 'policy_caller',
            'pi05_capability': self.pi05_capability,
        })
        return self._capture()

    def _require_latest(self, observation_path):
        if self.latest_path is None or Path(observation_path).resolve() != self.latest_path:
            raise ValueError('Only the latest observation_path may be used')

    @staticmethod
    def _geometry_names(names):
        if (not isinstance(names, list) or not names
                or len(names) != len(set(names))
                or not set(names) <= set(FOUR_POINT_NAMES)):
            raise ValueError('names must be a nonempty list of unique four-point links')
        return tuple(names)

    def compile_translation(self, observation_path, names, delta_world_m):
        self._require_latest(observation_path)
        names = self._geometry_names(names)
        observation = json.loads(self.latest_path.read_text())
        return {'source_observation_path': str(self.latest_path),
                'target': translate_target(observation, delta_world_m, names=names),
                'active': {'position': list(names), 'orientation': []},
                'next_call': 'scalebfm_act'}

    def compile_rotation(self, observation_path, names, rotation_vector_world_rad,
                         pivot_world_m):
        self._require_latest(observation_path)
        names = self._geometry_names(names)
        observation = json.loads(self.latest_path.read_text())
        return {'source_observation_path': str(self.latest_path),
                'target': rotate_target(observation, rotation_vector_world_rad,
                                        pivot_world_m, names=names),
                'active': {'position': list(names), 'orientation': list(names)},
                'next_call': 'scalebfm_act'}

    def compile_pixel_to_plane(self, observation_path, camera, pixel_xy,
                               horizontal_plane_z_m):
        self._require_latest(observation_path)
        observation = json.loads(self.latest_path.read_text())
        matches = [image for image in observation.get('images', ())
                   if image.get('camera') == camera]
        if len(matches) != 1 or 'calibration' not in matches[0]:
            raise ValueError('camera must identify one calibrated latest image')
        point = pixel_to_horizontal_plane(
            matches[0]['calibration'], pixel_xy, horizontal_plane_z_m)
        return {'source_observation_path': str(self.latest_path),
                'camera': camera, 'pixel_xy': list(map(float, pixel_xy)),
                'horizontal_plane_z_m': float(horizontal_plane_z_m),
                'point_position_world_m': point,
                'method': 'calibrated_rgb_ray_horizontal_plane',
                'next_call': 'four_point_place_local_point or scalebfm_act'}

    def compile_local_point(self, observation_path, link_name,
                            point_position_world_m, point_offset_link_m):
        self._require_latest(observation_path)
        if link_name not in FOUR_POINT_NAMES[:2]:
            raise ValueError('link_name must be a controlled wrist link')
        observation = json.loads(self.latest_path.read_text())
        target = dict(observation['four_point_world'])
        current = target[link_name]
        placed = wrist_pose_for_local_point(
            point_position_world_m, current['quaternion_wxyz'],
            point_offset_link_m)
        target[link_name] = placed
        delta = (np.asarray(placed['position_world_m'])
                 - np.asarray(current['position_world_m']))
        return {'source_observation_path': str(self.latest_path),
                'link_name': link_name,
                'point_position_world_m': list(map(float, point_position_world_m)),
                'point_offset_link_m': list(map(float, point_offset_link_m)),
                'required_wrist_delta_world_m': delta.tolist(),
                'within_single_step_limit': bool(np.linalg.norm(delta) <= .030001),
                'target': target,
                'active': {'position': [link_name], 'orientation': []},
                'next_call': 'scalebfm_act with bounded <=3cm waypoint(s)'}

    def scalebfm_act(self, observation_path, response):
        self._require_latest(observation_path)
        action = validate_response(response)
        receipts = []
        def execute(receipt, duration, *, capture_motion=False):
            motion_samples=[]
            def capture_robot():
                packet=self.backend.observe()
                pose=FourPointPose.from_mapping(packet['four_point_world'])
                # Explicit allowlist: no contacts, objects, native reward or evaluator fields.
                motion_samples.append({'sim_s':packet.get('sim_s'),
                    'positions_world_m':pose.positions.tolist(),
                    'quaternions_wxyz':pose.quaternions.tolist(),
                    'joint_position_rad':packet.get('joint_position_rad',[]),
                    'commanded_joint_target_rad':packet.get('commanded_joint_target_rad',[])})
                if 'robot_root' in packet:
                    motion_samples[-1].update(
                        observation_id=packet.get('observation_id'),
                        episode_id=str(self.output_dir.resolve()),
                        robot_root=_public_robot_root(packet))
                return packet
            initial_robot_packet=None
            if capture_motion: initial_robot_packet=capture_robot()
            limit = int((duration + 2.1) / .02)
            for _ in range(limit):
                self.backend.tick()
                if capture_motion: capture_robot()
                if self.evaluator:
                    self.evaluator.update(self.backend)
                recorder = getattr(self.image_capture, 'record_tick', None)
                if recorder:
                    recorder(self.evaluator.outcome(self.backend) if self.evaluator else 'not_configured')
                if self.backend.status()['status'] != 'executing':
                    break
            if capture_motion:
                path=self.output_dir/f'robot_motion_{self.index:04d}.jsonl'
                path.write_text(''.join(json.dumps(row)+'\n' for row in motion_samples))
                points=np.array([row['positions_world_m'] for row in motion_samples])
                delta=points-points[0]
                peaks=[int(np.argmax(points[:,i,2])) for i in (2,3)]
                receipt['robot_motion_summary']={
                    'source':'named robot proprioception only; no contact or object truth',
                    'link_order':list(FOUR_POINT_NAMES),'sample_period_s':.02,
                    'joint_names':initial_robot_packet.get('joint_names',[]),
                    'joint_command_source':initial_robot_packet.get('joint_command_source','unavailable'),
                    'samples':len(motion_samples),'trace_path':str(path.resolve()),
                    'robot_root_summary':_robot_root_summary(motion_samples),
                    'max_position_delta_world_m':delta.max(axis=0).tolist(),
                    'min_position_delta_world_m':delta.min(axis=0).tolist(),
                    'peak_ankle_height_samples':[motion_samples[i] for i in peaks],
                    'limitation':'Ankle rise alone does not prove full foot clearance or successful locomotion.'}
            receipts.append({k: v for k, v in receipt.items() if not k.startswith('_')})
        continuous = (getattr(self.backend, 'continuous_chunks_enabled', False)
                      and len(action['trajectory']) > 1)
        if continuous:
            observation = self.backend.observe()
            receipt = self.backend.move_four_point_sequence(
                observation['observation_id'], action['request_id']+':continuous', action['trajectory'])
            self.backend.set_grippers(**action['trajectory'][0]['grippers'],
                                      duration=receipt['duration_s'])
            execute(receipt, receipt['duration_s'], capture_motion=True)
        else:
            for number, waypoint in enumerate(action['trajectory']):
                observation = self.backend.observe()
                receipt = self.backend.move_four_points(
                    observation['observation_id'], f"{action['request_id']}:{number}",
                    waypoint['target'].to_mapping(), waypoint['duration_s'],
                    position_names=waypoint['active']['position'],
                    orientation_names=waypoint['active']['orientation'])
                self.backend.set_grippers(**waypoint['grippers'], duration=waypoint['duration_s'])
                execute(receipt, waypoint['duration_s'])
                if self.backend.status()['status'] not in ('target_reached', 'gripper_duration_elapsed'):
                    break
        self._write_json(self.output_dir/f'execution_{self.index:04d}.json', {
            'response': response, 'receipts': receipts, 'final_status': self.backend.status()})
        packet = self._capture()
        packet['execution'] = receipts
        return packet

    def pi05_infer(self, observation_path):
        self._require_latest(observation_path)
        if self.pi05 is None:
            raise RuntimeError('No task-trained humanoid pi0.5 provider is connected')
        if self.pending_proposal_path is not None:
            raise ValueError('Execute or reject the pending pi0.5 proposal before inferring again')
        observation = json.loads(self.latest_path.read_text())
        proposal = self.pi05.infer(observation, self.task)
        validate_response(proposal)
        path = self.output_dir/'proposals'/f'{self.index:04d}.json'
        self._write_json(path, proposal)
        self.pending_proposal_path = path.resolve()
        self.pending_proposal_observation_path = self.latest_path
        return {'proposal_path': str(self.pending_proposal_path), 'proposal': proposal,
                'next_call': 'loco_execute with a reviewed response'}

    def execute_reviewed_proposal(self, proposal_path, response):
        proposal_path = Path(proposal_path).resolve()
        expected = (self.output_dir/'proposals').resolve()
        if expected not in proposal_path.parents:
            raise ValueError('proposal_path is outside this episode')
        if proposal_path != self.pending_proposal_path:
            raise ValueError('Only the current unconsumed pi0.5 proposal may be executed')
        if self.latest_path != self.pending_proposal_observation_path:
            raise ValueError('pi0.5 proposal is stale for the latest observation')
        validate_response(response)
        self.pending_proposal_path = None
        self.pending_proposal_observation_path = None
        packet = self.scalebfm_act(self.latest_path, response)
        packet['reviewed_proposal_path'] = str(proposal_path)
        return packet


class MujocoImageCapture:
    """Render the declared cameras currently present in the diagnostic scene."""

    def __init__(self, backend, *, width=640, height=480,
                 cameras=('track', 'head_cam', 'right_wrist_cam')):
        import mujoco
        self.backend = backend
        self.renderer = mujoco.Renderer(backend.model, width=width, height=height)
        self.cameras = tuple(name for name in cameras
                             if backend.model.camera(name).id >= 0)

    def __call__(self, directory):
        from PIL import Image
        from rsi.camera_calibration import render_intrinsics
        images = []
        for camera in self.cameras:
            self.renderer.update_scene(self.backend.data, camera=camera)
            path = Path(directory)/f'{camera}.png'
            rgb = self.renderer.render()
            Image.fromarray(rgb).save(path)
            camera_id = self.backend.model.camera(camera).id
            images.append({'camera': camera, 'path': str(path.resolve()),
                           'sim_exposure_s': float(self.backend.data.time),
                           'calibration': {
                               'width_px': int(rgb.shape[1]),
                               'height_px': int(rgb.shape[0]),
                               'fovy_deg': float(self.backend.model.cam_fovy[camera_id]),
                               'render_intrinsics': render_intrinsics(
                                   self.renderer.scene, int(rgb.shape[1]), int(rgb.shape[0])),
                               'position_world_m': self.backend.data.cam_xpos[
                                   camera_id].tolist(),
                               'rotation_camera_to_world_row_major':
                                   self.backend.data.cam_xmat[camera_id].tolist(),
                               'optical_convention':
                                   'x_right_y_up_minus_z_forward'}})
        return images

    def close(self):
        self.renderer.close()
