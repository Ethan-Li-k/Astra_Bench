"""model_38000 adapter, reusing locomanip math without changing its defaults.

Scale/default pose: same-checkpoint runtime_mirror metadata. PD gains: that
runtime's ScaleTrack/robots/g1_29dof.py. Full-anchor convention: checkpoint
interface section 3.1. This adapter has not been certified for hardware.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from locomanip.bfm.scaletrack import BODY_NAMES, DEFAULT_JOINT_POS, ScaleTrackInferFn
from rsi.four_point import FOUR_POINT_NAMES

MODEL = Path('/home/galbot/Downloads/model_38000.onnx')
MODEL_SHA256 = 'd87b5224ed953cbe5f118d5fd23ea28d21eac36fca2b1692683a9993884b31aa'
METADATA = Path('/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/runtime/model_38000_metadata.json')
SCENE = Path('/home/galbot/lizekai/Loco_manip/locomanip/assets/unitree_g1_5010/scene_mjx_track_dex3.xml')


class Model38000(ScaleTrackInferFn):
    def __init__(self, model, *, load_policy=True, far_offset=25, mode='UMI-4'):
        if mode != 'UMI-4':
            raise ValueError('This experiment only supports explicit UMI-4')
        # Mirrored training commands use randint(5, 33): upper bound excluded.
        if type(far_offset) is not int or not 5 <= far_offset <= 32:
            raise ValueError('far_offset must be an integer in [5, 32] control ticks')
        self.metadata = json.loads(METADATA.read_text())
        if self.metadata['joint_names'] != list(DEFAULT_JOINT_POS):
            raise ValueError('Metadata and named policy joint order disagree')
        if self.metadata['selected_body_names'] != list(BODY_NAMES):
            raise ValueError('Metadata and body order disagree')
        np.testing.assert_allclose(self.metadata['default_dof_pos'], list(DEFAULT_JOINT_POS.values()), atol=1e-7)
        super().__init__(None, model, mode_name=mode, ctrl_dt=.02,
                         future_idx=(0, 1, 2, 3, 4, far_offset))
        active = {BODY_NAMES[i] for i in np.flatnonzero(self.mode[0])}
        if active != set(FOUR_POINT_NAMES):
            raise ValueError(f'UMI-4 body mask mismatch: {sorted(active)}')
        self._full_anchor_quat = True
        if load_policy:
            if hashlib.sha256(MODEL.read_bytes()).hexdigest() != MODEL_SHA256:
                raise ValueError('Checkpoint changed: re-audit before inference')
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(str(MODEL), sess_options=options,
                                               providers=['CPUExecutionProvider'])

    def _action_scale_map(self):
        return dict(zip(self.metadata['joint_names'], self.metadata['action_scale']))

    def _pd_gain_maps(self, _):
        # Explicit training-side gains; never select an arbitrary sibling JSON.
        omega = 10 * 2 * np.pi
        kp, kd = {}, {}
        for name in self.metadata['joint_names']:
            if name in ('waist_roll_joint', 'waist_pitch_joint'):
                kp[name], kd[name] = 300., 5.
                continue
            if name == 'waist_yaw_joint':
                kp[name], kd[name] = 100., 2.
                continue
            if 'hip_roll' in name or 'knee' in name:
                armature = .025101925
            elif 'hip_pitch' in name or 'hip_yaw' in name:
                armature = .010177520
            elif 'ankle' in name:
                armature = 2 * .003609725
            elif 'wrist_pitch' in name or 'wrist_yaw' in name:
                armature = .00425
            else:
                armature = .003609725
            kp[name], kd[name] = armature * omega**2, 4 * armature * omega
        return kp, kd
