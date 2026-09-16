"""Read-only FSQ inspection with measured parity against actual ONNX outputs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import torch
from locomanip.bfm.two_stage import FSQQuantizer


def main():
    p = argparse.ArgumentParser()
    p.add_argument('trace', type=Path)
    p.add_argument('--rounding-audit', action='store_true')
    args = p.parse_args()
    output = args.trace/('rounding_audit.json' if args.rounding_audit else 'fsq_audit.json')
    if output.exists():
        raise FileExistsError(output)
    d = np.load(args.trace/'chain.npz')
    indices = np.flatnonzero(d['sim_s'] >= 10)
    runtime = Path('/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/runtime')
    os.environ['RUNTIME_DIR'] = str(runtime)
    torch.set_num_threads(1)
    spec = importlib.util.spec_from_file_location('rsi_fsq_audit_model', runtime/'scripts/exp8ap/scalebfm_eager.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.ScaleBFMEagerController().eval()
    state = torch.load('/home/galbot/Downloads/model_38000.pt',map_location='cpu',weights_only=True)
    model.load_state_dict(state['actor_state_dict'],strict=True)
    # The mirror uses (1-eps); local inference uses (1+eps). Change only
    # this zero-parameter inspection component, never the running ONNX.
    model.task_embedder.fsq = FSQQuantizer(latent_dim=32, num_levels=16)
    codes, outputs, latents = [], [], []
    quant_task_only, continuous_task_only = [], []
    with torch.inference_mode():
        for start in range(0, len(indices), 32):
            k = indices[start:start+32]
            task = torch.from_numpy(d['policy_task'][k])
            policy = torch.from_numpy(d['policy'][k])
            history = torch.from_numpy(d['action_history_in'][k])
            mode = torch.from_numpy(np.repeat(d['mode'],len(k),axis=0))
            mapping = torch.from_numpy(np.repeat(d['mode_mapping'],len(k),axis=0))
            task_input = model.build_task_input(task,mode,mapping)
            latent = model.task_embedder.encoder(task_input.flatten(1)).unsqueeze(1)
            code = model.task_embedder.fsq(latent)
            output_action = model.act_from_code(policy,history,code)
            if args.rounding_audit:
                levels = model.task_embedder.fsq._levels.to(latent)
                half_l = (levels-1)*(1+model.task_embedder.fsq.eps)/2
                offset = torch.where(levels%2==0, .5, 0.)
                continuous = (torch.tanh(latent+torch.atanh(offset/half_l))*half_l-offset)/(levels//2)
                fixed_policy = torch.from_numpy(np.repeat(d['policy'][indices[:1]],len(k),axis=0))
                fixed_history = torch.from_numpy(np.repeat(d['action_history_in'][indices[:1]],len(k),axis=0))
                quant_task_only.append(model.act_from_code(fixed_policy,fixed_history,code).numpy())
                continuous_task_only.append(model.act_from_code(fixed_policy,fixed_history,continuous).numpy())
            latents.append(latent.numpy()[:,0]);codes.append(code.numpy()[:,0]);outputs.append(output_action.numpy())
    codes = np.concatenate(codes); latents = np.concatenate(latents); outputs = np.concatenate(outputs)
    parity = float(np.max(abs(outputs-d['raw_action'][indices])))
    result = {'bound_formula': '(levels-1)*(1+eps)/2, eps=0.001',
              'changed_weights': False, 'running_onnx_modified': False,
              'reconstruction_vs_recorded_onnx_max_error': parity,
              'sample_count': len(indices), 'parity_pass': parity < 1e-4}
    if parity < 1e-4:
        flips = np.count_nonzero(np.diff(codes,axis=0),axis=1)
        result.update(code_change_fraction=float(np.mean(flips>0)), mean_changed_dimensions=float(flips.mean()),
                      max_changed_dimensions=int(flips.max()))
        jumps = np.rad2deg(np.diff(d['q_target'][indices],axis=0))
        result['target_steps'] = {}
        for name in ('left_elbow_joint','right_elbow_joint','left_shoulder_pitch_joint'):
            j = d['joint_names'].tolist().index(name)
            result['target_steps'][name] = {label:float(np.sqrt(np.mean(jumps[mask,j]**2))) if mask.any() else None
                for label,mask in [('code_changed_rms_deg',flips>0),('code_unchanged_rms_deg',flips==0)]}
        if args.rounding_audit:
            result['rounding_intervention'] = {}
            for label,values in [('quantized',quant_task_only),('without_rounding',continuous_task_only)]:
                jumps = np.rad2deg(np.diff(np.concatenate(values)*d['scale'],axis=0))
                result['rounding_intervention'][label] = {
                    name:float(np.sqrt(np.mean(jumps[:,d['joint_names'].tolist().index(name)]**2)))
                    for name in ('left_elbow_joint','right_elbow_joint','left_shoulder_pitch_joint')}
            result['intervention_limit'] = 'Offline only: remove rounding while freezing proprio/action history. Off-grid codes are not a validated control policy.'
        else:
            np.savez(args.trace/'fsq_verified.npz', indices=indices, codes=codes, latents=latents, outputs=outputs)
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
