from __future__ import annotations
"""Utilities for optional per-frame control-curve sidecars.

Phrase datasets can attach ``control_curves`` to a manifest row. Encoders use the
sidecar when present and otherwise retain the legacy scalar-row behavior.
"""
from pathlib import Path
from typing import Mapping, Any
import numpy as np


def _resample(values: np.ndarray, frames: int, *, discrete: bool = False) -> np.ndarray:
    x = np.asarray(values, dtype=np.float32).reshape(-1)
    if x.size == 0:
        return np.zeros(frames, np.float32)
    if x.size == frames:
        return x.astype(np.float32, copy=False)
    if x.size == 1:
        return np.full(frames, float(x[0]), np.float32)
    if discrete:
        idx = np.rint(np.linspace(0, x.size - 1, frames)).astype(np.int64)
        return x[idx].astype(np.float32, copy=False)
    old = np.linspace(0.0, 1.0, x.size, dtype=np.float64)
    new = np.linspace(0.0, 1.0, frames, dtype=np.float64)
    return np.interp(new, old, x.astype(np.float64)).astype(np.float32)


def load_control_sidecar(row: Mapping[str, Any], frames: int) -> dict[str, np.ndarray]:
    raw = row.get("control_curves")
    if not raw:
        return {}
    path = Path(str(raw))
    if not path.is_file():
        raise FileNotFoundError(f"control curve sidecar not found: {path}")
    out: dict[str, np.ndarray] = {}
    with np.load(path, allow_pickle=False) as data:
        for name in data.files:
            discrete = name in {"articulation_curve"}
            out[name] = _resample(data[name], frames, discrete=discrete)
    return out


def control_curve(
    sidecar: Mapping[str, np.ndarray],
    name: str,
    frames: int,
    default: float | np.ndarray,
    *,
    discrete: bool = False,
) -> np.ndarray:
    if name in sidecar:
        return _resample(sidecar[name], frames, discrete=discrete)
    if np.isscalar(default):
        return np.full(frames, float(default), np.float32)
    return _resample(np.asarray(default, np.float32), frames, discrete=discrete)
