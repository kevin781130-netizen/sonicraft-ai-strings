#!/usr/bin/env python3
from __future__ import annotations

"""Check whether an observed DNNI module family is parameter-geometry compatible
with a 512-wide gated recurrent unit family.

This is a structural compatibility test only. It does not identify GRU semantics,
gate order, reset mode, activation, graph direction, or proprietary packing.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry
from dnni_dtype_map_probe import numeric_stats, fp16_plausible, fp32_candidate, median_stats

HIDDEN = 512
FAMILY_START = 40_304_640
MODULE_STRIDE = 3_670_016
MODULE_COUNT = 4
MATRIX_BYTES = 524_288
CORE_MATRIX_COUNT = 6
TAIL_BLOCK_BYTES = 524_288
SHARED_SLAB_BYTES = 506 * 1024
SUFFIX_BYTES = 6 * 1024


def _read(model, rel: int, n: int) -> bytes:
    weights = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(weights.offset + rel)
        data = f.read(n)
    if len(data) != n:
        raise RuntimeError(f"{model.path}: short read at {rel}")
    return data


def _consensus_stats(models, rel: int, n: int):
    return median_stats([numeric_stats(_read(m, rel, n)) for m in models])


def _exact_identity_count(models, rel: int, n: int) -> int:
    reference = hashlib.sha256(_read(models[0], rel, n)).digest()
    return sum(
        hashlib.sha256(_read(m, rel, n)).digest() == reference
        for m in models
    )


def probe_recurrent_signature(models) -> dict:
    if len(models) < 2:
        raise ValueError("recurrent-signature probe requires at least two models")

    expected_matrix_bytes = HIDDEN * HIDDEN * 2
    if MATRIX_BYTES != expected_matrix_bytes:
        raise RuntimeError("configured matrix bytes do not match 512x512 FP16")

    modules = []
    for module_index in range(MODULE_COUNT):
        module_start = FAMILY_START + module_index * MODULE_STRIDE

        core_matrices = []
        for matrix_index in range(CORE_MATRIX_COUNT):
            rel = module_start + matrix_index * MATRIX_BYTES
            stats = _consensus_stats(models, rel, MATRIX_BYTES)
            core_matrices.append({
                "index": matrix_index,
                "relative_offset": rel,
                "bytes": MATRIX_BYTES,
                "dtype": "float16_le" if fp16_plausible(stats) else "unknown",
                "shape": [HIDDEN, HIDDEN],
                "exact_identity_models": _exact_identity_count(
                    models, rel, MATRIX_BYTES
                ),
            })

        tail_rel = module_start + CORE_MATRIX_COUNT * MATRIX_BYTES
        slab_stats = _consensus_stats(models, tail_rel, SHARED_SLAB_BYTES)
        suffix_rel = tail_rel + SHARED_SLAB_BYTES
        suffix_stats = _consensus_stats(models, suffix_rel, SUFFIX_BYTES)

        if fp32_candidate(suffix_stats):
            suffix_dtype = "float32_le"
            suffix_values = SUFFIX_BYTES // 4
        elif fp16_plausible(suffix_stats):
            suffix_dtype = "float16_le"
            suffix_values = SUFFIX_BYTES // 2
        else:
            suffix_dtype = "mixed_or_unknown"
            suffix_values = None

        suffix_vectors = (
            suffix_values // HIDDEN
            if suffix_values is not None and suffix_values % HIDDEN == 0
            else None
        )

        # Standard GRU-family parameter geometry with input_size == hidden_size:
        # 3 input-hidden HxH matrices + 3 hidden-hidden HxH matrices.
        six_matrix_geometry = (
            len(core_matrices) == 6
            and all(x["dtype"] == "float16_le" for x in core_matrices)
            and all(x["shape"] == [HIDDEN, HIDDEN] for x in core_matrices)
        )
        gru_bias_count_compatible = suffix_vectors in (3, 6)

        modules.append({
            "index": module_index,
            "relative_offset": module_start,
            "bytes": MODULE_STRIDE,
            "core_matrices": core_matrices,
            "shared_slab": {
                "relative_offset": tail_rel,
                "bytes": SHARED_SLAB_BYTES,
                "dtype": "float16_le" if fp16_plausible(slab_stats) else "unknown",
                "fp16_values": SHARED_SLAB_BYTES // 2,
                "orientation_candidates": [
                    [506, HIDDEN],
                    [HIDDEN, 506],
                ],
                "exact_identity_models": _exact_identity_count(
                    models, tail_rel, SHARED_SLAB_BYTES
                ),
            },
            "instrument_specific_suffix": {
                "relative_offset": suffix_rel,
                "bytes": SUFFIX_BYTES,
                "dtype": suffix_dtype,
                "value_count": suffix_values,
                "vector_width": HIDDEN if suffix_vectors else None,
                "vector_count": suffix_vectors,
                "exact_identity_models": _exact_identity_count(
                    models, suffix_rel, SUFFIX_BYTES
                ),
            },
            "gru_compatible_geometry": {
                "six_hidden_by_hidden_matrices": six_matrix_geometry,
                "three_plus_three_matrix_partition_possible": six_matrix_geometry,
                "bias_vector_count_compatible": gru_bias_count_compatible,
                "compatible": six_matrix_geometry and gru_bias_count_compatible,
            },
        })

    return {
        "schema": "sonicraft-dnni-recurrent-signature-v1",
        "truth_boundary": (
            "Parameter-count/shape compatibility only. This does not prove a GRU, "
            "gate order, bias semantics, activation functions, reset mode, recurrence "
            "equation, or graph direction."
        ),
        "model_count": len(models),
        "hidden_width_candidate": HIDDEN,
        "module_count": MODULE_COUNT,
        "standard_gru_geometry_reference": {
            "input_size_candidate": HIDDEN,
            "hidden_size_candidate": HIDDEN,
            "input_hidden_matrix_count": 3,
            "hidden_hidden_matrix_count": 3,
            "total_hidden_by_hidden_matrix_count": 6,
            "bias_vector_count_common_variants": [3, 6],
        },
        "modules": modules,
        "all_modules_gru_geometry_compatible": all(
            m["gru_compatible_geometry"]["compatible"] for m in modules
        ),
        "important_extra_parameter": {
            "per_module_shared_slab_bytes": SHARED_SLAB_BYTES,
            "fp16_values": SHARED_SLAB_BYTES // 2,
            "orientation_candidates": [[506, HIDDEN], [HIDDEN, 506]],
            "note": (
                "This extra cross-instrument-shared slab is not part of a minimal "
                "standard GRU parameter set and must be explained separately."
            ),
        },
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
    result = probe_recurrent_signature(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
