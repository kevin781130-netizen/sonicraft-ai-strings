#!/usr/bin/env python3
from __future__ import annotations

"""Evidence-grade operation constraints for the observed DNNI 512-state fragment.

The probe characterizes dense matrix numerics and verifies negative evidence:
- whether the matrices look identity-like, low-rank or near-orthogonal;
- whether known dimensions appear as literal uint32 descriptors in opaque sections;
- whether the 64-row model-specific tail is directly weight-tied to 64-wide FP32
  projection candidates.

It deliberately does not reconstruct permutation maps or assign proprietary op names.
"""

import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry

LATENT = 512
MATRIX_BYTES = 524_288
FAMILY_START = 40_304_640
MODULE_STRIDE = 3_670_016
MODULE_COUNT = 4
MATRIX_COUNT = 7
FINAL_SHARED_BYTES = 506 * 1024
FINAL_SUFFIX_BYTES = 6 * 1024
TARGET_DIMS = (64, 128, 256, 288, 448, 506, 512)

PREFERRED_SAMPLE_ROLES = ("violin", "flute", "french_horn", "tuba")


def _read(model, relative_offset: int, nbytes: int) -> bytes:
    weights = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(weights.offset + relative_offset)
        data = f.read(nbytes)
    if len(data) != nbytes:
        raise RuntimeError(f"{model.path}: short read at {relative_offset}")
    return data


def spectral_signature(a: np.ndarray) -> dict:
    a = np.asarray(a, dtype=np.float32)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("spectral_signature expects a square matrix")
    n = a.shape[0]
    s = np.linalg.svd(np.nan_to_num(a), compute_uv=False)
    total = float(np.sum(s))
    p = s / max(total, 1e-30)
    effective_rank = float(np.exp(-np.sum(p * np.log(p + 1e-30))))
    rank_1e4 = int(np.sum(s > 1e-4 * max(float(s[0]), 1e-30)))

    alpha = float(np.trace(a) / n)
    ident = alpha * np.eye(n, dtype=np.float32)
    identity_distance = float(
        np.linalg.norm(a - ident, "fro") / max(float(np.linalg.norm(a, "fro")), 1e-30)
    )

    gram = a.T @ a
    beta = float(np.trace(gram) / n)
    target = beta * np.eye(n, dtype=np.float32)
    orthogonality_error = float(
        np.linalg.norm(gram - target, "fro")
        / max(float(np.linalg.norm(gram, "fro")), 1e-30)
    )

    return {
        "width": n,
        "effective_rank": effective_rank,
        "rank_threshold_1e-4": rank_1e4,
        "spectral_norm": float(s[0]),
        "smallest_singular": float(s[-1]),
        "identity_distance": identity_distance,
        "orthogonality_error": orthogonality_error,
        "std": float(np.nanstd(a)),
    }


def classify_signature(sig: dict) -> dict:
    width = int(sig["width"])
    return {
        "dense_full_rank_like": int(sig["rank_threshold_1e-4"]) >= int(0.95 * width),
        "low_rank_like": float(sig["effective_rank"]) < 0.25 * width,
        "identity_like": float(sig["identity_distance"]) < 0.20,
        "near_orthogonal": float(sig["orthogonality_error"]) < 0.20,
    }


def _sample_models(models):
    by_role = {
        m.registry_match.instrument_role: m
        for m in models
        if m.registry_match and m.registry_match.instrument_role
    }
    chosen = [by_role[x] for x in PREFERRED_SAMPLE_ROLES if x in by_role]
    if len(chosen) >= 2:
        return chosen
    return models[: min(4, len(models))]


def _family_spectral_summary(models) -> dict:
    sample = _sample_models(models)
    per_matrix = []
    for matrix_index in range(MATRIX_COUNT):
        rows = []
        for model in sample:
            rel = FAMILY_START + matrix_index * MATRIX_BYTES
            raw = _read(model, rel, MATRIX_BYTES)
            a = np.frombuffer(raw, dtype="<f2").astype(np.float32).reshape(LATENT, LATENT)
            rows.append(spectral_signature(a))
        med = {}
        for field in (
            "effective_rank", "rank_threshold_1e-4", "spectral_norm",
            "smallest_singular", "identity_distance", "orthogonality_error", "std"
        ):
            med[field] = float(np.median([x[field] for x in rows]))
        med["width"] = LATENT
        per_matrix.append({
            "matrix_index": matrix_index,
            "sample_count": len(sample),
            "median_signature": med,
            "classification": classify_signature(med),
        })
    return {
        "sample_roles": [
            m.registry_match.instrument_role if m.registry_match else m.path.name
            for m in sample
        ],
        "matrices": per_matrix,
    }


def _pairwise_tied_weight_scan(models) -> dict:
    sample = _sample_models(models)
    max_direct = {"abs_correlation": 0.0}
    max_transpose = {"abs_correlation": 0.0}
    comparisons = 0

    for model in sample:
        for module_index in range(MODULE_COUNT):
            mats = []
            for matrix_index in range(MATRIX_COUNT):
                if module_index == MODULE_COUNT - 1 and matrix_index == MATRIX_COUNT - 1:
                    # Final module's last block is mixed: 506 KiB FP16 shared prefix
                    # plus 6 KiB FP32 instrument-specific suffix. Do not coerce it
                    # into a 512x512 FP16 matrix for tied-weight tests.
                    mats.append(None)
                    continue
                rel = (
                    FAMILY_START
                    + module_index * MODULE_STRIDE
                    + matrix_index * MATRIX_BYTES
                )
                a = np.frombuffer(
                    _read(model, rel, MATRIX_BYTES), dtype="<f2"
                ).astype(np.float32).reshape(LATENT, LATENT)
                mats.append(np.nan_to_num(a))

            for i in range(MATRIX_COUNT):
                if mats[i] is None:
                    continue
                ai = mats[i].ravel()
                ni = max(float(np.linalg.norm(ai)), 1e-30)
                for j in range(i + 1, MATRIX_COUNT):
                    if mats[j] is None:
                        continue
                    bj = mats[j]
                    nj = max(float(np.linalg.norm(bj)), 1e-30)
                    direct = float(np.dot(ai, bj.ravel()) / (ni * nj))
                    transposed = float(np.dot(ai, bj.T.ravel()) / (ni * nj))
                    comparisons += 1
                    if abs(direct) > max_direct["abs_correlation"]:
                        max_direct = {
                            "abs_correlation": abs(direct),
                            "correlation": direct,
                            "instrument_role": (
                                model.registry_match.instrument_role
                                if model.registry_match else model.path.name
                            ),
                            "module_index": module_index,
                            "matrix_pair": [i, j],
                        }
                    if abs(transposed) > max_transpose["abs_correlation"]:
                        max_transpose = {
                            "abs_correlation": abs(transposed),
                            "correlation": transposed,
                            "instrument_role": (
                                model.registry_match.instrument_role
                                if model.registry_match else model.path.name
                            ),
                            "module_index": module_index,
                            "matrix_pair": [i, j],
                        }

    return {
        "sample_roles": [
            m.registry_match.instrument_role if m.registry_match else m.path.name
            for m in sample
        ],
        "comparisons": comparisons,
        "max_direct_normalized_correlation": max_direct,
        "max_transpose_normalized_correlation": max_transpose,
        "tied_or_transpose_pair_detected": (
            max_direct["abs_correlation"] >= 0.90
            or max_transpose["abs_correlation"] >= 0.90
        ),
    }


def _metadata_dimension_scan(models) -> dict:
    section_keys = ("section1", "section3", "section4")
    out = {}
    for section_key in section_keys:
        target_counts = {}
        for value in TARGET_DIMS:
            pattern = struct.pack("<I", value)
            counts = []
            for model in models:
                section = model.section(section_key)
                with model.path.open("rb") as f:
                    f.seek(section.offset)
                    data = f.read(section.size)
                counts.append(data.count(pattern))
            target_counts[str(value)] = {
                "total_occurrences": int(sum(counts)),
                "min_per_model": int(min(counts)),
                "max_per_model": int(max(counts)),
            }
        out[section_key] = target_counts
    return out


def _final_block_split_scan(models) -> dict:
    modules = []
    for module_index in range(MODULE_COUNT):
        last_rel = (
            FAMILY_START
            + module_index * MODULE_STRIDE
            + (MATRIX_COUNT - 1) * MATRIX_BYTES
        )
        shared = _read(models[0], last_rel, FINAL_SHARED_BYTES)
        shared_hash = __import__("hashlib").sha256(shared).digest()
        shared_matches = 0
        suffix_matches = 0
        suffix_ref = None
        suffix_stats = []

        for model_index, model in enumerate(models):
            shared_i = _read(model, last_rel, FINAL_SHARED_BYTES)
            if __import__("hashlib").sha256(shared_i).digest() == shared_hash:
                shared_matches += 1

            suffix = _read(
                model,
                last_rel + FINAL_SHARED_BYTES,
                FINAL_SUFFIX_BYTES,
            )
            if model_index == 0:
                suffix_ref = __import__("hashlib").sha256(suffix).digest()
            if __import__("hashlib").sha256(suffix).digest() == suffix_ref:
                suffix_matches += 1

            u16 = np.frombuffer(suffix, dtype="<u2")
            exp16 = (u16 >> 10) & 31
            f16 = u16.view("<f2").astype(np.float32)
            f32 = np.frombuffer(suffix, dtype="<f4")
            finite32 = np.isfinite(f32)
            abs32 = np.abs(f32[finite32])
            suffix_stats.append({
                "fp16_exp31_fraction": float(np.mean(exp16 == 31)),
                "fp16_finite_fraction": float(np.mean(np.isfinite(f16))),
                "fp32_finite_fraction": float(np.mean(finite32)),
                "fp32_median_abs": (
                    float(np.median(abs32)) if len(abs32) else float("inf")
                ),
                "fp32_p95_abs": (
                    float(np.quantile(abs32, 0.95)) if len(abs32) else float("inf")
                ),
            })

        med = {
            key: float(np.median([x[key] for x in suffix_stats]))
            for key in suffix_stats[0]
        }
        fp32 = (
            med["fp16_exp31_fraction"] >= 0.004
            and med["fp32_finite_fraction"] >= 0.9999
            and med["fp32_p95_abs"] <= 50.0
        )
        suffix_dtype = "float32_le" if fp32 else "float16_le"
        value_count = FINAL_SUFFIX_BYTES // (4 if fp32 else 2)

        modules.append({
            "module_index": module_index,
            "shared_prefix_bytes": FINAL_SHARED_BYTES,
            "shared_prefix_exact_identity_models": shared_matches,
            "shared_prefix_dtype": "float16_le",
            "shared_prefix_row_major_512_candidate_rows": 506,
            "instrument_specific_suffix_bytes": FINAL_SUFFIX_BYTES,
            "instrument_specific_suffix_exact_identity_models": suffix_matches,
            "instrument_specific_suffix_dtype": suffix_dtype,
            "instrument_specific_suffix_value_count": value_count,
            "instrument_specific_suffix_512_wide_vector_count": value_count // LATENT,
            "suffix_consensus_stats": med,
        })

    return {
        "modules": modules,
        "suffix_dtype_pattern": [
            x["instrument_specific_suffix_dtype"] for x in modules
        ],
        "suffix_512_wide_vector_counts": [
            x["instrument_specific_suffix_512_wide_vector_count"] for x in modules
        ],
        "interpretation": (
            "All four final blocks have a 506 KiB cross-instrument shared FP16 prefix. "
            "Modules 0-2 end with six 512-wide FP16 rows; module 3 ends with three "
            "512-wide FP32 vectors. Semantic roles remain unknown."
        ),
    }


def probe_operation_constraints(models) -> dict:
    if len(models) < 2:
        raise ValueError("operation-constraint probe requires at least two models")

    spectral = _family_spectral_summary(models)
    classifications = [x["classification"] for x in spectral["matrices"]]

    return {
        "schema": "sonicraft-dnni-operation-constraints-v1",
        "truth_boundary": (
            "Numerical/negative structural evidence only. No proprietary operation name, "
            "activation, recurrence rule, graph direction, tensor semantic, or packing/"
            "permutation transform is reconstructed."
        ),
        "model_count": len(models),
        "family_start": FAMILY_START,
        "latent_width": LATENT,
        "spectral_summary": spectral,
        "family_constraints": {
            "all_sampled_matrices_dense_full_rank_like": all(
                x["dense_full_rank_like"] for x in classifications
            ),
            "any_sampled_matrix_low_rank_like": any(
                x["low_rank_like"] for x in classifications
            ),
            "any_sampled_matrix_identity_like": any(
                x["identity_like"] for x in classifications
            ),
            "any_sampled_matrix_near_orthogonal": any(
                x["near_orthogonal"] for x in classifications
            ),
        },
        "pairwise_tied_weight_scan": _pairwise_tied_weight_scan(models),
        "metadata_literal_dimension_scan": _metadata_dimension_scan(models),
        "final_block_split_scan": _final_block_split_scan(models),
        "remaining_unknowns": [
            "matrix multiplication direction/order",
            "nonlinear activation type",
            "bias/vector locations",
            "state recurrence/update equation",
            "meaning of the 128/256/288 feature widths and terminal 512-wide vector bundles",
            "output representation/decoder",
        ],
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
    result = probe_operation_constraints(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
