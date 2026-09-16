"""Stateful dispatch boundary for Codex dynamic loco-manip tools."""
import json
from pathlib import Path

from rsi.policy_harness import LocalFourPointHarness, tool_specs


class LocoManipToolHost:
    """Own one backend and one recorded episode; model transport lives elsewhere."""

    def __init__(self, rollout_root, backend_factory, *, method='direct', pi05=None,
                 evaluator_factory=None, image_capture_factory=None):
        self.rollout_root = Path(rollout_root).resolve()
        self.rollout_root.mkdir(parents=True, exist_ok=True)
        self.backend_factory = backend_factory
        self.method = method
        self.pi05 = pi05
        self.evaluator_factory = evaluator_factory
        self.image_capture_factory = image_capture_factory
        self.allowed = {spec['name'] for spec in tool_specs(method)}
        self.backend = self.capture = self.harness = None
        self.initialization_error = None
        self.runtime_error = None

    @staticmethod
    def _strict(arguments, keys):
        if not isinstance(arguments, dict) or set(arguments) != set(keys):
            raise ValueError(f'Tool arguments must contain exactly {tuple(keys)}')

    def _new_output(self, value, *, create):
        path = Path(value).resolve()
        if path == self.rollout_root or self.rollout_root not in path.parents:
            raise ValueError('output_dir must be a new descendant of rollout_root')
        if path.exists():
            raise ValueError('output_dir already exists')
        if create:
            path.mkdir(parents=True)
        return path

    @staticmethod
    def _write(path, name, value):
        (path/name).write_text(json.dumps(value, indent=2))

    def dispatch(self, name, arguments):
        if name not in self.allowed:
            raise ValueError(f'Tool {name!r} is unavailable for method {self.method!r}')
        if name == 'loco_start':
            self._strict(arguments, ('task', 'output_dir'))
            if self.initialization_error is not None:
                return self.initialization_error
            if self.harness is not None:
                raise ValueError('Episode already started')
            output = self._new_output(arguments['output_dir'], create=False)
            try:
                self.backend = self.backend_factory()
                self.capture = (self.image_capture_factory(self.backend)
                                if self.image_capture_factory else None)
                evaluator = (self.evaluator_factory()
                             if self.evaluator_factory else None)
                self.harness = LocalFourPointHarness(
                    self.backend, output, pi05=self.pi05,
                    image_capture=self.capture, evaluator=evaluator)
                result = self.harness.start(arguments['task'])
                self._write(output, 'tool_result.json', result)
            except Exception as error:
                self.initialization_error = {
                    'error_type': type(error).__name__, 'error': str(error),
                    'no_execution': True, 'retryable': False,
                    'native_outcome': 'not_started', 'rollout_finished': True,
                    'stop_reason': 'backend_initialization_error'}
                self._write(self.rollout_root, 'initialization_error.json',
                            self.initialization_error)
                return self.initialization_error
            return result

        if self.harness is None:
            raise ValueError('Call loco_start before any action tool')
        if name == 'scalebfm_act':
            self._strict(arguments, ('observation_path', 'response', 'output_dir'))
            handler = lambda: self.harness.scalebfm_act(
                arguments['observation_path'], arguments['response'])
        elif name == 'four_point_translate':
            self._strict(arguments, ('observation_path', 'names', 'delta_world_m', 'output_dir'))
            handler = lambda: self.harness.compile_translation(
                arguments['observation_path'], arguments['names'], arguments['delta_world_m'])
        elif name == 'four_point_rotate':
            self._strict(arguments, ('observation_path', 'names',
                                     'rotation_vector_world_rad', 'pivot_world_m', 'output_dir'))
            handler = lambda: self.harness.compile_rotation(
                arguments['observation_path'], arguments['names'],
                arguments['rotation_vector_world_rad'], arguments['pivot_world_m'])
        elif name == 'image_pixel_to_world_plane':
            self._strict(arguments, ('observation_path', 'camera', 'pixel_xy',
                                     'horizontal_plane_z_m', 'output_dir'))
            handler = lambda: self.harness.compile_pixel_to_plane(
                arguments['observation_path'], arguments['camera'],
                arguments['pixel_xy'], arguments['horizontal_plane_z_m'])
        elif name == 'four_point_place_local_point':
            self._strict(arguments, ('observation_path', 'link_name',
                                     'point_position_world_m', 'point_offset_link_m',
                                     'output_dir'))
            handler = lambda: self.harness.compile_local_point(
                arguments['observation_path'], arguments['link_name'],
                arguments['point_position_world_m'], arguments['point_offset_link_m'])
        elif name == 'pi05_infer':
            self._strict(arguments, ('observation_path', 'output_dir'))
            handler = lambda: self.harness.pi05_infer(arguments['observation_path'])
        else:
            self._strict(arguments, ('proposal_path', 'response', 'output_dir'))
            handler = lambda: self.harness.execute_reviewed_proposal(
                arguments['proposal_path'], arguments['response'])

        output = self._new_output(arguments['output_dir'], create=True)
        before_time=float(self.backend.data.time)
        try:
            result = handler()
        except Exception as error:
            advanced=float(self.backend.data.time)>before_time+1e-9
            pending=bool(self.backend.active)
            failure={'error_type':type(error).__name__,'message':str(error),
                'physics_advanced':advanced,'pending_reference':pending}
            self._write(output, 'tool_failure.json', failure)
            # A synchronous call may reject parameters without changing state.
            # Pending control/advanced physics after an exception is instead a
            # host failure: terminate this physical attempt, reply to the model,
            # and still await its full review. Never label it retryable.
            if advanced or pending or not isinstance(error,ValueError):
                if pending:self.backend.cancel()
                self.runtime_error=dict(failure,error=str(error),no_execution=not advanced,
                    retryable=False,rollout_finished=True,stop_reason='control_transaction_error',
                    native_outcome=(self.harness.evaluator.outcome(self.backend)
                        if self.harness.evaluator else 'not_configured'),
                    control_reference_cancelled=pending)
                self._write(output,'tool_result.json',self.runtime_error)
                return self.runtime_error
            raise
        self._write(output, 'tool_result.json', result)
        return result

    def close(self):
        if self.capture and hasattr(self.capture, 'close'):
            self.capture.close()
        if self.backend and hasattr(self.backend, 'close'):
            self.backend.close()
