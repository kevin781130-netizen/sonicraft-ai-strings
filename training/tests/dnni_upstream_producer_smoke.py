#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

import dnni_upstream_producer_probe as p


def main() -> None:
    a = p.layout_accounting()
    assert a["regular_matches"]
    assert a["final_matches"]
    assert a["final_ends_at_left_bank"]

    assert (
        5 * (512 * 512 * 2)
        + 12 * 512 * 2
        == 2_633_728
    )
    assert (
        4 * (512 * 512 * 2)
        + 512 * 452 * 2
        + 4 * 512 * 4
        == 2_568_192
    )
    assert p.FINAL_MODULE_START + p.FINAL_MODULE_BYTES == p.LEFT_BANK_START

    print("dnni_upstream_producer_smoke: ok")


if __name__ == "__main__":
    main()
