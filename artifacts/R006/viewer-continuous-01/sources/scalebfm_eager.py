"""Eager PyTorch executor for the frozen ScalingBFM tracker (model_38000).

The shipped ScaleBridge BFMAgent only accepts a torch.jit/TensorRT artifact, but the
delivered model_38000.pt is a raw training checkpoint. This module rebuilds the same
forward graph from the shipped HumanoidTransformer definition plus the FSQ task
embedder described in fsq_scaletrack_vla_interface.md, and loads actor_state_dict
directly. Weights are never modified.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import torch
import torch.nn as nn

RUNTIME_DIR = Path(
    os.environ.get(
        "RUNTIME_DIR",
        "/mnt/home/lizekai/APA/EXP8A_P0_INPUTS_FROM_QY_20260813/scalebridge_runtime",
    )
)
_HT_PATH = (
    RUNTIME_DIR
    / "ScaleBFM/ScaleTrack/source/my_rsl_rl/my_rsl_rl/networks/humanoid_transformer.py"
)

# Loaded by path: the my_rsl_rl package __init__ pulls in isaaclab/tensordict, which
# are not needed for inference and are not installed here.
_spec = importlib.util.spec_from_file_location("_scalebfm_ht", _HT_PATH)
_ht = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ht)
HumanoidTransformer = _ht.HumanoidTransformer

NUM_JOINTS = 29
NUM_BODIES = 14
TASK_DIM = 253
MODE_DIM = 14
FUTURE_LEN = 6
CONTEXT_LEN = 3
PROP_DIM = 64
LATENT_DIM = 32
EMBED_DIM = 256
FSQ_LEVELS = (16,) * LATENT_DIM


class FSQ(nn.Module):
    """Finite scalar quantization, zero-parameter. Matches vector_quantize_pytorch."""

    def __init__(self, levels=FSQ_LEVELS):
        super().__init__()
        self.register_buffer("_levels", torch.tensor(levels, dtype=torch.float32))

    def bound(self, z: torch.Tensor, eps: float = 1e-3) -> torch.Tensor:
        half_l = (self._levels - 1) * (1 - eps) / 2
        offset = torch.where(self._levels % 2 == 0, 0.5, 0.0)
        shift = (offset / half_l).atanh()
        return (z + shift).tanh() * half_l - offset

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        return torch.round(self.bound(z)) / (self._levels // 2)


class TaskEmbedderFSQ(nn.Module):
    def __init__(self):
        super().__init__()
        flat_dim = FUTURE_LEN * (TASK_DIM + MODE_DIM)
        self.fsq = FSQ()
        self.encoder = nn.Sequential(
            nn.Linear(flat_dim, 512), nn.ELU(),
            nn.Linear(512, 512), nn.ELU(),
            nn.Linear(512, LATENT_DIM),
        )
        self.trunk = nn.Linear(LATENT_DIM, EMBED_DIM)
        # Training-only reconstruction head. Kept so the 88-key checkpoint loads
        # strictly, which is itself an integrity check. Never called at inference.
        self.recon_head = nn.Sequential(
            nn.Linear(EMBED_DIM, 512), nn.ELU(),
            nn.Linear(512, 512), nn.ELU(),
            nn.Linear(512, flat_dim),
        )

    def encode(self, task_input: torch.Tensor) -> torch.Tensor:
        """(B, 6, 267) -> FSQ code (B, 1, 32) on the {(k-8)/8} grid."""
        z = self.encoder(task_input.flatten(1)).unsqueeze(1)
        return self.fsq(z)

    def forward(self, task_input: torch.Tensor) -> torch.Tensor:
        return self.trunk(self.encode(task_input))


class ScaleBFMEagerController(nn.Module):
    """GT WB49 task obs -> frozen tracker -> 29 DoF joint targets."""

    def __init__(self):
        super().__init__()
        self.transformer = HumanoidTransformer(
            prop_obs_dim=PROP_DIM,
            action_dim=NUM_JOINTS,
            output_dim=NUM_JOINTS,
            embed_dim=EMBED_DIM,
            num_heads=4,
            ff_dim=EMBED_DIM,
            num_layers=4,
        )
        self.task_embedder = TaskEmbedderFSQ()
        self.distribution = nn.Module()
        self.distribution.std_param = nn.Parameter(torch.ones(NUM_JOINTS))

    @classmethod
    def from_checkpoint(cls, ckpt_path=None, device="cuda"):
        ckpt_path = Path(ckpt_path or RUNTIME_DIR / "model_38000.pt")
        blob = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        model = cls()
        model.load_state_dict(blob["actor_state_dict"], strict=True)
        model.eval().to(device)
        for p in model.parameters():
            p.requires_grad_(False)
        return model, int(blob["iter"])

    def build_task_input(self, policy_task, mode, mode_mapping):
        """(B,6,253) x (B,14) x (B,253) -> (B,6,267), per interface md 3.2."""
        masked = policy_task * mode_mapping.unsqueeze(1)
        mode_exp = mode.unsqueeze(1).expand(-1, masked.shape[1], -1)
        return torch.cat([masked, mode_exp], dim=-1)

    def forward(self, policy, policy_task, action, mode, mode_mapping):
        task_input = self.build_task_input(policy_task, mode, mode_mapping)
        task_tokens = self.task_embedder(task_input)
        return self.transformer(policy, action, task_tokens)

    def act_from_code(self, policy, action, code):
        """Latent interface: VLA-produced FSQ code (B,1,32) drives the tracker."""
        return self.transformer(policy, action, self.task_embedder.trunk(code))

    def joint_targets(self, raw_action, default_dof_pos, action_scale):
        return default_dof_pos + action_scale * raw_action


def wholebody14_mode(batch_size: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    """WholeBody-14 mode vector and its [3,3,6,6]-per-body mapping (+ timestamp)."""
    mode = torch.ones(batch_size, MODE_DIM, device=device)
    parts = [mode.new_ones(batch_size, NUM_BODIES * d) for d in (3, 3, 6, 6)]
    parts.append(mode.new_ones(batch_size, 1))
    return mode, torch.cat(parts, dim=-1)
