#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_operation_semantics_probe import spectral_signature, classify_signature


def main() -> None:
    rng = np.random.default_rng(7)

    dense = rng.normal(0, .05, size=(64,64)).astype(np.float32)
    dense_sig = spectral_signature(dense)
    dense_class = classify_signature(dense_sig)
    assert dense_class["dense_full_rank_like"]
    assert not dense_class["low_rank_like"]
    assert not dense_class["identity_like"]

    ident = np.eye(64, dtype=np.float32)
    ident_class = classify_signature(spectral_signature(ident))
    assert ident_class["identity_like"]
    assert ident_class["near_orthogonal"]

    low = (
        rng.normal(size=(64,4)).astype(np.float32)
        @ rng.normal(size=(4,64)).astype(np.float32)
    )
    low_class = classify_signature(spectral_signature(low))
    assert low_class["low_rank_like"]
    assert not low_class["dense_full_rank_like"]

    print("dnni_operation_semantics_smoke: ok")


if __name__ == "__main__":
    main()
