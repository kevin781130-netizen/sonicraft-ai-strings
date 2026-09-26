#!/usr/bin/env python3
from __future__ import annotations

"""Build an evidence-graded graph fragment from observed DNNI structure.

This tool only derives dimension compatibility and basis-equivalence constraints
from previously verified tensor/dtype maps. It does not assign proprietary op names,
recover packing/permutation transforms, or claim executable graph semantics.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

LATENT_WIDTH = 512


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_graph_fragment(tensor_map: dict, dtype_map: dict) -> dict:
    shape = tensor_map.get("per_module", {}).get("shape")
    if shape != [LATENT_WIDTH, LATENT_WIDTH]:
        raise ValueError(f"expected verified {LATENT_WIDTH}x{LATENT_WIDTH} core matrices")

    module_count = int(tensor_map["modules"]["count"])
    matrix_count = int(tensor_map["per_module"]["matrix_count"])

    modules = []
    for module_index in range(module_count):
        matrices = []
        for matrix_index in range(matrix_count):
            shared = matrix_index >= 4
            matrices.append({
                "id": f"m{module_index}.w{matrix_index}",
                "module": module_index,
                "matrix_index": matrix_index,
                "dtype": "float16_le",
                "shape": [LATENT_WIDTH, LATENT_WIDTH],
                "bytes": int(tensor_map["per_module"]["matrix_bytes"]),
                "parameter_scope": "cross_instrument_shared" if shared else "cross_instrument_reordered",
                "semantic_role": "unknown",
            })
        modules.append({
            "id": f"module_{module_index}",
            "width": LATENT_WIDTH,
            "matrix_count": matrix_count,
            "matrices": matrices,
        })

    basis = tensor_map.get("basis_order_equivalence", {})
    constraints = []
    for obs in basis.get("observations", []):
        constraints.append({
            "type": "basis_order_equivalence_evidence",
            "relation": obs["relation"],
            "matches": obs["matches"],
            "total": obs["total"],
        })

    projections = []
    width_counts = Counter()
    for i, span in enumerate(dtype_map.get("spans", dtype_map.get("float32_candidate_spans", []))):
        elements = int(span["element_count"])
        if elements % LATENT_WIDTH:
            continue
        other = elements // LATENT_WIDTH
        width_counts[other] += 1
        projections.append({
            "id": f"fp32_projection_candidate_{i}",
            "offset": int(span["offset"]),
            "bytes": int(span["bytes"]),
            "dtype": "float32_le",
            "element_count": elements,
            "latent_width": LATENT_WIDTH,
            "other_width": other,
            "orientation_candidates": [
                [LATENT_WIDTH, other],
                [other, LATENT_WIDTH],
            ],
            "direction": "unknown",
            "semantic_role": "unknown",
            "confidence": "dimension-compatible",
        })

    projection_families = [
        {
            "latent_width": LATENT_WIDTH,
            "other_width": width,
            "count": count,
        }
        for width, count in sorted(width_counts.items())
    ]

    return {
        "schema": "sonicraft-dnni-graph-fragment-v1",
        "truth_boundary": (
            "Dimension/basis constraints only. No op type, activation, graph direction, "
            "tensor name, decoder role, conditioning semantic, or proprietary permutation "
            "mapping is asserted or reconstructed."
        ),
        "latent_width": LATENT_WIDTH,
        "verified_core": {
            "module_count": module_count,
            "matrices_per_module": matrix_count,
            "matrix_shape": [LATENT_WIDTH, LATENT_WIDTH],
            "matrix_dtype": "float16_le",
            "module_stride_bytes": int(tensor_map["modules"]["stride_bytes"]),
        },
        "basis_constraints": constraints,
        "projection_candidates": projections,
        "projection_families": projection_families,
        "candidate_dimension_graph": {
            "nodes": [
                {"id": "latent_512", "width": 512, "confidence": "verified"},
                *[
                    {
                        "id": f"feature_{x['other_width']}",
                        "width": x["other_width"],
                        "confidence": "dimension-compatible",
                    }
                    for x in projection_families
                ],
            ],
            "edges": [
                {
                    "id": p["id"],
                    "between": ["latent_512", f"feature_{p['other_width']}"],
                    "orientation": "unknown",
                    "dtype": p["dtype"],
                    "offset": p["offset"],
                    "bytes": p["bytes"],
                }
                for p in projections
            ],
        },
        "next_evidence_gates": [
            "resolve exact FP32 span boundaries at finer than 64 KiB consensus",
            "identify whether 512-compatible projections are input-side or output-side",
            "locate adjacent bias/vector tensors if present",
            "find an independently verifiable nonlinear/state boundary",
            "produce one finite graph-fragment output without decoder assumptions",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tensor-map",
        default="training/configs/dnni_observed_tensor_map.json",
    )
    ap.add_argument(
        "--dtype-map",
        default="training/configs/dnni_observed_dtype_map.json",
    )
    ap.add_argument("--out")
    args = ap.parse_args()

    result = build_graph_fragment(_load(args.tensor_map), _load(args.dtype_map))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
