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
TAIL_SHARED_BYTES = 448 * 1024
TAIL_VARIABLE_BYTES = 64 * 1024
PROJECTION64_OFFSETS = (75_628_544, 95_617_024)
PROJECTION64_BYTES = 131_072
TARGET_DIMS = (64, 128, 256, 288, 448, 512)

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


def _quantized_u16(values: np.ndarray) -> np.ndarray:
    return np.nan_to_num(values.astype(np.float32)).astype("<f2").view("<u2")


def _same_u16_multiset(a: np.ndarray, b: np.ndarray) -> bool:
    return np.array_equal(
        np.bincount(a, minlength=65536),
        np.bincount(b, minlength=65536),
    )


def _adapter_projection_match_scan(models) -> dict:
    comparisons = 0
    exact = 0
    transpose_exact = 0
    value_multiset = 0

    for model in models:
        projections = []
        for rel in PROJECTION64_OFFSETS:
            x = np.frombuffer(
                _read(model, rel, PROJECTION64_BYTES), dtype="<f4"
            ).astype(np.float32)
            projections.append(_quantized_u16(x))

        for module_index in range(MODULE_COUNT):
            last_matrix = (
                FAMILY_START
                + module_index * MODULE_STRIDE
                + (MATRIX_COUNT - 1) * MATRIX_BYTES
            )
            tail_rel = last_matrix + TAIL_SHARED_BYTES
            tail = np.frombuffer(
                _read(model, tail_rel, TAIL_VARIABLE_BYTES), dtype="<f2"
            ).astype(np.float32)
            tail_u16 = _quantized_u16(tail)

            for proj_u16 in projections:
                comparisons += 1
                if np.array_equal(tail_u16, proj_u16):
                    exact += 1
                if np.array_equal(
                    tail_u16.reshape(64, 512),
                    proj_u16.reshape(512, 64).T,
                ):
                    transpose_exact += 1
                if _same_u16_multiset(tail_u16, proj_u16):
                    value_multiset += 1

    return {
        "comparisons": comparisons,
        "exact_matches_after_fp16_quantization": exact,
        "transpose_matches_after_fp16_quantization": transpose_exact,
        "value_multiset_matches_after_fp16_quantization": value_multiset,
        "interpretation": (
            "The 64-wide projection candidates and 64-row model-specific module tails "
            "are dimensionally compatible but are not direct copies/transposes/value-tied weights."
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
        "metadata_literal_dimension_scan": _metadata_dimension_scan(models),
        "adapter_projection_direct_weight_scan": _adapter_projection_match_scan(models),
        "remaining_unknowns": [
            "matrix multiplication direction/order",
            "nonlinear activation type",
            "bias/vector locations",
            "state recurrence/update equation",
            "meaning of the 128/256/64/288 feature widths",
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
