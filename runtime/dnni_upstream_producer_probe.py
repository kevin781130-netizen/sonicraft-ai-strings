#!/usr/bin/env python3
from __future__ import annotations

"""Verify the instrument-specific upstream family immediately before the 128/256 bank.

Observed layout:
- seven regular modules of 2,633,728 bytes;
- one shorter final module ending exactly at the left projection-bank boundary.

This probe establishes byte accounting, dtype plausibility, cross-instrument sharing
scope and adjacency. It does not assign proprietary op names or musical semantics.
"""

import argparse
import hashlib
import json
from pathlib import Path

from dnni_model_shell import DnniModelCatalog, load_registry
from dnni_dtype_map_probe import numeric_stats, fp16_plausible, fp32_candidate, median_stats

HIDDEN = 512
FAMILY_START = 18_251_776
REGULAR_MODULE_COUNT = 7
REGULAR_MODULE_BYTES = 2_633_728
FINAL_MODULE_INDEX = 7
FINAL_MODULE_START = FAMILY_START + REGULAR_MODULE_COUNT * REGULAR_MODULE_BYTES
LEFT_BANK_START = 39_256_064

MATRIX_BYTES = HIDDEN * HIDDEN * 2
REGULAR_MATRIX_COUNT = 5
REGULAR_VECTOR_COUNT = 12
REGULAR_VECTOR_PACKET_BYTES = REGULAR_VECTOR_COUNT * HIDDEN * 2

FINAL_MATRIX_COUNT = 4
FINAL_PROJECTION_OTHER_WIDTH = 452
FINAL_PROJECTION_BYTES = HIDDEN * FINAL_PROJECTION_OTHER_WIDTH * 2
FINAL_FP32_VECTOR_COUNT = 4
FINAL_FP32_PACKET_BYTES = FINAL_FP32_VECTOR_COUNT * HIDDEN * 4
FINAL_MODULE_BYTES = (
    FINAL_MATRIX_COUNT * MATRIX_BYTES
    + FINAL_PROJECTION_BYTES
    + FINAL_FP32_PACKET_BYTES
)


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


def layout_accounting() -> dict:
    regular_expected = (
        REGULAR_MATRIX_COUNT * MATRIX_BYTES + REGULAR_VECTOR_PACKET_BYTES
    )
    final_expected = (
        FINAL_MATRIX_COUNT * MATRIX_BYTES
        + FINAL_PROJECTION_BYTES
        + FINAL_FP32_PACKET_BYTES
    )
    return {
        "regular_module_bytes": REGULAR_MODULE_BYTES,
        "regular_accounted_bytes": regular_expected,
        "regular_matches": regular_expected == REGULAR_MODULE_BYTES,
        "final_module_bytes": FINAL_MODULE_BYTES,
        "final_accounted_bytes": final_expected,
        "final_matches": final_expected == FINAL_MODULE_BYTES,
        "final_module_start": FINAL_MODULE_START,
        "final_module_end": FINAL_MODULE_START + FINAL_MODULE_BYTES,
        "left_bank_start": LEFT_BANK_START,
        "final_ends_at_left_bank": (
            FINAL_MODULE_START + FINAL_MODULE_BYTES == LEFT_BANK_START
        ),
    }


def probe_upstream_family(models) -> dict:
    if len(models) < 2:
        raise ValueError("upstream-producer probe requires at least two models")

    accounting = layout_accounting()
    if not (
        accounting["regular_matches"]
        and accounting["final_matches"]
        and accounting["final_ends_at_left_bank"]
    ):
        raise RuntimeError("configured upstream-family accounting is inconsistent")

    regular = []
    for module_index in range(REGULAR_MODULE_COUNT):
        start = FAMILY_START + module_index * REGULAR_MODULE_BYTES
        matrices = []
        for i in range(REGULAR_MATRIX_COUNT):
            rel = start + i * MATRIX_BYTES
            stats = _consensus_stats(models, rel, MATRIX_BYTES)
            matrices.append({
                "index": i,
                "relative_offset": rel,
                "bytes": MATRIX_BYTES,
                "dtype": "float16_le" if fp16_plausible(stats) else "unknown",
                "shape": [HIDDEN, HIDDEN],
                "exact_identity_models": _identity_count(models, rel, MATRIX_BYTES),
            })

        packet_rel = start + REGULAR_MATRIX_COUNT * MATRIX_BYTES
        packet_stats = _consensus_stats(
            models, packet_rel, REGULAR_VECTOR_PACKET_BYTES
        )
        regular.append({
            "module_index": module_index,
            "relative_offset": start,
            "bytes": REGULAR_MODULE_BYTES,
            "matrices": matrices,
            "vector_packet": {
                "relative_offset": packet_rel,
                "bytes": REGULAR_VECTOR_PACKET_BYTES,
                "dtype": "float16_le" if fp16_plausible(packet_stats) else "unknown",
                "vector_width": HIDDEN,
                "vector_count": REGULAR_VECTOR_COUNT,
                "exact_identity_models": _identity_count(
                    models, packet_rel, REGULAR_VECTOR_PACKET_BYTES
                ),
            },
        })

    final_start = FINAL_MODULE_START
    final_matrices = []
    for i in range(FINAL_MATRIX_COUNT):
        rel = final_start + i * MATRIX_BYTES
        stats = _consensus_stats(models, rel, MATRIX_BYTES)
        final_matrices.append({
            "index": i,
            "relative_offset": rel,
            "bytes": MATRIX_BYTES,
            "dtype": "float16_le" if fp16_plausible(stats) else "unknown",
            "shape": [HIDDEN, HIDDEN],
            "exact_identity_models": _identity_count(models, rel, MATRIX_BYTES),
        })

    projection_rel = final_start + FINAL_MATRIX_COUNT * MATRIX_BYTES
    projection_stats = _consensus_stats(
        models, projection_rel, FINAL_PROJECTION_BYTES
    )
    packet_rel = projection_rel + FINAL_PROJECTION_BYTES
    packet_stats = _consensus_stats(
        models, packet_rel, FINAL_FP32_PACKET_BYTES
    )

    final = {
        "module_index": FINAL_MODULE_INDEX,
        "relative_offset": final_start,
        "bytes": FINAL_MODULE_BYTES,
        "matrices": final_matrices,
        "projection_candidate": {
            "relative_offset": projection_rel,
            "bytes": FINAL_PROJECTION_BYTES,
            "dtype": "float16_le" if fp16_plausible(projection_stats) else "unknown",
            "element_count": FINAL_PROJECTION_BYTES // 2,
            "orientation_candidates": [
                [HIDDEN, FINAL_PROJECTION_OTHER_WIDTH],
                [FINAL_PROJECTION_OTHER_WIDTH, HIDDEN],
            ],
            "other_width": FINAL_PROJECTION_OTHER_WIDTH,
            "exact_identity_models": _identity_count(
                models, projection_rel, FINAL_PROJECTION_BYTES
            ),
        },
        "fp32_vector_packet": {
            "relative_offset": packet_rel,
            "bytes": FINAL_FP32_PACKET_BYTES,
            "dtype": "float32_le" if fp32_candidate(packet_stats) else "unknown",
            "vector_width": HIDDEN,
            "vector_count": FINAL_FP32_VECTOR_COUNT,
            "exact_identity_models": _identity_count(
                models, packet_rel, FINAL_FP32_PACKET_BYTES
            ),
        },
        "end_offset": final_start + FINAL_MODULE_BYTES,
        "ends_exactly_at_left_bank": (
            final_start + FINAL_MODULE_BYTES == LEFT_BANK_START
        ),
    }

    all_regions_instrument_specific = all(
        x["exact_identity_models"] == 1
        for module in regular
        for x in [
            *module["matrices"],
            module["vector_packet"],
        ]
    ) and all(
        x["exact_identity_models"] == 1
        for x in [
            *final_matrices,
            final["projection_candidate"],
            final["fp32_vector_packet"],
        ]
    )

    return {
        "schema": "sonicraft-dnni-upstream-producer-family-v1",
        "truth_boundary": (
            "Verified byte accounting, dtype plausibility, sharing scope and serialization "
            "adjacency only. Operation semantics, graph direction and musical feature meaning "
            "remain unknown."
        ),
        "model_count": len(models),
        "hidden_width": HIDDEN,
        "accounting": accounting,
        "regular_modules": regular,
        "final_module": final,
        "all_observed_parameter_regions_instrument_specific": (
            all_regions_instrument_specific
        ),
        "producer_boundary_candidate": {
            "upstream_family_start": FAMILY_START,
            "regular_module_count": REGULAR_MODULE_COUNT,
            "final_module_start": FINAL_MODULE_START,
            "final_module_end": LEFT_BANK_START,
            "next_serialized_region": "128/256 projection bank",
            "confidence": "strong serialization boundary",
            "orientation_hint": (
                "The final 452-by-512/512-by-452 FP16 projection is followed by four "
                "512-wide FP32 vectors; this favors a 512-wide output-side interpretation "
                "but does not prove matrix orientation."
            ),
        },
        "next_evidence_gate": (
            "Trace the input to the special final upstream module and determine whether "
            "the 452-wide projection is input-side, output-side or an auxiliary branch."
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
    result = probe_upstream_family(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
