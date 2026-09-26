#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

import dnni_module_accounting_probe as p


def solve(bias_bytes: int) -> int:
    core = p.CORE_MATRIX_COUNT * p.MATRIX_BYTES
    projection_bytes = p.MODULE_STRIDE_BYTES - core - bias_bytes
    assert projection_bytes % (p.HIDDEN * 2) == 0
    return projection_bytes // (p.HIDDEN * 2)


def main() -> None:
    assert solve(6 * 512 * 2) == 506
    assert solve(3 * 512 * 4) == 506
    assert (
        6 * (512 * 512 * 2)
        + (512 * 506 * 2)
        + (6 * 512 * 2)
        == p.MODULE_STRIDE_BYTES
    )
    assert (
        6 * (512 * 512 * 2)
        + (512 * 506 * 2)
        + (3 * 512 * 4)
        == p.MODULE_STRIDE_BYTES
    )
    print("dnni_module_accounting_smoke: ok")


if __name__ == "__main__":
    main()
