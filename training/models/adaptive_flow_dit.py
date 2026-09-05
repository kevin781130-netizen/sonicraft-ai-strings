"""SONICRAFT compact AdaLN-Zero rectified-flow / shortcut DiT.

v1.7 frontier additions are deliberately parameter-efficient:
- optional shared AdaLN modulation across depth (block identity is a tiny learned embedding),
- optional recurrent/weight-tied transformer block challenger,
- dyadic shortcut step-size conditioning using fixed Fourier features + one learned gain vector,
- PyTorch SDPA so no xFormers/Triton package is required at runtime.

Legacy v1.5/v1.6 layouts remain the default, so old checkpoints still strict-load.
No third-party weights, datasets, or assets live here.
"""
from __future__ import annotations
import math
import torch
from torch import nn
import torch.nn.functional as F


class FourierTime(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = int(dim)
        self.mlp = nn.Sequential(
            nn.Linear(self.dim, self.dim * 4), nn.SiLU(), nn.Linear(self.dim * 4, self.dim)
        )

    @staticmethod
    def features(t: torch.Tensor, dim: int, scale: float = 1000.0) -> torch.Tensor:
        half = int(dim) // 2
        f = torch.exp(-math.log(10000.0) * torch.arange(half, device=t.device, dtype=t.dtype) / max(1, half - 1))
        x = t[:, None] * f[None, :] * float(scale)
        e = torch.cat([x.sin(), x.cos()], -1)
        if e.shape[-1] < int(dim):
            e = F.pad(e, (0, 1))
        return e

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        return self.mlp(self.features(t, self.dim))


def modulate(x: torch.Tensor, shift: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    return x * (1.0 + scale[:, None, :]) + shift[:, None, :]


class SDPASelfAttention(nn.Module):
    """Parameter-equivalent MHA using PyTorch's native SDPA dispatcher."""
    def __init__(self, dim: int, heads: int, dropout: float = 0.0):
        super().__init__()
        if dim % heads:
            raise ValueError(f'dim={dim} must be divisible by heads={heads}')
        self.dim = int(dim); self.heads = int(heads); self.head_dim = self.dim // self.heads
        self.dropout = float(dropout)
        self.qkv = nn.Linear(self.dim, 3 * self.dim)
        self.proj = nn.Linear(self.dim, self.dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, d = x.shape
        qkv = self.qkv(x).view(b, t, 3, self.heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv.unbind(0)
        y = F.scaled_dot_product_attention(
            q, k, v,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=False,
        )
        return self.proj(y.transpose(1, 2).contiguous().view(b, t, d))


class AdaLNFlowBlock(nn.Module):
    def __init__(self, dim: int, heads: int, mlp_ratio: float = 3.0, dropout: float = 0.0,
                 attention_impl: str = 'mha', shared_adaln: bool = False):
        super().__init__()
        hidden = max(dim, int(round(dim * float(mlp_ratio))))
        self.n1 = nn.LayerNorm(dim, elementwise_affine=False, eps=1e-6)
        self.n2 = nn.LayerNorm(dim, elementwise_affine=False, eps=1e-6)
        self.attention_impl = str(attention_impl).lower()
        if self.attention_impl == 'sdpa':
            self.attn = SDPASelfAttention(dim, heads, dropout=dropout)
        elif self.attention_impl == 'mha':
            self.attn = nn.MultiheadAttention(dim, heads, dropout=dropout, batch_first=True)
        else:
            raise ValueError(f'unknown attention implementation: {attention_impl}')
        self.ff = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(), nn.Linear(hidden, dim))
        self.ada = None if bool(shared_adaln) else nn.Sequential(nn.SiLU(), nn.Linear(dim, 6 * dim))
        if self.ada is not None:
            nn.init.zeros_(self.ada[-1].weight)
            nn.init.zeros_(self.ada[-1].bias)

    def forward(self, x: torch.Tensor, c: torch.Tensor, ada_params: torch.Tensor | None = None) -> torch.Tensor:
        params = self.ada(c) if self.ada is not None else ada_params
        if params is None:
            raise RuntimeError('shared AdaLN block requires externally supplied modulation')
        s1, sc1, g1, s2, sc2, g2 = params.chunk(6, -1)
        q = modulate(self.n1(x), s1, sc1)
        if self.attention_impl == 'sdpa':
            a = self.attn(q)
        else:
            a = self.attn(q, q, q, need_weights=False)[0]
        x = x + g1[:, None, :] * a
        x = x + g2[:, None, :] * self.ff(modulate(self.n2(x), s2, sc2))
        return x


class AdaptiveFlowDiT(nn.Module):
    """AdaLN-Zero velocity/shortcut backbone for a pre-conditioned latent sequence.

    ``shared_adaln`` removes the repeated d->6d modulation matrix from every block and
    keeps one shared matrix. A tiny per-depth embedding preserves block identity.

    ``weight_tied`` is an aggressive challenger that recurrently applies one attention/MLP
    block ``depth`` times. It keeps compute depth while removing duplicate block weights.

    ``interval_conditioning`` exposes the desired shortcut step size ``flow_h`` without
    adding another MLP: fixed Fourier features are scaled by a single learned vector.
    """

    def __init__(self, dim: int = 384, depth: int = 8, heads: int = 8,
                 mlp_ratio: float = 3.0, dropout: float = 0.0,
                 attention_impl: str = 'mha', shared_adaln: bool = False,
                 weight_tied: bool = False, interval_conditioning: bool = False):
        super().__init__()
        self.dim = int(dim); self.depth = int(depth)
        self.attention_impl = str(attention_impl).lower()
        self.shared_adaln = bool(shared_adaln)
        self.weight_tied = bool(weight_tied)
        self.interval_conditioning = bool(interval_conditioning)
        self.time = FourierTime(dim)
        self.cond = nn.Sequential(nn.Linear(dim, dim), nn.SiLU(), nn.Linear(dim, dim))

        block_kw = dict(dim=dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout,
                        attention_impl=self.attention_impl, shared_adaln=self.shared_adaln)
        if self.weight_tied:
            self.shared_block = AdaLNFlowBlock(**block_kw)
            self.blocks = nn.ModuleList()
        else:
            self.shared_block = None
            self.blocks = nn.ModuleList([AdaLNFlowBlock(**block_kw) for _ in range(self.depth)])

        if self.shared_adaln:
            self.shared_ada = nn.Sequential(nn.SiLU(), nn.Linear(dim, 6 * dim))
            nn.init.zeros_(self.shared_ada[-1].weight)
            nn.init.zeros_(self.shared_ada[-1].bias)
            # Small identity signal costs depth*dim parameters instead of depth*d*6d matrices.
            self.block_condition = nn.Parameter(torch.empty(self.depth, dim))
            nn.init.normal_(self.block_condition, mean=0.0, std=0.02)
        else:
            self.shared_ada = None
            self.register_parameter('block_condition', None)

        if self.interval_conditioning:
            # Zero-init preserves a normal RF initialization while gradients can immediately
            # learn how much each fixed Fourier channel should encode the desired jump size.
            self.step_gain = nn.Parameter(torch.zeros(dim))
        else:
            self.register_parameter('step_gain', None)

        self.norm = nn.LayerNorm(dim, elementwise_affine=False, eps=1e-6)
        self.out_mod = nn.Sequential(nn.SiLU(), nn.Linear(dim, 2 * dim))
        nn.init.zeros_(self.out_mod[-1].weight)
        nn.init.zeros_(self.out_mod[-1].bias)

    def _condition(self, t: torch.Tensor, phrase_condition: torch.Tensor,
                   flow_h: torch.Tensor | None) -> torch.Tensor:
        c = self.time(t) + self.cond(phrase_condition)
        if self.interval_conditioning:
            if flow_h is None:
                flow_h = torch.zeros_like(t)
            if flow_h.ndim == 0:
                flow_h = flow_h.expand_as(t)
            # Lower frequency scale is intentional: h lies in [0,1] and must remain smooth.
            step = FourierTime.features(flow_h.to(dtype=t.dtype), self.dim, scale=32.0)
            c = c + step * self.step_gain[None, :]
        return c

    def forward(self, x: torch.Tensor, t: torch.Tensor, phrase_condition: torch.Tensor,
                flow_h: torch.Tensor | None = None) -> torch.Tensor:
        c = self._condition(t, phrase_condition, flow_h)
        for i in range(self.depth):
            block = self.shared_block if self.weight_tied else self.blocks[i]
            if self.shared_adaln:
                ci = c + self.block_condition[i][None, :]
                params = self.shared_ada(ci)
                x = block(x, ci, params)
            else:
                x = block(x, c)
        shift, scale = self.out_mod(c).chunk(2, -1)
        return modulate(self.norm(x), shift, scale)
