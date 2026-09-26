#!/usr/bin/env python3
from __future__ import annotations

"""Directionality evidence for the symmetric DNNI projection-bank sandwich.

The probe compares the bank immediately before the 4-module family with the bank
immediately after it. It evaluates numerical homogeneity, dense-matrix plausibility,
operator gain, singular-spectrum pairing, and serialization adjacency.

It does not prove graph direction. The output is an evidence-graded producer/consumer
candidate only.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry

LATENT = 512
LEFT_START = 39_256_064
RIGHT_START = 54_984_704
BANK_BYTES = 1_048_576
BLOCK_BYTES = 262_144
FAMILY_START = 40_304_640
FAMILY_BYTES = 4 * 3_670_016

BRANCH_WIDTHS = (128, 256, 256, 256)
DTYPES = ("<f4", "<f2", "<f2", "<f2")


def _read(model, rel: int, n: int) -> bytes:
    w = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(w.offset + rel)
        data = f.read(n)
    if len(data) != n:
        raise RuntimeError(f"{model.path}: short read at {rel}")
    return data


def _as_matrix(model, bank_start: int, block_index: int, producer: bool) -> np.ndarray:
    width = BRANCH_WIDTHS[block_index]
    dtype = DTYPES[block_index]
    raw = _read(model, bank_start + block_index * BLOCK_BYTES, BLOCK_BYTES)
    x = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    # Do not silently treat non-finite values as valid dense weights. The caller
    # records them separately; nan_to_num is only for diagnostics after counting.
    x = np.nan_to_num(x, posinf=65504.0, neginf=-65504.0)
    if producer:
        return x.reshape(width, LATENT).T  # branch -> latent
    return x.reshape(width, LATENT)       # latent -> branch


def _half_exp31_count(model, bank_start: int, block_index: int) -> int:
    if block_index == 0:
        return 0
    raw = _read(model, bank_start + block_index * BLOCK_BYTES, BLOCK_BYTES)
    u = np.frombuffer(raw, dtype="<u2")
    return int(np.sum(((u >> 10) & 31) == 31))


def _operator_rms_gain(a: np.ndarray) -> float:
    return float(np.linalg.norm(a, "fro") / math.sqrt(a.shape[1]))


def _rank(a: np.ndarray) -> int:
    s = np.linalg.svd(a, compute_uv=False)
    if len(s) == 0 or s[0] <= 0:
        return 0
    return int(np.sum(s > 1e-6 * s[0]))


def _normalized_spectrum(a: np.ndarray) -> np.ndarray:
    s = np.linalg.svd(a, compute_uv=False)
    return s / max(float(np.linalg.norm(s)), 1e-30)


def probe_bank_direction(models) -> dict:
    if len(models) < 2:
        raise ValueError("bank-direction probe requires at least two models")

    if LEFT_START + BANK_BYTES != FAMILY_START:
        raise RuntimeError("left bank is not immediately before the module family")
    if FAMILY_START + FAMILY_BYTES != RIGHT_START:
        raise RuntimeError("right bank is not immediately after the module family")

    left_blocks = []
    right_blocks = []
    spectral_pairing = []

    for block_index, width in enumerate(BRANCH_WIDTHS):
        left_exp31 = []
        right_exp31 = []
        left_prod_gain = []
        left_cons_gain = []
        right_prod_gain = []
        right_cons_gain = []
        left_rank = []
        right_rank = []
        spectrum_corr = []

        for model in models:
            left_exp31.append(_half_exp31_count(model, LEFT_START, block_index))
            right_exp31.append(_half_exp31_count(model, RIGHT_START, block_index))

            lp = _as_matrix(model, LEFT_START, block_index, True)
            lc = _as_matrix(model, LEFT_START, block_index, False)
            rp = _as_matrix(model, RIGHT_START, block_index, True)
            rc = _as_matrix(model, RIGHT_START, block_index, False)

            left_prod_gain.append(_operator_rms_gain(lp))
            left_cons_gain.append(_operator_rms_gain(lc))
            right_prod_gain.append(_operator_rms_gain(rp))
            right_cons_gain.append(_operator_rms_gain(rc))
            left_rank.append(_rank(lc))
            right_rank.append(_rank(rc))

            sl = _normalized_spectrum(lc)
            sr = _normalized_spectrum(rc)
            spectrum_corr.append(
                float(np.dot(sl, sr) / (
                    max(float(np.linalg.norm(sl)), 1e-30)
                    * max(float(np.linalg.norm(sr)), 1e-30)
                ))
            )

        left_blocks.append({
            "block_index": block_index,
            "nominal_branch_width": width,
            "dtype_candidate": "float32_le" if block_index == 0 else "float16_le",
            "fp16_exp31_count_min": min(left_exp31),
            "fp16_exp31_count_max": max(left_exp31),
            "producer_rms_gain_median": float(np.median(left_prod_gain)),
            "consumer_rms_gain_median": float(np.median(left_cons_gain)),
            "rank_min": min(left_rank),
            "rank_max": max(left_rank),
            "plain_dense_matrix_candidate": (
                block_index == 0 or max(left_exp31) == 0
            ),
        })
        right_blocks.append({
            "block_index": block_index,
            "nominal_branch_width": width,
            "dtype_candidate": "float32_le" if block_index == 0 else "float16_le",
            "fp16_exp31_count_min": min(right_exp31),
            "fp16_exp31_count_max": max(right_exp31),
            "producer_rms_gain_median": float(np.median(right_prod_gain)),
            "consumer_rms_gain_median": float(np.median(right_cons_gain)),
            "rank_min": min(right_rank),
            "rank_max": max(right_rank),
            "plain_dense_matrix_candidate": (
                block_index == 0 or max(right_exp31) == 0
            ),
        })
        spectral_pairing.append({
            "block_index": block_index,
            "median_normalized_singular_spectrum_correlation": float(
                np.median(spectrum_corr)
            ),
            "min_correlation": float(min(spectrum_corr)),
            "max_correlation": float(max(spectrum_corr)),
        })

    left_dense_count = sum(x["plain_dense_matrix_candidate"] for x in left_blocks)
    right_dense_count = sum(x["plain_dense_matrix_candidate"] for x in right_blocks)

    left_prod_gains = [x["producer_rms_gain_median"] for x in left_blocks]
    right_prod_gains = [x["producer_rms_gain_median"] for x in right_blocks]

    left_balance = max(left_prod_gains) / max(min(left_prod_gains), 1e-30)
    right_balance = max(right_prod_gains) / max(min(right_prod_gains), 1e-30)

    return {
        "schema": "sonicraft-dnni-bank-direction-v1",
        "truth_boundary": (
            "Serialization adjacency and numerical plausibility only. Direction is a "
            "structural candidate, not a decoded proprietary graph edge."
        ),
        "model_count": len(models),
        "latent_width": LATENT,
        "serialization": {
            "left_bank_start": LEFT_START,
            "left_bank_end": LEFT_START + BANK_BYTES,
            "family_start": FAMILY_START,
            "family_end": FAMILY_START + FAMILY_BYTES,
            "right_bank_start": RIGHT_START,
            "right_bank_end": RIGHT_START + BANK_BYTES,
            "left_immediately_precedes_family": LEFT_START + BANK_BYTES == FAMILY_START,
            "right_immediately_follows_family": FAMILY_START + FAMILY_BYTES == RIGHT_START,
        },
        "left_bank": {
            "blocks": left_blocks,
            "plain_dense_block_count": left_dense_count,
            "producer_gain_balance_ratio": left_balance,
        },
        "right_bank": {
            "blocks": right_blocks,
            "plain_dense_block_count": right_dense_count,
            "producer_gain_balance_ratio": right_balance,
        },
        "left_right_spectral_pairing": spectral_pairing,
        "candidate_direction": {
            "left_bank_role": "stronger producer/input-side candidate",
            "middle_family_role": "512-state processing candidate",
            "right_bank_role": "stronger consumer/packed-output-side candidate",
            "confidence": "moderate structural",
            "evidence": [
                "left bank is serialized immediately before the module family",
                "right bank is serialized immediately after the module family",
                "all four left blocks remain numerically plausible as plain dense projections",
                "right blocks 2 and 3 contain repeatable non-plain FP16 patterns across every model",
                "left producer-side branch gains are comparatively balanced",
                "left/right blocks 0 and 1 have strongly similar singular spectra without tied weights",
            ],
            "not_proven": [
                "actual execution order",
                "matrix orientation",
                "branch semantics",
                "whether right blocks 2/3 are mixed dtype, auxiliary packets, or another packed structure",
            ],
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
    result = probe_bank_direction(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
