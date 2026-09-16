"""BFM actor split into two callables: encode_task() and decode_action().

The compiled ``bfm_g1_29dof.pt`` is one fused TRT engine — you can't peek
inside it. ``ckpts/model.pt`` is the raw state_dict from training, which is
what we load here.

Architecture (verified against ``mjlab/src/mjlab/tasks/scaletrack/rl/``):

  task_obs (B, F, 267)
        |
        +-- TaskEmbedder.task_projection: Linear(267, 256)
        |        ↓
  task_tokens (B, F, 256)  ← shared latent space across masks/modes

  prop_obs (B, H=3, 64), action_obs (B, H=3, 29), task_tokens (B, F, 256)
        |
        +-- HumanoidTransformer: 4 × (self_attn + cross_attn + SwiGLU FFN)
        |        ↓
  action (B, 29)  ← policy mean; deploy multiplies by action_scale

The network classes are vendored verbatim from mjlab to dodge the mujoco_warp
import chain — they are pure torch and unlikely to change shape.
"""

from __future__ import annotations

import math
from pathlib import Path

import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Vendored network blocks (mjlab/tasks/scaletrack/rl/humanoid_transformer.py)
# ---------------------------------------------------------------------------


class RoPEPositionalEncoding(nn.Module):
  def __init__(self, dim: int, base: int = 10000):
    super().__init__()
    inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
    self.register_buffer("inv_freq", inv_freq)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    seq_len = x.shape[1]
    position = torch.arange(seq_len, device=x.device, dtype=torch.float32)
    freqs = torch.outer(position, self.inv_freq)
    cos_freqs = torch.cos(freqs).unsqueeze(0)
    sin_freqs = torch.sin(freqs).unsqueeze(0)
    x_even = x[:, :, 0::2]
    x_odd = x[:, :, 1::2]
    out = torch.zeros_like(x)
    out[..., 0::2] = x_even * cos_freqs - x_odd * sin_freqs
    out[..., 1::2] = x_even * sin_freqs + x_odd * cos_freqs
    return out


class RMSNorm(nn.Module):
  def __init__(self, dim: int, eps: float = 1e-8):
    super().__init__()
    self.scale = nn.Parameter(torch.ones(dim))
    self.eps = eps

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    norm = x.norm(dim=-1, keepdim=True) / (x.size(-1) ** 0.5)
    return self.scale * x / (norm + self.eps)


class ScaleOnly(nn.Module):
  """Element-wise per-dim scale, no normalization.

  Used in BFMDecoder to replace ``cond_norm`` (originally an RMSNorm). The
  encoder now does the ``z / rms(z)`` step once, so each decoder block only
  needs to apply its learned per-dim scale ``scale_i * x``. Drop-in state-dict
  compatible with RMSNorm — the parameter name (``scale``) matches.
  """

  def __init__(self, dim: int):
    super().__init__()
    self.scale = nn.Parameter(torch.ones(dim))

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    return self.scale * x


class SwiGLU(nn.Module):
  def __init__(self, input_dim: int, hidden_dim: int):
    super().__init__()
    self.w = nn.Linear(input_dim, hidden_dim, bias=False)
    self.v = nn.Linear(input_dim, hidden_dim, bias=False)
    self.output = nn.Linear(hidden_dim, input_dim, bias=False)
    self.silu = nn.SiLU()

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    return self.output(self.silu(self.w(x)) * self.v(x))


class HumanoidTransformerBlock(nn.Module):
  def __init__(self, embed_dim: int, num_heads: int, ff_dim: int):
    super().__init__()
    self.self_attention = nn.MultiheadAttention(
      embed_dim, num_heads, batch_first=True
    )
    self.cross_attention = nn.MultiheadAttention(
      embed_dim, num_heads, batch_first=True
    )
    self.feed_forward = SwiGLU(embed_dim, ff_dim)
    self.rmsnorm1 = RMSNorm(embed_dim)
    self.rmsnorm2 = RMSNorm(embed_dim)
    self.rmsnorm3 = RMSNorm(embed_dim)
    self.cond_norm = RMSNorm(embed_dim)
    self.rope = RoPEPositionalEncoding(embed_dim)

  def forward(
    self, x: torch.Tensor, cond: torch.Tensor, self_attn_mask: torch.Tensor
  ) -> torch.Tensor:
    x_norm = self.rmsnorm1(x)
    x_rope = self.rope(x_norm)
    attn_out, _ = self.self_attention(
      x_rope, x_rope, x_norm, attn_mask=self_attn_mask
    )
    x = x + attn_out
    x_norm = self.rmsnorm2(x)
    cond_norm = self.cond_norm(cond)
    cross_out, _ = self.cross_attention(x_norm, cond_norm, cond_norm)
    x = x + cross_out
    x = x + self.feed_forward(self.rmsnorm3(x))
    return x


class TaskEmbedder(nn.Module):
  """ref → latent. Single Linear(267, 256) for our ckpt (no reduced_task_dim)."""

  def __init__(
    self,
    task_obs_dim: int,
    embedding_dim: int,
    reduced_task_dim: int | None = None,
    hidden_dims: tuple[int, ...] = (),
  ):
    super().__init__()
    self._reduced = reduced_task_dim is not None
    target_dim = reduced_task_dim if self._reduced else embedding_dim
    if len(hidden_dims) == 0:
      self.task_projection: nn.Module = nn.Linear(task_obs_dim, target_dim)
    else:
      layers: list[nn.Module] = [nn.Linear(task_obs_dim, hidden_dims[0]), nn.ELU()]
      for i in range(len(hidden_dims) - 1):
        layers.extend([nn.Linear(hidden_dims[i], hidden_dims[i + 1]), nn.ELU()])
      layers.append(nn.Linear(hidden_dims[-1], target_dim))
      self.task_projection = nn.Sequential(*layers)
    if self._reduced:
      # Orthogonal projection matrix (registered as buffer "W" in training).
      A = torch.randn(embedding_dim, reduced_task_dim, dtype=torch.float32)
      Q, R = torch.linalg.qr(A, mode="reduced")
      diag = torch.sign(torch.diag(R))
      diag[diag == 0] = 1.0
      self.register_buffer("W", Q * diag)

  def forward(self, task_obs: torch.Tensor) -> torch.Tensor:
    z = self.task_projection(task_obs)
    if not self._reduced:
      return z
    z = z / (z.norm(dim=-1, keepdim=True) + 1e-8)
    return torch.matmul(z, self.W.T)


class FSQQuantizer(nn.Module):
  """Parameter-free finite scalar quantizer (Mentzer et al.), eval forward.

  Matches the FSQ-ScaleTrack training repo's ``rl/task_embedder.py::_FSQ``
  as exported in ``bfm_fsq_model_*.onnx`` (constants read off that graph:
  half_l = (L−1)·(1+1e−3)/2 = 7.5075, offset = 0.5 for even L, final
  divide by ⌊L/2⌋ = 8):

    bound(z) = tanh(z + atanh(offset/half_l)) · half_l − offset
    z_q      = round(bound(z)) / ⌊L/2⌋   ∈ {(k−8)/8 : k = 0..15} per dim

  Training uses a straight-through round; at inference plain round is the
  same value.  ``_levels`` is a float32 buffer to mirror the checkpoint.
  """

  def __init__(self, latent_dim: int = 32, num_levels: int = 16, eps: float = 1e-3):
    super().__init__()
    self.register_buffer(
      "_levels", torch.full((latent_dim,), float(num_levels), dtype=torch.float32)
    )
    self.eps = eps

  def forward(self, z: torch.Tensor) -> torch.Tensor:
    levels = self._levels
    half_l = (levels - 1) * (1 + self.eps) / 2
    offset = (levels % 2 == 0).to(z.dtype) * 0.5
    shift = torch.atanh(offset / half_l)
    bounded = torch.tanh(z + shift) * half_l - offset
    half_width = torch.floor(levels / 2)
    return torch.round(bounded) / half_width


class TaskEmbedderFSQ(nn.Module):
  """FSQ task embedder: ``(B, F, 267)`` → single task token ``(B, 1, 256)``.

  The FSQ-ScaleTrack variant of :class:`TaskEmbedder` (see
  ``ckpts/fsq_scaletrack_vla_interface.md``): the whole task window is
  flattened and squeezed through a 32-d × 16-level FSQ bottleneck — the
  128-bit code that VLA-side latent heads target — then a linear trunk
  decodes the code into one cross-attention token.

  ``recon_head`` (token → task-window reconstruction) only feeds an MSE
  loss during training; it is kept as a submodule so raw rsl_rl
  checkpoints strict-load, but ``forward`` never calls it.
  """

  def __init__(
    self,
    task_obs_dim: int = 267,
    num_future: int = 6,
    latent_dim: int = 32,
    num_levels: int = 16,
    hidden_dim: int = 512,
    embedding_dim: int = 256,
  ):
    super().__init__()
    in_dim = task_obs_dim * num_future
    self.encoder = nn.Sequential(
      nn.Linear(in_dim, hidden_dim), nn.ELU(),
      nn.Linear(hidden_dim, hidden_dim), nn.ELU(),
      nn.Linear(hidden_dim, latent_dim),
    )
    self.fsq = FSQQuantizer(latent_dim, num_levels)
    self.trunk = nn.Linear(latent_dim, embedding_dim)
    self.recon_head = nn.Sequential(
      nn.Linear(embedding_dim, hidden_dim), nn.ELU(),
      nn.Linear(hidden_dim, hidden_dim), nn.ELU(),
      nn.Linear(hidden_dim, in_dim),
    )

  def encode_code(self, task_obs: torch.Tensor) -> torch.Tensor:
    """(B, F, 267) → quantized FSQ code (B, 1, 32), values on the (k−8)/8 grid."""
    z = self.encoder(task_obs.reshape(task_obs.shape[0], -1))
    return self.fsq(z.unsqueeze(1))

  def forward(self, task_obs: torch.Tensor) -> torch.Tensor:
    return self.trunk(self.encode_code(task_obs))


class HumanoidTransformer(nn.Module):
  """(prop_obs, action_obs, task_tokens) → action (29,). decode_action() body."""

  def __init__(
    self,
    prop_obs_dim: int,
    action_dim: int,
    output_dim: int,
    embed_dim: int = 256,
    num_heads: int = 2,
    ff_dim: int = 256,
    num_layers: int = 4,
  ):
    super().__init__()
    self.embed_dim = embed_dim
    self.prop_projection = nn.Linear(prop_obs_dim, embed_dim)
    self.action_projection = nn.Linear(action_dim, embed_dim)
    self.empty_embedding = nn.Parameter(torch.randn(1, 1, embed_dim))
    self.transformer_blocks = nn.ModuleList(
      [HumanoidTransformerBlock(embed_dim, num_heads, ff_dim) for _ in range(num_layers)]
    )
    self.final_norm = RMSNorm(embed_dim)
    self.projection_head = nn.Linear(embed_dim, output_dim)

  def forward(
    self,
    prop_obs: torch.Tensor,
    action_obs: torch.Tensor,
    task_tokens: torch.Tensor,
  ) -> torch.Tensor:
    batch_size = prop_obs.shape[0]
    prop_tokens = self.prop_projection(prop_obs)              # (B, H, D)
    action_tokens = self.action_projection(action_obs)        # (B, H, D)
    if prop_tokens.shape[1] != action_tokens.shape[1]:
      raise ValueError(
        f"prop/action history mismatch: {prop_tokens.shape[1]} vs "
        f"{action_tokens.shape[1]}."
      )
    H = prop_tokens.shape[1]
    # Interleave prop[t0], a[t1], prop[t1], a[t2], ..., prop[tH-1] (H + (H-1) = 2H-1).
    context = prop_tokens.new_empty(batch_size, 2 * H - 1, self.embed_dim)
    context[:, 0::2] = prop_tokens
    context[:, 1::2] = action_tokens[:, 1:]
    x = torch.cat([context, self.empty_embedding.expand(batch_size, -1, -1)], dim=1)
    # All non-last tokens attend to the last (empty) token via the mask True.
    mask = torch.zeros(x.shape[1], x.shape[1], dtype=torch.bool, device=x.device)
    row = torch.arange(x.shape[1] - 1, device=x.device)
    mask[row, x.shape[1] - 1] = True
    for blk in self.transformer_blocks:
      x = blk(x, task_tokens, mask)
    x = self.final_norm(x)
    return self.projection_head(x[:, -1, :])


# ---------------------------------------------------------------------------
# Standalone encoder / decoder (the preferred API for new code)
# ---------------------------------------------------------------------------


class BFMEncoder(nn.Module):
  """Task encoder: ``task_obs (B, F, 267)`` → unit-RMS latent ``(B, F, 256)``.

  The output is ``Linear(task_obs) / rms(Linear(task_obs))`` — on the
  RMS=1 hypersphere, decoder-ready.

  This is the **interface for downstream learners (pi0, planners, latent
  priors)**: each per-step latent is a 256-d unit-RMS direction, so:
    - per-dim magnitudes are O(1), gradients well-conditioned for regression
    - small perturbations → small action deltas (no magnitude-amplified
      directions to blow up)
    - distance / interpolation / Gaussian noise are well-defined on the
      hypersphere

  The decoder's per-block ``cond_norm`` was originally ``RMSNorm(z) =
  scale_i * z / rms(z)``; we factor it as ``[z / rms(z)] · scale_i`` and
  put the first half here (shared across all blocks, no learned params),
  leaving the per-block scale_i as a degenerate ``ScaleOnly`` layer in each
  decoder block. End-to-end is bit-exactly equivalent to the original.

  ``encode_raw`` is kept for analysis (e.g. studying the affine map). Don't
  feed raw output to the decoder — it expects unit-RMS form.
  """

  TASK_DIM = 267
  EMBED_DIM = 256
  NUM_FUTURE = 6
  NUM_BLOCKS = 4
  NORM_EPS = 1e-8

  def __init__(self) -> None:
    super().__init__()
    self.task_projection = nn.Linear(self.TASK_DIM, self.EMBED_DIM)
    # Cached read-only copies of decoder.transformer.transformer_blocks[i]
    # .cond_norm.scale (4, 256) — kept here so latent analysis can fetch a
    # block's learned per-dim weighting without loading the decoder. NOT
    # applied during encode; the decoder applies it via ScaleOnly.
    self.register_buffer(
      "cond_norm_scales",
      torch.ones(self.NUM_BLOCKS, self.EMBED_DIM, dtype=torch.float32),
    )

  @torch.no_grad()
  def encode(self, task_obs: torch.Tensor) -> torch.Tensor:
    """(B, F, 267) → (B, F, 256) unit-RMS direction. Decoder-ready.

    As a side-effect caches ``self._last_raw_magnitude`` (shape (B, F)) — the
    L2 norm of the un-normalized Linear output. Used by ``BFMMotionDecoder``
    to reverse the affine map back to task_obs without guessing magnitude.
    At deploy time when latents come from an external planner (no GT raw_z
    available), this cache is stale — callers should pass ``raw_magnitude``
    explicitly.
    """
    z = self.task_projection(task_obs)
    self._last_raw_magnitude = z.norm(dim=-1).detach()
    return self.normalize(z)

  @torch.no_grad()
  def encode_raw(self, task_obs: torch.Tensor) -> torch.Tensor:
    """(B, F, 267) → (B, F, 256) raw Linear output, pre-normalize.
    For research only — do not feed to BFMDecoder."""
    return self.task_projection(task_obs)

  @torch.no_grad()
  def normalize(self, latent: torch.Tensor) -> torch.Tensor:
    """Pure unit-RMS projection: ``z / rms(z)``. Applied internally by
    ``encode``; expose here so external code (planner output, generator
    samples) can be put into the same form before feeding the decoder."""
    rms = latent.norm(dim=-1, keepdim=True) / (self.EMBED_DIM ** 0.5)
    return latent / (rms + self.NORM_EPS)

  @torch.no_grad()
  def feature_view(self, latent: torch.Tensor, block: int = 0) -> torch.Tensor:
    """The form block ``block``'s cross-attn K/V sees AFTER cond_norm:
    ``cond_norm_scales[block] * normalize(latent)``. For PCA / cluster /
    distance analysis — folds in block's learned per-dim importance.
    Not for feeding the decoder."""
    assert 0 <= block < self.NUM_BLOCKS, block
    return self.cond_norm_scales[block] * self.normalize(latent)

  @torch.no_grad()
  def forward(self, task_obs: torch.Tensor) -> torch.Tensor:
    return self.encode(task_obs)

  @classmethod
  def from_split_ckpt(cls, path: str | Path, device: str = "cuda") -> "BFMEncoder":
    """Load a ``bfm_encoder.pt`` produced by ``tools/bfm/split_bfm_ckpt.py``."""
    sd = torch.load(str(path), map_location="cpu", weights_only=True)
    enc = cls()
    miss, unex = enc.load_state_dict(sd, strict=True)
    if miss or unex:
      raise RuntimeError(f"encoder ckpt mismatch: missing={miss} unexpected={unex}")
    enc.to(device).eval()
    for p in enc.parameters():
      p.requires_grad_(False)
    return enc


class BFMDecoder(nn.Module):
  """Decoder: ``(prop_obs, action_obs, latent)`` → ``action (B, 29)``.

  Wraps the full ``HumanoidTransformer`` (4 cross-attn blocks + final norm +
  output head). Each block's ``cond_norm`` is replaced with ``ScaleOnly``
  (element-wise multiply, no normalize) because the encoder already does
  ``z / rms(z)`` once at output. End-to-end is bit-exactly equivalent to the
  original RMSNorm form.

  Latent input shape ``(B, F, 256)`` is the same as encoder output. ``F`` is
  the cross-attn K/V sequence length; F=6 was the BFM training default, but
  the decoder is structurally indifferent to F — passing other values works,
  just may drift the distribution slightly.
  """

  PROP_DIM = 64
  ACT_DIM = 29
  EMBED_DIM = 256
  NUM_HEADS = 4
  FF_DIM = 256
  NUM_LAYERS = 4
  HISTORY_LEN = 3

  def __init__(self) -> None:
    super().__init__()
    self.transformer = HumanoidTransformer(
      prop_obs_dim=self.PROP_DIM,
      action_dim=self.ACT_DIM,
      output_dim=self.ACT_DIM,
      embed_dim=self.EMBED_DIM,
      num_heads=self.NUM_HEADS,
      ff_dim=self.FF_DIM,
      num_layers=self.NUM_LAYERS,
    )
    # Replace all 4 cond_norm modules with ScaleOnly (the encoder takes care
    # of the normalize step; only the per-block scale is left here).
    for blk in self.transformer.transformer_blocks:
      blk.cond_norm = ScaleOnly(self.EMBED_DIM)

  @torch.no_grad()
  def decode(
    self,
    prop_obs: torch.Tensor,
    action_obs: torch.Tensor,
    latent: torch.Tensor,
  ) -> torch.Tensor:
    """Shapes:
      prop_obs:   (B, H=3, 64)
      action_obs: (B, H=3, 29)
      latent:     (B, F=6, 256)
    """
    return self.transformer(prop_obs, action_obs, latent)

  @torch.no_grad()
  def forward(self, prop_obs, action_obs, latent) -> torch.Tensor:
    return self.decode(prop_obs, action_obs, latent)

  @classmethod
  def from_split_ckpt(cls, path: str | Path, device: str = "cuda") -> "BFMDecoder":
    """Load a ``bfm_decoder.pt`` produced by ``tools/bfm/split_bfm_ckpt.py``."""
    sd = torch.load(str(path), map_location="cpu", weights_only=True)
    dec = cls()
    miss, unex = dec.load_state_dict(sd, strict=True)
    if miss or unex:
      raise RuntimeError(f"decoder ckpt mismatch: missing={miss} unexpected={unex}")
    dec.to(device).eval()
    for p in dec.parameters():
      p.requires_grad_(False)
    return dec


# ---------------------------------------------------------------------------
# Motion decoder: latent → task_obs → body pose (in anchor frame).
# No training needed — encoder is affine + normalize, so this is closed-form.
# ---------------------------------------------------------------------------


class BFMMotionDecoder(nn.Module):
  """Reverse of ``BFMEncoder``: ``latent (B, F, 256)`` → reconstructed
  ``task_obs (B, F, 267)`` → ``body_pose (B, F, 14, 7) wxyz`` in anchor frame.

  The encoder is ``z = (W·t + b) / rms(W·t + b)`` with W (256, 267). The
  affine map ``W·t + b`` is **rank ≤ 256 over a 267-d input** so its
  pseudo-inverse gives the min-Frobenius-norm task_obs that produces a given
  raw_z. **Magnitude is lost in unit-RMS normalization** — empirically
  ``||raw_z||`` ranges across [50, 1700] (mean 840, std 490) over a typical
  motion library, so the choice of ``raw_magnitude`` materially affects the
  reconstructed pos scale. The default 840 matches the training mean.

  Implications:
    - The actor decoder (``BFMDecoder``) is magnitude-invariant by design
      (ScaleOnly), so for action inference magnitude does not matter.
    - For motion *visualization* you get the right shape / direction of the
      motion regardless of magnitude, but the absolute pos scale (m) depends
      on ``raw_magnitude``. Default is OK for ballpark visualizing.
    - If you really need pixel-perfect reconstruction, have pi0 output one
      extra scalar (magnitude) per latent step, or learn a small MLP that
      predicts magnitude from latent direction.

  Outputs are in the **anchor (pelvis) frame**. To put them back in world
  frame, the caller supplies the robot's pelvis pos/quat (the same anchor
  that the encoder saw at training time):

      world_pos[i]  = anchor_pos + quat_apply(anchor_quat, body_pos_anchor[i])
      world_quat[i] = quat_mul(anchor_quat, body_quat_anchor[i])
  """

  TASK_DIM = 267
  EMBED_DIM = 256
  NUM_BODIES = 14
  POS_BLOCK_LEN = 14 * 3        # pos block size in task_obs (0..42)
  ROT_BLOCK_OFFSET = 14 * 6     # pos(42) + pos_rel(42)  → rot starts at index 84
  ROT_BLOCK_LEN = 14 * 6        # rot block (84..168) — tan(3)+norm(3) per body
  DEFAULT_RAW_MAGNITUDE = 840.0  # empirical mean of ||raw_z|| at training

  def __init__(self, encoder: BFMEncoder, ridge_lambda: float = 1.0) -> None:
    """``ridge_lambda``: Tikhonov regularization. The plain pseudoinverse W⁺
    has condition number ~590 (σ_min ≈ 0.04 of W), so it amplifies latent
    noise by up to **24×** along low-energy directions — making the recon
    visualization "fly around" under even small latent perturbations even
    though the actor decoder is completely robust to the same noise. Ridge
    regularization replaces ``W⁺ = V Σ⁻¹ Uᵀ`` with ``V (Σ / (Σ² + λI)) Uᵀ``,
    capping amplification at ``1 / (2√λ)``. λ=1.0 gives ~0.5× cap (recon is
    smoother than encoder output noise); λ=0 = unregularized pinv (24× cap).

    Signal recovery cost: low-SV directions of W carry little of the encoder
    signal anyway (otherwise W wouldn't compress 267→256), so ridge barely
    hurts noise-free reconstruction but kills noise amplification.
    """
    super().__init__()
    W = encoder.task_projection.weight       # (256, 267) — Linear: out, in
    b = encoder.task_projection.bias         # (256,)
    if ridge_lambda > 0:
      U, S, Vt = torch.linalg.svd(W, full_matrices=False)   # U: (256, 256), S: (256,), Vt: (256, 267)
      S_reg = S / (S * S + ridge_lambda)                    # (256,)
      W_pinv = Vt.T @ torch.diag(S_reg) @ U.T               # (267, 256)
    else:
      W_pinv = torch.linalg.pinv(W)
    self.register_buffer("W_pinv", W_pinv)
    self.register_buffer("b", b)
    self.ridge_lambda = ridge_lambda

  @torch.no_grad()
  def decode_task_obs(
    self,
    latent: torch.Tensor,
    raw_magnitude: float | None = None,
  ) -> torch.Tensor:
    """latent (B, F, 256) → task_obs reconstruction (B, F, 267).

    ``raw_magnitude``: L2 norm to rescale the unit-RMS latent back to
    (so the pseudo-inverse gives task_obs values in the training range).
    Defaults to the empirical training mean (840).
    """
    if raw_magnitude is None:
      raw_magnitude = self.DEFAULT_RAW_MAGNITUDE
    # Convert RMS=1 back to L2 norm ≈ raw_magnitude.
    # ||unit_z|| = sqrt(D); we want ||raw_z|| = raw_magnitude.
    raw_z = latent * (raw_magnitude / (self.EMBED_DIM ** 0.5))
    # x = (z - b) @ W_pinv^T   (since W_pinv: (267, 256))
    return torch.matmul(raw_z - self.b, self.W_pinv.T)

  @torch.no_grad()
  def decode_body_pose_in_anchor(
    self,
    latent: torch.Tensor,
    raw_magnitude: float | None = None,
  ) -> tuple[torch.Tensor, torch.Tensor]:
    """latent → (body_pos_anchor (B, F, 14, 3), body_quat_anchor (B, F, 14, 4))
    in pelvis-anchor frame, wxyz quaternion.

    Bodies that are masked-out (mode says don't track) come back as zeros
    in the encoder input, so their reconstructed pos / rot are ~zero too —
    callers should apply their own per-mode mask if they want to filter."""
    task_obs = self.decode_task_obs(latent, raw_magnitude=raw_magnitude)
    # pos: indices 0..42, reshape to (B, F, 14, 3)
    body_pos = task_obs[..., 0:self.POS_BLOCK_LEN].reshape(
      *task_obs.shape[:-1], self.NUM_BODIES, 3
    )
    # rot: indices 84..168, tan/norm 6d per body
    rot_block = task_obs[..., self.ROT_BLOCK_OFFSET:
                                self.ROT_BLOCK_OFFSET + self.ROT_BLOCK_LEN]
    rot_block = rot_block.reshape(*task_obs.shape[:-1], self.NUM_BODIES, 6)
    tan = rot_block[..., 0:3]
    norm = rot_block[..., 3:6]
    body_quat = self._tan_norm_to_quat_wxyz(tan, norm)
    return body_pos, body_quat

  @staticmethod
  def _tan_norm_to_quat_wxyz(tan: torch.Tensor, norm: torch.Tensor) -> torch.Tensor:
    """6D tan/norm → quaternion wxyz, via Gram-Schmidt → rotation matrix → quat.

    Encoder convention (mjlab quat_to_tan_norm): tan = R[:, 0], norm = R[:, 2].
    Invert: c1 = tan / |tan|;  c3 = (norm - (norm·c1) c1) / |.|;  c2 = c3 × c1.
    """
    eps = 1e-8
    c1 = tan / (tan.norm(dim=-1, keepdim=True) + eps)
    proj = (norm * c1).sum(dim=-1, keepdim=True) * c1
    c3 = norm - proj
    c3 = c3 / (c3.norm(dim=-1, keepdim=True) + eps)
    c2 = torch.cross(c3, c1, dim=-1)
    # R has columns [c1, c2, c3]; build (..., 3, 3)
    R = torch.stack([c1, c2, c3], dim=-1)
    return _rotmat_to_quat_wxyz(R)


class NeuralMotionDecoder(nn.Module):
  """Learned MLP inverse: ``latent (B, F, 256)`` → 4-body pose in anchor frame.

  Mirrors ``BFMMotionDecoder.decode_body_pose_in_anchor`` API so it's a
  drop-in replacement at viewer / overlay sites. Output expands to 14-body
  shape (non-tracked bodies zero) to match the closed-form convention used
  by ``draw_recon_overlay``.

  Trained via ``tools/bfm/train_motion_decoder.py`` on (latent, GT body pose)
  pairs with latent noise augmentation (σ ~ U(0, 0.15)) — under σ=0.05
  pseudo-pi0 noise the recon error stays ~10mm vs closed-form's 730mm.

  Only supports the mode the MLP was trained on (default UMI-4 — left/right
  wrist + left/right ankle).
  """

  Z_DIM = 256
  N_BODY = 4
  OUT_DIM = N_BODY * 9  # pos(3) + rot6d(6) per body

  def __init__(self, hidden_dim: int = 256, n_hidden: int = 2) -> None:
    super().__init__()
    layers: list[nn.Module] = [
      nn.Linear(self.Z_DIM, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()
    ]
    for _ in range(n_hidden - 1):
      layers += [nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()]
    layers += [nn.Linear(hidden_dim, self.OUT_DIM)]
    self.net = nn.Sequential(*layers)
    # viz_idx (4 body slots into 14-body BODY_NAMES) — set on load.
    self.register_buffer("viz_idx", torch.zeros(self.N_BODY, dtype=torch.long))

  @torch.no_grad()
  def decode_body_pose_in_anchor(
    self,
    latent: torch.Tensor,
    raw_magnitude: float | None = None,  # ignored, kept for API compatibility
  ) -> tuple[torch.Tensor, torch.Tensor]:
    """``latent (B, F, 256)`` → ``(pos: (B, F, 14, 3), quat: (B, F, 14, 4) wxyz)``.

    Only 4 tracked bodies (UMI-4: left/right wrist + left/right ankle) have
    meaningful values; the other 10 slots are zero pos / identity quat,
    so calling code that uses ``viz_idx`` still indexes correctly.
    """
    B, F = latent.shape[:2]
    z_flat = latent.reshape(-1, self.Z_DIM)               # (B*F, 256)
    out = self.net(z_flat).reshape(-1, self.N_BODY, 9)    # (B*F, 4, 9)
    pos4 = out[..., 0:3].reshape(B, F, self.N_BODY, 3)
    rot4_6d = out[..., 3:9].reshape(B, F, self.N_BODY, 6)
    tan = rot4_6d[..., 0:3]
    norm = rot4_6d[..., 3:6]
    quat4 = BFMMotionDecoder._tan_norm_to_quat_wxyz(tan, norm)  # (B, F, 4, 4)

    # Expand to (B, F, 14, ...) at the trained body slots, fill the rest with
    # zeros (pos) / identity (quat) so callers can index by 14-body BODY_NAMES.
    NB_TOTAL = 14
    pos14 = torch.zeros(B, F, NB_TOTAL, 3,
                        device=latent.device, dtype=latent.dtype)
    quat14 = torch.zeros(B, F, NB_TOTAL, 4,
                         device=latent.device, dtype=latent.dtype)
    quat14[..., 0] = 1.0
    for i, bi in enumerate(self.viz_idx.tolist()):
      pos14[..., bi, :] = pos4[..., i, :]
      quat14[..., bi, :] = quat4[..., i, :]
    return pos14, quat14

  @classmethod
  def from_ckpt(cls, path: str | Path, device: str = "cuda") -> "NeuralMotionDecoder":
    state = torch.load(str(path), map_location="cpu", weights_only=False)
    obj = cls(hidden_dim=state["hidden_dim"], n_hidden=state["n_hidden"])
    # state["state_dict"] keys are "net.0.weight" etc. (because the training
    # MLP wraps the layers in self.net = Sequential(...) — same structure
    # here). Load directly onto obj; viz_idx is set afterwards.
    miss, unex = obj.load_state_dict(state["state_dict"], strict=False)
    if unex:
      raise RuntimeError(f"unexpected keys when loading motion decoder: {unex}")
    if "viz_idx" not in {k for k in miss}:  # only viz_idx is expected missing
      pass
    # Resolve viz_idx from the body_names list embedded in the ckpt
    from locomanip.bfm.scaletrack import BODY_NAMES
    viz_idx = [BODY_NAMES.index(n) for n in state["body_names"]]
    obj.viz_idx = torch.tensor(viz_idx, dtype=torch.long)
    obj.to(device).eval()
    for p in obj.parameters():
      p.requires_grad_(False)
    return obj


def _rotmat_to_quat_wxyz(R: torch.Tensor) -> torch.Tensor:
  """Batched (..., 3, 3) → (..., 4) wxyz. Shepperd's method, branch-free
  via masked accumulation."""
  leading = R.shape[:-2]
  R_flat = R.reshape(-1, 3, 3)
  N = R_flat.shape[0]
  m = R_flat
  m00, m01, m02 = m[:, 0, 0], m[:, 0, 1], m[:, 0, 2]
  m10, m11, m12 = m[:, 1, 0], m[:, 1, 1], m[:, 1, 2]
  m20, m21, m22 = m[:, 2, 0], m[:, 2, 1], m[:, 2, 2]
  trace = m00 + m11 + m22
  q = torch.zeros(N, 4, dtype=R.dtype, device=R.device)

  def _assign(mask, w, x, y, z):
    if not mask.any():
      return
    q[mask, 0] = w
    q[mask, 1] = x
    q[mask, 2] = y
    q[mask, 3] = z

  ca = trace > 0
  cb = (~ca) & (m00 >= m11) & (m00 >= m22)
  cc = (~ca) & (~cb) & (m11 >= m22)
  cd = ~(ca | cb | cc)
  if ca.any():
    s = (trace[ca] + 1.0).sqrt() * 2
    _assign(ca, 0.25 * s,
            (m21[ca] - m12[ca]) / s,
            (m02[ca] - m20[ca]) / s,
            (m10[ca] - m01[ca]) / s)
  if cb.any():
    s = (1.0 + m00[cb] - m11[cb] - m22[cb]).sqrt() * 2
    _assign(cb, (m21[cb] - m12[cb]) / s,
            0.25 * s,
            (m01[cb] + m10[cb]) / s,
            (m02[cb] + m20[cb]) / s)
  if cc.any():
    s = (1.0 + m11[cc] - m00[cc] - m22[cc]).sqrt() * 2
    _assign(cc, (m02[cc] - m20[cc]) / s,
            (m01[cc] + m10[cc]) / s,
            0.25 * s,
            (m12[cc] + m21[cc]) / s)
  if cd.any():
    s = (1.0 + m22[cd] - m00[cd] - m11[cd]).sqrt() * 2
    _assign(cd, (m10[cd] - m01[cd]) / s,
            (m02[cd] + m20[cd]) / s,
            (m12[cd] + m21[cd]) / s,
            0.25 * s)
  q = q / (q.norm(dim=-1, keepdim=True) + 1e-8)
  return q.reshape(*leading, 4)


# ---------------------------------------------------------------------------
# Back-compat wrapper: thin shim that just holds BFMEncoder + BFMDecoder.
# All existing call sites (BFMRawInferFn, track_motion, track_latent,
# track_from_latent) keep working without changes.
# ---------------------------------------------------------------------------


class BFMTwoStage(nn.Module):
  """BFM actor decomposed into ``encode_task`` and ``decode_action``.

  Loads ``ckpts/model.pt`` (raw training checkpoint, NOT the TRT-fused
  ``bfm_g1_29dof.pt``). The model_state_dict prefixes map as:

    state_dict key prefix         → submodule
    -----------------------------------------------------
    actor.*                       → self.transformer  (HumanoidTransformer)
    actor_task_embedder.*         → self.task_embedder (TaskEmbedder)
    critic.*, critic_task_*, std  → ignored at deploy
  """

  TASK_DIM = 267   # 253 raw + 14 mode
  PROP_DIM = 64    # proj_grav(3) + gyro(3) + jpos_rel(29) + jvel_scaled(29)
  ACT_DIM = 29
  EMBED_DIM = 256
  # mjlab/tasks/scaletrack/rl/humanoid_transformer.py trains with num_heads=4.
  # `nn.MultiheadAttention` in_proj_weight is (3*embed_dim, embed_dim) regardless
  # of num_heads, so strict state_dict load succeeds with the wrong value — but
  # head_dim = embed_dim / num_heads, and softmax(QK^T/sqrt(head_dim)) is
  # computed per-head, so a mismatched num_heads silently rearranges every
  # attention into nonsense and the policy outputs low-authority "soft" actions
  # that drift the robot into a fall a few seconds in.
  NUM_HEADS = 4
  FF_DIM = 256
  NUM_LAYERS = 4
  HISTORY_LEN = 3
  NUM_FUTURE = 6
  NUM_BODIES = 14

  def __init__(self, ckpt_path: str | Path, device: str = "cuda") -> None:
    super().__init__()
    self.device = device
    self.encoder = BFMEncoder()
    self.decoder = BFMDecoder()

    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    sd = ckpt["model_state_dict"]
    # Decoder weights: every ``actor.*`` key (except actor_task_embedder.*),
    # re-prefixed onto self.decoder.transformer.
    dec_sd = {
      "transformer." + k[len("actor."):]: v
      for k, v in sd.items()
      if k.startswith("actor.") and not k.startswith("actor_task_embedder.")
    }
    # Encoder weights: task_projection + cached per-block cond_norm scales.
    cn_stack = torch.stack([
      sd[f"actor.transformer_blocks.{i}.cond_norm.scale"]
      for i in range(BFMEncoder.NUM_BLOCKS)
    ], dim=0)
    enc_sd = {
      "task_projection.weight": sd["actor_task_embedder.task_projection.weight"],
      "task_projection.bias":   sd["actor_task_embedder.task_projection.bias"],
      "cond_norm_scales":       cn_stack,
    }
    miss_d, unex_d = self.decoder.load_state_dict(dec_sd, strict=True)
    miss_e, unex_e = self.encoder.load_state_dict(enc_sd, strict=True)
    if miss_d or unex_d or miss_e or unex_e:
      raise RuntimeError(
        f"state_dict mismatch: decoder missing={miss_d} unexpected={unex_d}; "
        f"encoder missing={miss_e} unexpected={unex_e}"
      )

    self.to(device).eval()
    for p in self.parameters():
      p.requires_grad_(False)

  # ---------- Back-compat aliases (track_motion / track_latent / etc.) ------

  @property
  def task_embedder(self) -> BFMEncoder:
    """Legacy attribute name. Prefer ``self.encoder``."""
    return self.encoder

  @property
  def transformer(self) -> HumanoidTransformer:
    """Legacy attribute. The actual nn.Module is inside the decoder."""
    return self.decoder.transformer

  @torch.no_grad()
  def encode_task(self, task_obs: torch.Tensor) -> torch.Tensor:
    """ref → latent. ``task_obs`` (B, F, 267) → raw ``latent`` (B, F, 256).
    Feed directly to ``decode_action``. For latent-space analysis use
    ``self.encoder.normalize(latent)`` or ``self.encoder.feature_view(...)``.
    """
    return self.encoder.encode(task_obs)

  @torch.no_grad()
  def decode_action(
    self,
    prop_obs: torch.Tensor,
    action_obs: torch.Tensor,
    latent: torch.Tensor,
  ) -> torch.Tensor:
    """latent + self state → policy mean (29,). PD target before action_scale.

    Shapes:
      prop_obs:   (B, H=3, 64)
      action_obs: (B, H=3, 29)
      latent:     (B, F=6, 256) from ``encode_task`` (or interpolated).
    """
    return self.decoder.decode(prop_obs, action_obs, latent)

  # ---------- New: load from already-split ckpts -----------------------------

  @classmethod
  def from_split_ckpts(
    cls, encoder_path: str | Path, decoder_path: str | Path, device: str = "cuda"
  ) -> "BFMTwoStage":
    """Construct without ever touching the raw ckpt.

    Useful when you only have the split ``bfm_encoder.pt`` + ``bfm_decoder.pt``
    on disk and don't want to ship the full 73 MB raw state_dict around.
    """
    obj = cls.__new__(cls)
    nn.Module.__init__(obj)
    obj.device = device
    obj.encoder = BFMEncoder.from_split_ckpt(encoder_path, device=device)
    obj.decoder = BFMDecoder.from_split_ckpt(decoder_path, device=device)
    obj.eval()
    return obj
