#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_bank_direction_probe import _operator_rms_gain, _rank


def main() -> None:
    eye = np.eye(8, dtype=np.float32)
    assert abs(_operator_rms_gain(eye) - 1.0) < 1e-6
    assert _rank(eye) == 8

    low = np.zeros((8, 8), dtype=np.float32)
    low[:, 0] = 1.0
    assert _rank(low) == 1

    print("dnni_bank_direction_smoke: ok")


if __name__ == "__main__":
    main()
