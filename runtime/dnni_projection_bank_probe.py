#!/usr/bin/env python3
from __future__ import annotations

"""Verify the observed 512-connected projection-bank sandwich fragment.

This is an evidence probe, not an executable decoder. It checks numeric encoding,
byte boundaries, repeated stride and cross-model sharing. Op direction and semantic
roles remain unknown.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry
from dnni_dtype_map_probe import (
    numeric_stats,
    fp16_plausible,
    fp32_candidate,
    median_stats,
)

LATENT_WIDTH = 512
BANK_BLOCK_BYTES = 262_144
BANK_BLOCK_COUNT = 4
BANK_BYTES = BANK_BLOCK_BYTES * BANK_BLOCK_COUNT
BANK_STARTS = (39_256_064, 54_984_704)

FAMILY_START = 40_304_640
FAMILY_MODULE_COUNT = 4
FAMILY_MODULE_STRIDE = 3_670_016
FAMILY_MATRIX_BYTES = 524_288
FAMILY_MATRIX_COUNT = 7
FAMILY_BYTES = FAMILY_MODULE_COUNT * FAMILY_MODULE_STRIDE
FAMILY_LAST_SHARED_BYTES = 506 * 1024
FAMILY_LAST_VARIABLE_BYTES = 6 * 1024


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
    ref = hashlib.sha256(_read(models[0], rel, n)).digest()
    return sum(
        1
        for m in models
        if hashlib.sha256(_read(m, rel, n)).digest() == ref
    )


def probe_projection_banks(models) -> dict:
    if len(models) < 2:
        raise ValueError("projection-bank probe requires at least two models")

    required = BANK_STARTS[-1] + BANK_BYTES
    for model in models:
        if model.section("weights").size < required:
            raise ValueError(f"{model.path}: weights too small for observed projection banks")

    banks = []
    expected_pattern = ("float32_le", "float16_le", "float16_le", "float16_le")
    for bank_index, bank_start in enumerate(BANK_STARTS):
        blocks = []
        observed_pattern = []
        for block_index in range(BANK_BLOCK_COUNT):
            rel = bank_start + block_index * BANK_BLOCK_BYTES
            stats = _consensus_stats(models, rel, BANK_BLOCK_BYTES)
            if fp32_candidate(stats):
                dtype = "float32_le"
                elements = BANK_BLOCK_BYTES // 4
            elif fp16_plausible(stats):
                dtype = "float16_le"
                elements = BANK_BLOCK_BYTES // 2
            else:
                dtype = "mixed_or_unknown"
                elements = None
            observed_pattern.append(dtype)

            other_width = None
            orientations = []
            if elements and elements % LATENT_WIDTH == 0:
                other_width = elements // LATENT_WIDTH
                orientations = [
                    [LATENT_WIDTH, other_width],
                    [other_width, LATENT_WIDTH],
                ]

            blocks.append({
                "index": block_index,
                "relative_offset": rel,
                "bytes": BANK_BLOCK_BYTES,
                "dtype": dtype,
                "element_count": elements,
                "latent_width": LATENT_WIDTH if other_width else None,
                "other_width": other_width,
                "orientation_candidates": orientations,
                "exact_identity_models": _exact_identity_count(
                    models, rel, BANK_BLOCK_BYTES
                ),
            })

        banks.append({
            "index": bank_index,
            "relative_offset": bank_start,
            "bytes": BANK_BYTES,
            "observed_dtype_pattern": observed_pattern,
            "matches_expected_pattern": tuple(observed_pattern) == expected_pattern,
            "blocks": blocks,
        })

    if BANK_STARTS[0] + BANK_BYTES != FAMILY_START:
        raise RuntimeError("left projection bank does not end at module-family start")
    if FAMILY_START + FAMILY_BYTES != BANK_STARTS[1]:
        raise RuntimeError("module family does not end at right projection bank start")

    modules = []
    for module_index in range(FAMILY_MODULE_COUNT):
        module_start = FAMILY_START + module_index * FAMILY_MODULE_STRIDE
        matrices = []
        for matrix_index in range(FAMILY_MATRIX_COUNT):
            rel = module_start + matrix_index * FAMILY_MATRIX_BYTES
            if matrix_index < FAMILY_MATRIX_COUNT - 1:
                stats = _consensus_stats(models, rel, FAMILY_MATRIX_BYTES)
                dtype = "float16_le" if fp16_plausible(stats) else "unknown"
                shape_candidate = [LATENT_WIDTH, LATENT_WIDTH]
                shape_confidence = (
                    "structurally-linked"
                    if FAMILY_MATRIX_BYTES // 2 == LATENT_WIDTH * LATENT_WIDTH
                    else "none"
                )
            else:
                prefix_stats = _consensus_stats(models, rel, FAMILY_LAST_SHARED_BYTES)
                suffix_stats = _consensus_stats(
                    models, rel + FAMILY_LAST_SHARED_BYTES, FAMILY_LAST_VARIABLE_BYTES
                )
                suffix_dtype = (
                    "float32_le" if fp32_candidate(suffix_stats)
                    else ("float16_le" if fp16_plausible(suffix_stats) else "mixed_or_unknown")
                )
                dtype = "split"
                shape_candidate = None
                shape_confidence = "split-boundary-verified"

            matrices.append({
                "index": matrix_index,
                "relative_offset": rel,
                "bytes": FAMILY_MATRIX_BYTES,
                "dtype": dtype,
                "fp16_elements": (
                    FAMILY_MATRIX_BYTES // 2
                    if matrix_index < FAMILY_MATRIX_COUNT - 1 else None
                ),
                "shape_candidate": shape_candidate,
                "shape_confidence": shape_confidence,
                "exact_identity_models": _exact_identity_count(
                    models, rel, FAMILY_MATRIX_BYTES
                ),
            })
        last_rel = module_start + (FAMILY_MATRIX_COUNT - 1) * FAMILY_MATRIX_BYTES
        last_shared_models = _exact_identity_count(
            models, last_rel, FAMILY_LAST_SHARED_BYTES
        )
        suffix_stats = _consensus_stats(
            models,
            last_rel + FAMILY_LAST_SHARED_BYTES,
            FAMILY_LAST_VARIABLE_BYTES,
        )
        suffix_dtype = (
            "float32_le" if fp32_candidate(suffix_stats)
            else ("float16_le" if fp16_plausible(suffix_stats) else "mixed_or_unknown")
        )
        last_variable_models = _exact_identity_count(
            models,
            last_rel + FAMILY_LAST_SHARED_BYTES,
            FAMILY_LAST_VARIABLE_BYTES,
        )
        modules.append({
            "index": module_index,
            "relative_offset": module_start,
            "bytes": FAMILY_MODULE_STRIDE,
            "matrices": matrices,
            "last_matrix_split": {
                "shared_prefix_bytes": FAMILY_LAST_SHARED_BYTES,
                "variable_tail_bytes": FAMILY_LAST_VARIABLE_BYTES,
                "shared_prefix_exact_identity_models": last_shared_models,
                "variable_tail_exact_identity_models": last_variable_models,
                "shared_prefix": {
                    "bytes": FAMILY_LAST_SHARED_BYTES,
                    "dtype": "float16_le",
                    "fp16_values": FAMILY_LAST_SHARED_BYTES // 2,
                    "row_major_512_candidate_rows": 506,
                },
                "instrument_specific_suffix": {
                    "bytes": FAMILY_LAST_VARIABLE_BYTES,
                    "dtype": suffix_dtype,
                    "value_count": (
                        FAMILY_LAST_VARIABLE_BYTES // 4
                        if suffix_dtype == "float32_le"
                        else FAMILY_LAST_VARIABLE_BYTES // 2
                    ),
                    "512_wide_vector_count": (
                        (FAMILY_LAST_VARIABLE_BYTES // 4) // LATENT_WIDTH
                        if suffix_dtype == "float32_le"
                        else (FAMILY_LAST_VARIABLE_BYTES // 2) // LATENT_WIDTH
                    ),
                },
            },
        })

    all_bank_patterns_match = all(
        b["matches_expected_pattern"] for b in banks
    )
    all_regular_matrices_fp16 = all(
        m["dtype"] == "float16_le"
        for module in modules
        for m in module["matrices"][:-1]
    )
    split_suffix_pattern = [
        module["last_matrix_split"]["instrument_specific_suffix"]["dtype"]
        for module in modules
    ]
    split_pattern_verified = (
        split_suffix_pattern[:3] == ["float16_le", "float16_le", "float16_le"]
        and split_suffix_pattern[3:] == ["float32_le"]
        and all(
            module["last_matrix_split"]["shared_prefix_exact_identity_models"] == len(models)
            and module["last_matrix_split"]["variable_tail_exact_identity_models"] == 1
            for module in modules
        )
    )

    return {
        "schema": "sonicraft-dnni-projection-bank-fragment-v1",
        "truth_boundary": (
            "Verified byte/dtype/stride relationships plus dimension-compatible shape "
            "candidates. Graph direction, op type, activation, bias, state semantics and "
            "decoder/conditioning roles remain unknown."
        ),
        "model_count": len(models),
        "latent_width": LATENT_WIDTH,
        "banks": banks,
        "middle_family": {
            "relative_offset": FAMILY_START,
            "bytes": FAMILY_BYTES,
            "module_count": FAMILY_MODULE_COUNT,
            "module_stride_bytes": FAMILY_MODULE_STRIDE,
            "matrix_bytes": FAMILY_MATRIX_BYTES,
            "matrices_per_module": FAMILY_MATRIX_COUNT,
            "all_regular_matrices_fp16_plausible": all_regular_matrices_fp16,
            "last_matrix_suffix_dtype_pattern": split_suffix_pattern,
            "last_matrix_split_verified": split_pattern_verified,
            "modules": modules,
        },
        "sandwich_verified": (
            all_bank_patterns_match and all_regular_matrices_fp16 and split_pattern_verified
        ),
        "candidate_fragment": {
            "left_bank_dimensions": [128, 256, 256, 256],
            "middle_latent_width": LATENT_WIDTH,
            "middle_module_count": FAMILY_MODULE_COUNT,
            "right_bank_dimensions": [128, 256, 256, 256],
            "direction": "unknown",
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
    result = probe_projection_banks(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
