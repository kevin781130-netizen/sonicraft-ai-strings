#!/usr/bin/env python3
from __future__ import annotations

"""Verify exact byte-accounting for the observed 3.5 MiB DNNI module family.

The key question is whether 506 is merely a cross-model equality coincidence or an
exact dimension implied by the module serialization. The probe solves the remaining
projection width from module bytes after accounting for six 512x512 FP16 matrices
and the observed bias packet variants.

This establishes a strong layout candidate only. It does not identify the musical
meaning of the 506-wide vector or prove a recurrent operation.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry
from dnni_dtype_map_probe import numeric_stats, fp16_plausible, fp32_candidate, median_stats

HIDDEN = 512
MODULE_START = 40_304_640
MODULE_STRIDE_BYTES = 3_670_016
MODULE_COUNT = 4
MATRIX_BYTES = HIDDEN * HIDDEN * 2
CORE_MATRIX_COUNT = 6
FP16_BIAS_VECTORS = 6
FP32_BIAS_VECTORS = 3


def _read(model, rel: int, n: int) -> bytes:
    w = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(w.offset + rel)
        data = f.read(n)
    if len(data) != n:
        raise RuntimeError(f"{model.path}: short read at {rel}")
    return data


def _identity_count(models, rel: int, n: int) -> int:
    ref = hashlib.sha256(_read(models[0], rel, n)).digest()
    return sum(hashlib.sha256(_read(m, rel, n)).digest() == ref for m in models)


def _consensus_stats(models, rel: int, n: int):
    return median_stats([numeric_stats(_read(m, rel, n)) for m in models])


def _common_mask(models, rel: int, dtype: str, vectors: int) -> dict:
    arrays = [
        np.frombuffer(_read(m, rel, vectors * HIDDEN * np.dtype(dtype).itemsize), dtype=dtype)
        .reshape(vectors, HIDDEN)
        for m in models
    ]
    base = arrays[0]
    eq = np.ones(base.shape, dtype=bool)
    for a in arrays[1:]:
        eq &= (a == base)

    rows = []
    for i in range(vectors):
        row = eq[i]
        prefix = 0
        for v in row:
            if not v:
                break
            prefix += 1
        rows.append({
            "vector_index": i,
            "exact_common_values": int(np.sum(row)),
            "exact_common_prefix_values": prefix,
        })
    return {
        "exact_common_values_total": int(np.sum(eq)),
        "vectors": rows,
    }


def probe_module_accounting(models) -> dict:
    if len(models) < 2:
        raise ValueError("module-accounting probe requires at least two models")

    modules = []
    solved_widths = []

    for module_index in range(MODULE_COUNT):
        start = MODULE_START + module_index * MODULE_STRIDE_BYTES
        core_bytes = CORE_MATRIX_COUNT * MATRIX_BYTES

        core = []
        for i in range(CORE_MATRIX_COUNT):
            rel = start + i * MATRIX_BYTES
            stats = _consensus_stats(models, rel, MATRIX_BYTES)
            core.append({
                "matrix_index": i,
                "relative_offset": rel,
                "bytes": MATRIX_BYTES,
                "dtype": "float16_le" if fp16_plausible(stats) else "unknown",
                "shape": [HIDDEN, HIDDEN],
                "exact_identity_models": _identity_count(models, rel, MATRIX_BYTES),
            })

        remainder_start = start + core_bytes
        remainder_bytes = MODULE_STRIDE_BYTES - core_bytes

        # Modules 0-2 have six FP16 hidden-width bias vectors.
        # Module 3 has three FP32 hidden-width bias vectors.
        if module_index < 3:
            bias_dtype = "float16_le"
            bias_vector_count = FP16_BIAS_VECTORS
            bias_bytes = bias_vector_count * HIDDEN * 2
        else:
            bias_dtype = "float32_le"
            bias_vector_count = FP32_BIAS_VECTORS
            bias_bytes = bias_vector_count * HIDDEN * 4

        projection_bytes = remainder_bytes - bias_bytes
        denominator = HIDDEN * 2  # FP16 512-by-I projection
        if projection_bytes <= 0 or projection_bytes % denominator:
            raise RuntimeError(
                f"module {module_index}: remainder cannot be represented as 512xI FP16 + bias packet"
            )
        input_width = projection_bytes // denominator
        solved_widths.append(input_width)

        projection_stats = _consensus_stats(models, remainder_start, projection_bytes)
        bias_stats = _consensus_stats(
            models, remainder_start + projection_bytes, bias_bytes
        )
        projection_shared = _identity_count(models, remainder_start, projection_bytes)
        bias_shared = _identity_count(models, remainder_start + projection_bytes, bias_bytes)

        if bias_dtype == "float16_le":
            bias_mask = _common_mask(
                models,
                remainder_start + projection_bytes,
                "<u2",
                bias_vector_count,
            )
            bias_dtype_ok = fp16_plausible(bias_stats)
        else:
            bias_mask = _common_mask(
                models,
                remainder_start + projection_bytes,
                "<u4",
                bias_vector_count,
            )
            bias_dtype_ok = fp32_candidate(bias_stats)

        modules.append({
            "module_index": module_index,
            "relative_offset": start,
            "module_bytes": MODULE_STRIDE_BYTES,
            "core_matrix_count": CORE_MATRIX_COUNT,
            "core_matrix_bytes_total": core_bytes,
            "core_matrices": core,
            "remainder_bytes": remainder_bytes,
            "bias_packet": {
                "dtype": bias_dtype,
                "vector_width": HIDDEN,
                "vector_count": bias_vector_count,
                "bytes": bias_bytes,
                "dtype_plausible": bool(bias_dtype_ok),
                "exact_identity_models": bias_shared,
                "cross_instrument_common_mask": bias_mask,
            },
            "projection_candidate": {
                "dtype": "float16_le",
                "bytes": projection_bytes,
                "element_count": projection_bytes // 2,
                "shape_orientation_candidates": [
                    [HIDDEN, input_width],
                    [input_width, HIDDEN],
                ],
                "solved_other_width": input_width,
                "dtype_plausible": bool(fp16_plausible(projection_stats)),
                "exact_identity_models": projection_shared,
            },
            "byte_equation": {
                "expression": (
                    f"{CORE_MATRIX_COUNT}*(512*512*2) + "
                    f"(512*{input_width}*2) + {bias_bytes}"
                ),
                "evaluated_bytes": (
                    core_bytes + projection_bytes + bias_bytes
                ),
                "matches_module_stride": (
                    core_bytes + projection_bytes + bias_bytes
                    == MODULE_STRIDE_BYTES
                ),
            },
        })

    return {
        "schema": "sonicraft-dnni-module-byte-accounting-v1",
        "truth_boundary": (
            "Exact serialization arithmetic plus dtype/cross-instrument sharing evidence. "
            "The solved 506-wide projection is a strong layout candidate, but its graph "
            "direction and musical semantics remain unknown."
        ),
        "model_count": len(models),
        "hidden_width": HIDDEN,
        "module_count": MODULE_COUNT,
        "module_stride_bytes": MODULE_STRIDE_BYTES,
        "solved_projection_widths": solved_widths,
        "all_modules_solve_same_projection_width": len(set(solved_widths)) == 1,
        "solved_projection_width": solved_widths[0] if len(set(solved_widths)) == 1 else None,
        "modules": modules,
        "important_interpretation": (
            "Cross-instrument equality can extend into the bias packet; therefore an exact "
            "common-prefix boundary is not itself a tensor boundary. Byte accounting is the "
            "stronger constraint for the 506-wide projection candidate."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default="models/dnni")
    ap.add_argument("--registry", default="training/configs/dnni_source_labels.json")
    ap.add_argument("--out")
    args = ap.parse_args()

    registry = load_registry(args.registry)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(args.model_dir, recursive=True)
    result = probe_module_accounting(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
