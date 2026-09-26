#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_graph_fragment_probe import build_graph_fragment


def main() -> None:
    tensor = {
        "modules": {"count": 4, "stride_bytes": 3670016},
        "per_module": {
            "shape": [512, 512],
            "matrix_count": 7,
            "matrix_bytes": 524288,
        },
        "basis_order_equivalence": {
            "observations": [
                {
                    "relation": "matrix_1 row ordering == matrix_2 row ordering",
                    "matches": 56,
                    "total": 56,
                }
            ]
        },
    }
    dtype = {
        "spans": [
            {"offset": 1, "bytes": 262144, "element_count": 65536},
            {"offset": 2, "bytes": 131072, "element_count": 32768},
            {"offset": 3, "bytes": 589824, "element_count": 147456},
            {"offset": 4, "bytes": 4000, "element_count": 1000},
        ]
    }
    result = build_graph_fragment(tensor, dtype)
    assert result["latent_width"] == 512
    assert result["verified_core"]["module_count"] == 4
    assert result["projection_families"] == [
        {"latent_width": 512, "other_width": 64, "count": 1},
        {"latent_width": 512, "other_width": 128, "count": 1},
        {"latent_width": 512, "other_width": 288, "count": 1},
    ]
    dims = {
        tuple(x["orientation_candidates"][0])
        for x in result["projection_candidates"]
    }
    assert dims == {(512, 64), (512, 128), (512, 288)}
    print("dnni_graph_fragment_smoke: ok")


if __name__ == "__main__":
    main()
