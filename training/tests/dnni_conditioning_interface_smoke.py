#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_conditioning_interface_probe import (
    MATRIX_BYTES,
    OLD_506_BOUNDARY_BYTES,
    _packet_decomposition,
)


def main() -> None:
    assert MATRIX_BYTES == 524288
    assert OLD_506_BOUNDARY_BYTES == 518144

    fp16 = _packet_decomposition(5136, "float16_le")
    assert fp16 == {
        "value_count": 2568,
        "scalar_prefix_candidate": 8,
        "vector_width_candidate": 512,
        "vector_count_candidate": 5,
    }

    fp32 = _packet_decomposition(5136, "float32_le")
    assert fp32 == {
        "value_count": 1284,
        "scalar_prefix_candidate": 4,
        "vector_width_candidate": 256,
        "vector_count_candidate": 5,
    }

    assert 519152 != OLD_506_BOUNDARY_BYTES
    assert 519152 - OLD_506_BOUNDARY_BYTES == 1008
    print("dnni_conditioning_interface_smoke: ok")


if __name__ == "__main__":
    main()
