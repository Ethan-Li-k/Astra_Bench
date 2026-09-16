"""Offline stage audit and one-step input interventions, never a live policy."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument('trace', type=Path)
    args = p.parse_args()
    d = np.load(args.trace/'chain.npz')
    output = args.trace/'analysis.json'
    if output.exists():
        raise FileExistsError(output)
    i = np.flatnonzero(d['sim_s'] >= 10)
    scale, default = d['scale'], d['default']
    checks = {
        'target_decode_max_error_rad': float(np.max(abs(d['q_target']-(default+scale*d['raw_action'])))),
        'pd_send_max_error_nm': float(np.max(abs(d['torque_sent']-np.clip(d['pd_unclipped'], d['limits'][:,0], d['limits'][:,1])))),
        'history_latest_vs_previous_output_max_error': float(np.max(abs(d['action_history_in'][1:,-1]-d['raw_action'][:-1]))),
        'q_proprio_vs_pd_max_error_rad': float(np.max(abs(d['policy'][:,-1,6:35]+default-d['q_before_pd'][::5]))),
        'physics_to_control_log_max_error_rad': float(np.max(abs(d['q_after_pd'][4::5]-d['q_after']))),
        'nominal_world_reference_range_max_m': float(np.ptp(d['nominal_pos'],axis=0).max()),
        'tracker_world_reference_range_max_m': float(np.ptp(d['tracker_pos'],axis=0).max()),
        'control_frames': len(d['sim_s']), 'physics_frames': len(d['substep_s'])}
    options = ort.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    session = ort.InferenceSession('/home/galbot/Downloads/model_38000.onnx', options, providers=['CPUExecutionProvider'])
    base = {name: d[key][i].astype(np.float32) for name,key in
            [('policy','policy'),('policy_task','policy_task'),('action','action_history_in')]}
    def run(feed):
        outputs = []
        for start in range(0, len(i), 32):
            b = {k:v[start:start+32] for k,v in feed.items()}
            n = len(b['policy'])
            b.update(mode=np.repeat(d['mode'], n, axis=0), mode_mapping=np.repeat(d['mode_mapping'], n, axis=0))
            outputs.append(session.run(['actions'], b)[0])
        return np.concatenate(outputs)
    replay = run(base)
    checks['onnx_replay_max_error'] = float(np.max(abs(replay-d['raw_action'][i])))
    fixed = {k:np.repeat(v[:1],len(i),axis=0) for k,v in base.items()}
    cases = {'full': replay, 'all_fixed': run(fixed)}
    for key in base:
        cases['only_'+key] = run({**fixed, key:base[key]})
        cases['freeze_'+key] = run({**base, key:fixed[key]})
    names = d['joint_names'].tolist()
    def metrics(a):
        return {'step_rms_deg': np.rad2deg(np.sqrt(np.mean(np.diff(a,axis=0)**2,axis=0))).tolist(),
                'range_deg': np.rad2deg(np.ptp(a,axis=0)).tolist()}
    result = {'checks': checks, 'joint_names': names,
        'actual_motion': metrics(d['q_after'][i]),
        'model_targets': metrics(d['q_target'][i]),
        'one_step_interventions': {k:metrics(v*scale) for k,v in cases.items()},
        'interpretation_limit': 'Offline one-step input substitutions; not additive causal shares or a deployable frozen-input controller.'}
    runtime = Path('/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/runtime')
    os.environ['RUNTIME_DIR'] = str(runtime)
    torch.set_num_threads(1)
    spec = importlib.util.spec_from_file_location('rsi_audit_eager', runtime/'scripts/exp8ap/scalebfm_eager.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.ScaleBFMEagerController().eval()
    state = torch.load('/home/galbot/Downloads/model_38000.pt', map_location='cpu', weights_only=True)
    model.load_state_dict(state['actor_state_dict'], strict=True)
    with torch.inference_mode():
        codes, eager = [], []
        for start in range(0, len(i), 32):
            b = {k:torch.from_numpy(v[start:start+32]) for k,v in base.items()}
            n = b['policy'].shape[0]
            mode = torch.from_numpy(np.repeat(d['mode'],n,axis=0))
            mapping = torch.from_numpy(np.repeat(d['mode_mapping'],n,axis=0))
            code = model.task_embedder.encode(model.build_task_input(b['policy_task'],mode,mapping))
            codes.append(code.numpy()[:,0])
            eager.append(model.act_from_code(b['policy'],b['action'],code).numpy())
        codes = np.concatenate(codes)
        eager = np.concatenate(eager)
    parity = float(np.max(abs(eager-replay)))
    result['eager_onnx_max_error'] = parity
    if parity < 1e-4:
        flips = np.count_nonzero(np.diff(codes,axis=0),axis=1)
        result['fsq'] = {'frames_with_code_changes_fraction': float(np.mean(flips>0)),
            'mean_changed_dimensions_per_tick': float(flips.mean()),
            'maximum_changed_dimensions_per_tick': int(flips.max())}
        np.savez(args.trace/'replay.npz', indices=i, fsq_code=codes, **cases)
    else:
        result['fsq'] = {'status':'unverified; eager graph did not match ONNX'}
    output.write_text(json.dumps(result,indent=2))
    for key in ('left_elbow_joint','right_elbow_joint','left_shoulder_pitch_joint'):
        j = names.index(key)
        print(key,{case:round(value['step_rms_deg'][j],5) for case,value in result['one_step_interventions'].items()})
    print('checks',checks,'eager parity',parity,'FSQ',result['fsq'],flush=True)


if __name__ == '__main__':
    main()
