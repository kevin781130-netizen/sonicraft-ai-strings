from __future__ import annotations
"""Parameter-free physics geometry regularizer for modeled string examples.

The loss only activates for pairs that share enough *known* physical labels.
It never asks modeled audio to match real timbre. Instead it asks relative
latent distances to vary coherently with exact clean-room physical distances.
"""
import torch
import torch.nn.functional as F


def physics_metric_alignment_loss(z: torch.Tensor, targets: torch.Tensor, mask: torch.Tensor,
                                  modeled: torch.Tensor | None = None, min_common: int = 4) -> torch.Tensor:
    if z.ndim != 3: raise ValueError('z must be [B,C,T]')
    B=z.shape[0]
    if B<2: return z.sum()*0.0
    if modeled is None: modeled=torch.ones(B,dtype=torch.bool,device=z.device)
    else: modeled=modeled.to(device=z.device,dtype=torch.bool)
    pooled=z.mean(-1)
    # Scale-free latent geometry. Normalization prevents raw VAE variance from
    # becoming the target and keeps this loss a weak relational constraint.
    pooled=F.normalize(pooled.float(),dim=-1,eps=1e-6)
    pd=[]; ld=[]
    for i in range(B):
        if not bool(modeled[i]): continue
        for j in range(i+1,B):
            if not bool(modeled[j]): continue
            common=(mask[i]>0)&(mask[j]>0)
            if int(common.sum())<int(min_common): continue
            dphys=torch.sqrt(((targets[i,common]-targets[j,common])**2).mean()+1e-8)
            dlat=1.0-(pooled[i]*pooled[j]).sum()
            pd.append(dphys); ld.append(dlat)
    if len(pd)<2: return z.sum()*0.0
    pd=torch.stack(pd); ld=torch.stack(ld)
    # Match centered, scale-normalized pair geometry, not absolute units.
    pd=(pd-pd.mean())/(pd.std(unbiased=False)+1e-5)
    ld=(ld-ld.mean())/(ld.std(unbiased=False)+1e-5)
    return F.smooth_l1_loss(ld,pd)
