#!/usr/bin/env python3
from __future__ import annotations

"""Conditioning-interface evidence probe for the observed DNNI recurrent-family boundary.

This probe deliberately falsifies attractive-but-unsupported tensor interpretations.
It verifies:
- the exact cross-instrument common-prefix boundary of the final 512 KiB family block;
- dtype of the instrument-specific suffix;
- simple vector-packet decompositions of that suffix;
- the immediately adjacent 128/256-compatible projection banks.

It does not assign musical semantics to any feature width.
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
FAMILY_START = 40_304_640
MODULE_STRIDE = 3_670_016
MODULE_COUNT = 4
MATRIX_BYTES = 524_288
FINAL_BLOCK_INDEX = 6

LEFT_BANK_START = 39_256_064
RIGHT_BANK_START = 54_984_704
BANK_BLOCK_BYTES = 262_144
BANK_BLOCK_COUNT = 4
BANK_BYTES = BANK_BLOCK_BYTES * BANK_BLOCK_COUNT

# Previously hypothesized boundary. Kept only as a falsification target.
OLD_506_BOUNDARY_BYTES = 506 * LATENT_WIDTH * 2


def _read(model, rel: int, n: int) -> bytes:
    weights = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(weights.offset + rel)
        data = f.read(n)
    if len(data) != n:
        raise RuntimeError(f"{model.path}: short read at {rel}")
    return data


def _exact_common_prefix_length(chunks: list[bytes]) -> int:
    if not chunks:
        return 0
    n = min(len(x) for x in chunks)
    first = chunks[0]
    for i in range(n):
        b = first[i]
        if any(x[i] != b for x in chunks[1:]):
            return i
    return n


def _consensus_stats(models, rel: int, n: int):
    return median_stats([numeric_stats(_read(m, rel, n)) for m in models])


def _classify_dtype(stats) -> str:
    if fp32_candidate(stats):
        return "float32_le"
    if fp16_plausible(stats):
        return "float16_le"
    return "mixed_or_unknown"


def _packet_decomposition(nbytes: int, dtype: str) -> dict:
    if dtype == "float16_le":
        values = nbytes // 2
        scalar_prefix = values % 512
        vector_width = 512
    elif dtype == "float32_le":
        values = nbytes // 4
        # 256 is independently observed in the adjacent projection-bank family.
        scalar_prefix = values % 256
        vector_width = 256
    else:
        return {
            "value_count": None,
            "scalar_prefix_candidate": None,
            "vector_width_candidate": None,
            "vector_count_candidate": None,
        }

    return {
        "value_count": values,
        "scalar_prefix_candidate": scalar_prefix,
        "vector_width_candidate": vector_width,
        "vector_count_candidate": (values - scalar_prefix) // vector_width,
    }


def _bank_block(models, bank_start: int, block_index: int) -> dict:
    rel = bank_start + block_index * BANK_BLOCK_BYTES
    stats = _consensus_stats(models, rel, BANK_BLOCK_BYTES)
    dtype = _classify_dtype(stats)

    if dtype == "float32_le":
        elements = BANK_BLOCK_BYTES // 4
    elif dtype == "float16_le":
        elements = BANK_BLOCK_BYTES // 2
    else:
        elements = None

    if elements and elements % LATENT_WIDTH == 0:
        other = elements // LATENT_WIDTH
        orientations = [[LATENT_WIDTH, other], [other, LATENT_WIDTH]]
    else:
        other = None
        orientations = []

    return {
        "index": block_index,
        "relative_offset": rel,
        "bytes": BANK_BLOCK_BYTES,
        "dtype": dtype,
        "element_count": elements,
        "latent_width": LATENT_WIDTH if other else None,
        "other_width": other,
        "orientation_candidates": orientations,
    }


def probe_conditioning_interface(models) -> dict:
    if len(models) < 2:
        raise ValueError("conditioning-interface probe requires at least two models")

    modules = []
    prefix_lengths = []
    suffix_dtypes = []

    for module_index in range(MODULE_COUNT):
        block_rel = (
            FAMILY_START
            + module_index * MODULE_STRIDE
            + FINAL_BLOCK_INDEX * MATRIX_BYTES
        )
        chunks = [_read(m, block_rel, MATRIX_BYTES) for m in models]
        prefix = _exact_common_prefix_length(chunks)
        suffix_bytes = MATRIX_BYTES - prefix
        suffix_stats = median_stats([
            numeric_stats(x[prefix:]) for x in chunks
        ])
        suffix_dtype = _classify_dtype(suffix_stats)

        prefix_lengths.append(prefix)
        suffix_dtypes.append(suffix_dtype)

        modules.append({
            "module_index": module_index,
            "final_block_relative_offset": block_rel,
            "final_block_bytes": MATRIX_BYTES,
            "exact_common_prefix_bytes": prefix,
            "instrument_specific_suffix_bytes": suffix_bytes,
            "suffix_dtype": suffix_dtype,
            "suffix_packet_candidate": _packet_decomposition(
                suffix_bytes, suffix_dtype
            ),
            "old_506_boundary": {
                "bytes": OLD_506_BOUNDARY_BYTES,
                "matches_exact_common_boundary": prefix == OLD_506_BOUNDARY_BYTES,
                "additional_common_bytes_after_old_boundary": max(
                    0, prefix - OLD_506_BOUNDARY_BYTES
                ),
            },
        })

    left = [
        _bank_block(models, LEFT_BANK_START, i)
        for i in range(BANK_BLOCK_COUNT)
    ]
    right = [
        _bank_block(models, RIGHT_BANK_START, i)
        for i in range(BANK_BLOCK_COUNT)
    ]

    if LEFT_BANK_START + BANK_BYTES != FAMILY_START:
        raise RuntimeError("left bank does not terminate at family start")
    if FAMILY_START + MODULE_COUNT * MODULE_STRIDE != RIGHT_BANK_START:
        raise RuntimeError("family does not terminate at right bank start")

    bank_pattern = [
        {"dtype": x["dtype"], "other_width": x["other_width"]}
        for x in left
    ]
    right_pattern = [
        {"dtype": x["dtype"], "other_width": x["other_width"]}
        for x in right
    ]

    return {
        "schema": "sonicraft-dnni-conditioning-interface-v1",
        "truth_boundary": (
            "Verified byte equality/dtype/dimension-compatibility only. Musical feature "
            "semantics, graph direction, tensor orientation and proprietary runtime behavior "
            "remain unknown."
        ),
        "model_count": len(models),
        "latent_width": LATENT_WIDTH,
        "terminal_block_evidence": {
            "module_count": MODULE_COUNT,
            "exact_common_prefix_bytes_by_module": prefix_lengths,
            "suffix_dtype_pattern": suffix_dtypes,
            "modules": modules,
            "old_506_conditioning_width_supported": all(
                x == OLD_506_BOUNDARY_BYTES for x in prefix_lengths
            ),
            "conclusion": (
                "The previous 506-wide conditioning interpretation is not supported by "
                "the exact cross-model boundary and must not be treated as a verified input width."
            ),
        },
        "adjacent_projection_interface": {
            "left_bank_start": LEFT_BANK_START,
            "right_bank_start": RIGHT_BANK_START,
            "bank_bytes": BANK_BYTES,
            "left_bank": left,
            "right_bank": right,
            "left_pattern": bank_pattern,
            "right_pattern": right_pattern,
            "patterns_match": bank_pattern == right_pattern,
            "dimension_candidates": [
                x["other_width"] for x in left if x["other_width"] is not None
            ],
            "boundary_equalities": [
                "left_bank_end == family_start",
                "family_end == right_bank_start",
            ],
        },
        "next_evidence_gate": (
            "Determine whether the adjacent 128/256-compatible bank is input-side, output-side "
            "or bidirectional by finding an independently verifiable producer/consumer tensor."
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
    result = probe_conditioning_interface(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
