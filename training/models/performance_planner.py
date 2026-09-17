from __future__ import annotations

"""Small symbolic model that plans string-performance controls before rendering."""

import torch
from torch import nn

from performance_planner_contract import ARTICULATIONS, CONTINUOUS_TARGETS, FEATURE_NAMES


class SymbolicPerformancePlanner(nn.Module):
    """Note-sequence Transformer for articulation and expression planning.

    This model never renders audio. It predicts note-level control suggestions that
    are merged with authoritative written controls before the audio renderer.
    """

    def __init__(
        self,
        *,
        feature_dim: int = len(FEATURE_NAMES),
        d_model: int = 128,
        layers: int = 4,
        heads: int = 4,
        ff_mult: int = 3,
        dropout: float = 0.08,
        max_notes: int = 512,
    ) -> None:
        super().__init__()
        if d_model % heads:
            raise ValueError("d_model must be divisible by heads")
        self.feature_dim = int(feature_dim)
        self.d_model = int(d_model)
        self.max_notes = int(max_notes)
        self.input_proj = nn.Sequential(
            nn.Linear(self.feature_dim, self.d_model),
            nn.LayerNorm(self.d_model),
            nn.GELU(),
        )
        self.position = nn.Parameter(torch.zeros(1, self.max_notes, self.d_model))
        nn.init.normal_(self.position, mean=0.0, std=0.015)
        layer = nn.TransformerEncoderLayer(
            d_model=self.d_model,
            nhead=int(heads),
            dim_feedforward=self.d_model * int(ff_mult),
            dropout=float(dropout),
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=int(layers), norm=nn.LayerNorm(self.d_model))
        self.articulation_head = nn.Linear(self.d_model, len(ARTICULATIONS))
        self.continuous_head = nn.Linear(self.d_model, len(CONTINUOUS_TARGETS))

    def forward(self, features: torch.Tensor, padding_mask: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        if features.ndim != 3:
            raise ValueError("features must have shape [batch, notes, features]")
        if features.shape[-1] != self.feature_dim:
            raise ValueError(f"feature dimension {features.shape[-1]} != {self.feature_dim}")
        notes = int(features.shape[1])
        if notes > self.max_notes:
            raise ValueError(f"note sequence length {notes} exceeds max_notes={self.max_notes}")
        x = self.input_proj(features) + self.position[:, :notes]
        x = self.encoder(x, src_key_padding_mask=padding_mask)
        return {
            "articulation_logits": self.articulation_head(x),
            # All continuous training targets are normalized into [0,1].
            "continuous": torch.sigmoid(self.continuous_head(x)),
        }

    def config(self) -> dict[str, int | float]:
        first = self.encoder.layers[0]
        return {
            "feature_dim": self.feature_dim,
            "d_model": self.d_model,
            "layers": len(self.encoder.layers),
            "heads": int(first.self_attn.num_heads),
            "ff_mult": int(first.linear1.out_features // self.d_model),
            "dropout": float(first.dropout.p),
            "max_notes": self.max_notes,
        }
