"""Compact rectified-flow sampling helpers for SONICRAFT.

No model weights live here. The sampler is deliberately runtime-small:
- Euler / Heun ODE integration
- MIDI-authority preserving classifier-free guidance
- deterministic noise helpers live in the backend
"""
from __future__ import annotations
from typing import Dict

# These fields are the learned expressive/performance layer. The strict note trajectory
# (pitch/gate/onset/velocity/note progress/phrase position/intervals) stays intact in the
# guidance base branch so CFG cannot rewrite the score.
_EXPRESSIVE_ZERO = {
    'dynamics', 'vibrato', 'expression', 'legato', 'pitchbend',
    'transition_speed', 'short_tightness', 'attack_character',
    'bow_change_prob', 'vibrato_onset', 'tempo_bpm', 'seconds_per_beat',
    'note_duration_beats', 'transition_target_ms', 'speed_profile',
    'vibrato_depth_cents', 'vibrato_rate_hz', 'vibrato_jitter',
    'dynamics_known', 'vibrato_known', 'expression_known', 'legato_known',
    'pitchbend_known', 'timing_known', 'vibrato_physics_known', 'frontier_context',
}


def midi_authority_base(controls: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """Return the cond-dropout-compatible base branch used by runtime CFG.

    Articulation is intentionally kept authoritative here; CFG only pushes expressive
    realization around the written score/keyswitch decisions.
    """
    import torch
    out = {}
    for key, value in controls.items():
        if key in _EXPRESSIVE_ZERO and torch.is_tensor(value):
            out[key] = torch.zeros_like(value)
        else:
            out[key] = value
    return out


def _batch_cat(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    import torch
    if a.ndim == 0:
        return torch.stack([a, b], 0)
    return torch.cat([a, b], dim=0)


def guided_velocity(model, x: torch.Tensor, t: torch.Tensor,
                    controls: Dict[str, torch.Tensor], guidance_scale: float = 1.0,
                    flow_h: torch.Tensor | None = None) -> torch.Tensor:
    """One model call with batched base/full branches when guidance is enabled."""
    import torch
    scale = float(guidance_scale)
    if scale <= 1.000001:
        return model(x, t, flow_h=flow_h, **controls)
    base = midi_authority_base(controls)
    xb = torch.cat([x, x], 0)
    tb = torch.cat([t, t], 0)
    hb = None if flow_h is None else _batch_cat(flow_h, flow_h)
    cb = {k: _batch_cat(base[k], controls[k]) for k in controls}
    pred = model(xb, tb, flow_h=hb, **cb)
    p0, p1 = pred.chunk(2, 0)
    return p0 + (p1 - p0) * scale


def sample_rectified_flow(model, x0: torch.Tensor, controls: Dict[str, torch.Tensor],
                          steps: int = 8, solver: str = 'euler', guidance_scale: float = 1.0) -> torch.Tensor:
    """Integrate a rectified-flow velocity field from t=0 -> 1.

    ``heun`` uses two evaluations per step and is provided as an A/B challenger for
    lower step counts. ``euler`` remains the default because RF training explicitly
    favors straight trajectories and matches the strongest violin reference path.
    """
    n = max(1, int(steps))
    solver = str(solver).lower()
    if solver not in ('euler', 'heun'):
        raise ValueError(f'unknown flow solver: {solver}')
    x = x0
    dt = 1.0 / n
    for i in range(n):
        t0 = x.new_full((x.shape[0],), i / n)
        h = x.new_full((x.shape[0],), dt)
        v0 = guided_velocity(model, x, t0, controls, guidance_scale, flow_h=h)
        if solver == 'euler' or i == n - 1:
            x = x + v0 * dt
        else:
            xp = x + v0 * dt
            t1 = x.new_full((x.shape[0],), (i + 1) / n)
            v1 = guided_velocity(model, xp, t1, controls, guidance_scale, flow_h=h)
            x = x + (v0 + v1) * (0.5 * dt)
    return x



def sample_shortcut_flow(model, x0: torch.Tensor, controls: Dict[str, torch.Tensor],
                         steps: int = 1, guidance_scale: float = 1.0) -> torch.Tensor:
    """Dyadic/interval-conditioned shortcut sampler.

    The runtime state is identical to ordinary Euler RF; the only difference is that
    each model evaluation is told the requested jump size ``flow_h``. A shortcut-trained
    checkpoint can therefore serve 1/2/4/8-step budgets with the same weights.
    """
    return sample_rectified_flow(model, x0, controls, steps=max(1, int(steps)),
                                 solver='euler', guidance_scale=guidance_scale)
