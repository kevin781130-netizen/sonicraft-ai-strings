#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

import dnni_recurrent_signature_probe as p


def main() -> None:
    assert p.HIDDEN == 512
    assert p.CORE_MATRIX_COUNT == 6
    assert p.MATRIX_BYTES == 512 * 512 * 2
    assert p.SHARED_SLAB_BYTES == 506 * 512 * 2
    assert p.SUFFIX_BYTES == 6 * 512 * 2
    assert p.SUFFIX_BYTES // 2 // p.HIDDEN == 6
    assert p.SUFFIX_BYTES // 4 // p.HIDDEN == 3
    print("dnni_recurrent_signature_smoke: ok")


if __name__ == "__main__":
    main()
