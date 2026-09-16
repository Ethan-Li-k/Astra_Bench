"""Explicit simulation diagnostics for the frozen weights' FSQ boundary.

Continuous mode changes inference semantics and is NOT the original ONNX
policy. It is never selected by default or used as a hardware-ready backend.
"""
import importlib.util
import os
from pathlib import Path
import numpy as np
import torch
from locomanip.bfm.two_stage import FSQQuantizer


class DiagnosticLatentPolicy:
    def __init__(self, adapter, quantizer):
        if quantizer not in ('torch_raw', 'hysteresis', 'continuous'):
            raise ValueError('Unknown diagnostic quantizer')
        runtime = Path('/home/galbot/lizekai/APA/N_TRACK_ASSETS/runtime_mirror/runtime')
        os.environ['RUNTIME_DIR'] = str(runtime)
        torch.set_num_threads(1)
        spec = importlib.util.spec_from_file_location('rsi_diagnostic_model', runtime/'scripts/exp8ap/scalebfm_eager.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.model = module.ScaleBFMEagerController().eval()
        state = torch.load('/home/galbot/Downloads/model_38000.pt', map_location='cpu', weights_only=True)
        self.model.load_state_dict(state['actor_state_dict'], strict=True)
        self.model.task_embedder.fsq = FSQQuantizer(latent_dim=32, num_levels=16)
        self.adapter, self.quantizer = adapter, quantizer
        self.previous = None
        self.raw_latent = self.raw_code = self.used_code = None
        self.parity_error = None

    def __call__(self, task):
        a = self.adapter
        with torch.inference_mode():
            policy, history = torch.from_numpy(a.policy_history), torch.from_numpy(a.action_history)
            inp = self.model.build_task_input(torch.from_numpy(task[None]), torch.from_numpy(a.mode), torch.from_numpy(a.mode_mapping))
            latent = self.model.task_embedder.encoder(inp.flatten(1)).unsqueeze(1)
            self.raw_latent = latent.numpy()[0, 0].copy()
            levels = self.model.task_embedder.fsq._levels.to(latent)
            half_l = (levels-1)*(1+self.model.task_embedder.fsq.eps)/2
            offset = torch.where(levels%2==0, .5, 0.)
            bounded = torch.tanh(latent+torch.atanh(offset/half_l))*half_l-offset
            integers = torch.round(bounded)
            raw = integers/(levels//2)
            if self.parity_error is None:
                expected = a.session.run(['actions'], {'policy':a.policy_history, 'policy_task':task[None],
                    'action':a.action_history, 'mode':a.mode, 'mode_mapping':a.mode_mapping})[0]
                actual = self.model.act_from_code(policy,history,raw).numpy()
                self.parity_error = float(abs(actual-expected).max())
                if self.parity_error > 1e-4:
                    raise ValueError(f'Diagnostic reconstruction does not match ONNX: {self.parity_error}')
            if self.quantizer=='hysteresis' and self.previous is not None:
                integers = torch.where(abs(bounded-self.previous)>.6, integers, self.previous)
            self.previous = integers.clone()
            used = bounded/(levels//2) if self.quantizer=='continuous' else integers/(levels//2)
            self.raw_code, self.used_code = raw.numpy()[0,0].copy(), used.numpy()[0,0].copy()
            return self.model.act_from_code(policy,history,used).numpy()[0].copy()
