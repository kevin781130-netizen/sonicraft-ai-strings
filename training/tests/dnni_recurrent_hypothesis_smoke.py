#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_recurrent_hypothesis_probe import _probe_input, _sigmoid, INPUT_WIDTH, HIDDEN


def main() -> None:
    x = _probe_input()
    assert x.shape == (INPUT_WIDTH,)
    assert abs(float(np.linalg.norm(x)) - 1.0) < 1e-5

    z = _sigmoid(np.array([-100.0, 0.0, 100.0], dtype=np.float32))
    assert z[0] < 1e-6
    assert abs(float(z[1]) - 0.5) < 1e-6
    assert z[2] > 1.0 - 1e-6

    h = np.zeros(HIDDEN, dtype=np.float32)
    assert h.shape == (512,)
    print("dnni_recurrent_hypothesis_smoke: ok")


if __name__ == "__main__":
    main()
