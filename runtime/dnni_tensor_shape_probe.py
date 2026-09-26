#!/usr/bin/env python3
from __future__ import annotations

"""Recover high-confidence matrix boundaries in the repeated DNNI core modules.

This probe never derives or emits permutation maps. It only asks whether an exact
row/column hash multiset is preserved across models for a proposed 2-D reshape.
That is enough to distinguish a structural matrix shape without reconstructing any
proprietary reordering/protection transform.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry

MODULE_STRIDE_BYTES = 3_670_016       # 3.5 MiB
MODULE_COUNT = 4
VARIABLE_PREFIX_BYTES = 2_097_152     # 2 MiB
SHARED_SUFFIX_BYTES = 1_572_864       # 1.5 MiB
MATRIX_BYTES = 524_288                # 512 * 512 * sizeof(fp16)
MATRIX_ELEMENTS = MATRIX_BYTES // 2
CANDIDATE_SHAPES = (
    (128, 2048),
    (256, 1024),
    (512, 512),
    (1024, 256),
    (2048, 128),
)


def _digest_rows(a: np.ndarray) -> list[bytes]:
    return sorted(
        hashlib.blake2b(row.tobytes(), digest_size=12).digest()
        for row in a
    )


def _digest_cols(a: np.ndarray) -> list[bytes]:
    return sorted(
        hashlib.blake2b(a[:, i].tobytes(), digest_size=12).digest()
        for i in range(a.shape[1])
    )


def _read_matrix(model, relative_offset: int, rows: int, cols: int) -> np.ndarray:
    weights = model.section("weights")
    nbytes = rows * cols * 2
    with model.path.open("rb") as f:
        f.seek(weights.offset + relative_offset)
        data = f.read(nbytes)
    if len(data) != nbytes:
        raise RuntimeError(f"{model.path}: short read at {relative_offset}")
    return np.frombuffer(data, dtype="<u2").reshape(rows, cols)


def _read_block(model, relative_offset: int, nbytes: int) -> bytes:
    weights = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(weights.offset + relative_offset)
        data = f.read(nbytes)
    if len(data) != nbytes:
        raise RuntimeError(f"{model.path}: short read at {relative_offset}")
    return data


def _same_value_multiset(models, relative_offset: int) -> bool:
    reference = np.frombuffer(
        _read_block(models[0], relative_offset, MATRIX_BYTES), dtype="<u2"
    )
    ref_hist = np.bincount(reference, minlength=65536)
    for model in models[1:]:
        values = np.frombuffer(
            _read_block(model, relative_offset, MATRIX_BYTES), dtype="<u2"
        )
        if not np.array_equal(ref_hist, np.bincount(values, minlength=65536)):
            return False
    return True


def _axis_invariance(models, relative_offset: int, rows: int, cols: int) -> dict:
    base = _read_matrix(models[0], relative_offset, rows, cols)
    base_rows = _digest_rows(base)
    base_cols = _digest_cols(base)
    row_matches = 1
    col_matches = 1
    exact_matches = 1

    base_bytes = base.tobytes()
    for model in models[1:]:
        x = _read_matrix(model, relative_offset, rows, cols)
        if x.tobytes() == base_bytes:
            exact_matches += 1
        if _digest_rows(x) == base_rows:
            row_matches += 1
        if _digest_cols(x) == base_cols:
            col_matches += 1

    return {
        "rows": rows,
        "cols": cols,
        "row_multiset_match_models": row_matches,
        "column_multiset_match_models": col_matches,
        "exact_match_models": exact_matches,
    }


def probe_tensor_shapes(models) -> dict:
    if len(models) < 2:
        raise ValueError("tensor-shape probe requires at least two models")
    for model in models:
        if model.section("weights").size < MODULE_COUNT * MODULE_STRIDE_BYTES:
            raise ValueError(f"{model.path}: weights too small for observed core modules")

    modules = []
    shape_support = {shape: True for shape in CANDIDATE_SHAPES}

    for module_index in range(MODULE_COUNT):
        module_offset = module_index * MODULE_STRIDE_BYTES
        variable = []
        for matrix_index in range(4):
            relative = module_offset + matrix_index * MATRIX_BYTES
            entry = {
                "index": matrix_index,
                "relative_offset": relative,
                "bytes": MATRIX_BYTES,
                "fp16_elements": MATRIX_ELEMENTS,
                "same_fp16_value_multiset_across_models": _same_value_multiset(
                    models, relative
                ),
                "candidate_shapes": [],
            }
            for rows, cols in CANDIDATE_SHAPES:
                inv = _axis_invariance(models, relative, rows, cols)
                entry["candidate_shapes"].append(inv)
            variable.append(entry)

        shared = []
        for shared_index in range(3):
            relative = module_offset + VARIABLE_PREFIX_BYTES + shared_index * MATRIX_BYTES
            blocks = [_read_block(m, relative, MATRIX_BYTES) for m in models]
            shared.append({
                "index": 4 + shared_index,
                "relative_offset": relative,
                "bytes": MATRIX_BYTES,
                "fp16_elements": MATRIX_ELEMENTS,
                "exact_byte_identity_across_models": all(
                    b == blocks[0] for b in blocks[1:]
                ),
            })

        # Shape discrimination uses two independent axis signatures:
        # block 0 must preserve columns across every model;
        # block 3 must preserve rows across every model.
        for shape in CANDIDATE_SHAPES:
            rows, cols = shape
            b0 = next(
                x for x in variable[0]["candidate_shapes"]
                if x["rows"] == rows and x["cols"] == cols
            )
            b3 = next(
                x for x in variable[3]["candidate_shapes"]
                if x["rows"] == rows and x["cols"] == cols
            )
            if (
                b0["column_multiset_match_models"] != len(models)
                or b3["row_multiset_match_models"] != len(models)
            ):
                shape_support[shape] = False

        modules.append({
            "index": module_index,
            "relative_offset": module_offset,
            "bytes": MODULE_STRIDE_BYTES,
            "variable_prefix_bytes": VARIABLE_PREFIX_BYTES,
            "shared_suffix_bytes": SHARED_SUFFIX_BYTES,
            "variable_matrices": variable,
            "shared_matrices": shared,
        })

    surviving = [
        {"rows": r, "cols": c}
        for (r, c), ok in shape_support.items()
        if ok
    ]

    verified = surviving[0] if len(surviving) == 1 else None
    return {
        "schema": "sonicraft-dnni-tensor-shape-probe-v1",
        "truth_boundary": (
            "This establishes byte boundaries, FP16 element counts and cross-model "
            "axis-invariance. It does not emit permutation maps, tensor names, layer "
            "semantics, graph connectivity, or executable proprietary transforms."
        ),
        "model_count": len(models),
        "module_count": MODULE_COUNT,
        "module_stride_bytes": MODULE_STRIDE_BYTES,
        "matrix_bytes": MATRIX_BYTES,
        "matrix_fp16_elements": MATRIX_ELEMENTS,
        "candidate_shapes": [
            {"rows": r, "cols": c, "survives_all_modules": shape_support[(r, c)]}
            for r, c in CANDIDATE_SHAPES
        ],
        "unique_verified_shape": verified,
        "modules": modules,
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
    result = probe_tensor_shapes(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
