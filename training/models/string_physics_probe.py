from __future__ import annotations
import torch
from torch import nn

PHYSICS_FIELDS = (
    "bow_speed",
    "bow_force",
    "contact_point",
    "vibrato_depth_cents",
    "vibrato_rate_hz",
    "friction_noise",
    "spectral_slope",
    "contact_notch_depth",
    "residual_energy",
    "section_pitch_spread_cents",
    "section_timing_spread_ms",
    "section_bow_spread",
)

class StringPhysicsProbe(nn.Module):
    """Tiny TRAINING-ONLY latent probe.

    It is never included in decoder-only release checkpoints. The probe turns
    exact clean-room physical labels into pressure on the VAE latent geometry,
    without making modeled audio a timbre anchor.
    """
    def __init__(self, latent_dim: int = 64, hidden: int = 48, outputs: int = len(PHYSICS_FIELDS)):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(latent_dim, hidden, 1), nn.SiLU(),
            nn.Conv1d(hidden, hidden, 1), nn.SiLU(),
        )
        self.head = nn.Linear(hidden, outputs)
    def forward(self, z):
        return self.head(self.net(z).mean(dim=-1))

def physics_targets(rows, device=None):
    """Return normalized targets and validity masks from heterogeneous manifests."""
    vals=[]; masks=[]
    scales={
        "bow_speed": 1.0, "bow_force": 1.0, "contact_point": 1.0,
        "vibrato_depth_cents": 80.0, "vibrato_rate_hz": 10.0, "friction_noise": 1.0,
        "spectral_slope": 2.0, "contact_notch_depth": 1.0, "residual_energy": .5,
        "section_pitch_spread_cents": 24.0, "section_timing_spread_ms": 40.0, "section_bow_spread": .35,
    }
    for row in rows:
        rv=[]; rm=[]
        for f in PHYSICS_FIELDS:
            known_key=f+"_known"
            origin=str(row.get('training_origin') or row.get('source_kind') or 'real').lower()
            known = bool(row.get(known_key, (origin=='modeled' and f in row)))
            try: v=float(row.get(f,0.0))/scales[f]
            except (TypeError,ValueError): v=0.0; known=False
            rv.append(v); rm.append(1.0 if known else 0.0)
        vals.append(rv); masks.append(rm)
    return torch.tensor(vals,dtype=torch.float32,device=device), torch.tensor(masks,dtype=torch.float32,device=device)

def masked_physics_loss(pred, target, mask):
    denom=mask.sum().clamp_min(1.0)
    return (((pred-target)**2)*mask).sum()/denom
