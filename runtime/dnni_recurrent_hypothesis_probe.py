#!/usr/bin/env python3
from __future__ import annotations

"""Execute one evidence-graded GRU-style hypothesis on the observed DNNI recurrent family.

This is NOT claimed to be the proprietary runtime. It uses only verified byte
boundaries/shapes plus a public GRU equation to test numerical plausibility.

No raw weights or state vectors are emitted. Output contains aggregate/state norms,
ranges and gate saturation statistics only.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry
from dnni_recurrent_signature_probe import (
    HIDDEN,
    FAMILY_START,
    MODULE_STRIDE,
    MODULE_COUNT,
    MATRIX_BYTES,
    CORE_MATRIX_COUNT,
    SHARED_SLAB_BYTES,
    SUFFIX_BYTES,
)

INPUT_WIDTH = 506


def _read(model, rel: int, n: int) -> bytes:
    weights = model.section("weights")
    with model.path.open("rb") as f:
        f.seek(weights.offset + rel)
        data = f.read(n)
    if len(data) != n:
        raise RuntimeError(f"{model.path}: short read at {rel}")
    return data


def _probe_input() -> np.ndarray:
    i = np.arange(INPUT_WIDTH, dtype=np.float32)
    x = (
        np.sin(i * np.float32(0.173))
        + np.float32(0.5) * np.cos(i * np.float32(0.071))
    ).astype(np.float32)
    norm = float(np.linalg.norm(x))
    return x / max(norm, 1e-30)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-x))


def _load_module(model, module_index: int):
    start = FAMILY_START + module_index * MODULE_STRIDE
    matrices = []
    for i in range(CORE_MATRIX_COUNT):
        raw = _read(model, start + i * MATRIX_BYTES, MATRIX_BYTES)
        matrices.append(
            np.frombuffer(raw, dtype="<f2")
            .astype(np.float32)
            .reshape(HIDDEN, HIDDEN)
        )

    tail = start + CORE_MATRIX_COUNT * MATRIX_BYTES
    projection = (
        np.frombuffer(
            _read(model, tail, SHARED_SLAB_BYTES), dtype="<f2"
        )
        .astype(np.float32)
        .reshape(HIDDEN, INPUT_WIDTH)
    )

    suffix = _read(
        model, tail + SHARED_SLAB_BYTES, SUFFIX_BYTES
    )
    if module_index < 3:
        biases = (
            np.frombuffer(suffix, dtype="<f2")
            .astype(np.float32)
            .reshape(6, HIDDEN)
        )
        bias_input = biases[:3]
        bias_recurrent = biases[3:]
        bias_mode = "six_fp16_vectors_split_3_plus_3"
    else:
        biases = (
            np.frombuffer(suffix, dtype="<f4")
            .astype(np.float32)
            .reshape(3, HIDDEN)
        )
        bias_input = biases
        bias_recurrent = np.zeros_like(biases)
        bias_mode = "three_fp32_vectors_as_combined_input_bias_candidate"

    return matrices, projection, bias_input, bias_recurrent, bias_mode


def _run_candidate(model, module_index: int, steps: int) -> dict:
    matrices, projection, b_in, b_rec, bias_mode = _load_module(
        model, module_index
    )
    # Candidate serialization assumption:
    # matrices 0..2 = input transforms for reset/update/candidate
    # matrices 3..5 = recurrent transforms for reset/update/candidate.
    w_r, w_z, w_n = matrices[:3]
    r_r, r_z, r_n = matrices[3:]

    q = projection @ _probe_input()
    h = np.zeros(HIDDEN, dtype=np.float32)

    max_gate_saturation = 0.0
    trajectory = []
    all_finite = True

    for step in range(steps):
        reset = _sigmoid(w_r @ q + b_in[0] + r_r @ h + b_rec[0])
        update = _sigmoid(w_z @ q + b_in[1] + r_z @ h + b_rec[1])
        candidate = np.tanh(
            w_n @ q
            + b_in[2]
            + reset * (r_n @ h + b_rec[2])
        )
        h = (1.0 - update) * candidate + update * h

        finite = bool(np.all(np.isfinite(h)))
        all_finite = all_finite and finite
        saturation = max(
            float(np.mean((reset < 0.01) | (reset > 0.99))),
            float(np.mean((update < 0.01) | (update > 0.99))),
        )
        max_gate_saturation = max(max_gate_saturation, saturation)
        trajectory.append({
            "step": step + 1,
            "state_l2_norm": float(np.linalg.norm(h)),
            "state_max_abs": float(np.max(np.abs(h))),
            "gate_saturation_fraction": saturation,
            "finite": finite,
        })

    return {
        "module_index": module_index,
        "bias_mode": bias_mode,
        "steps": steps,
        "all_finite": all_finite,
        "max_gate_saturation_fraction": max_gate_saturation,
        "final_state_l2_norm": trajectory[-1]["state_l2_norm"],
        "final_state_max_abs": trajectory[-1]["state_max_abs"],
        "trajectory": trajectory,
    }


def probe_hypothesis(models, steps: int = 8) -> dict:
    rows = []
    for model in models:
        identity = model.registry_match
        role = (
            identity.instrument_role
            if identity and identity.instrument_role
            else model.path.stem
        )
        modules = [
            _run_candidate(model, module_index, steps)
            for module_index in range(MODULE_COUNT)
        ]
        rows.append({
            "instrument_role": role,
            "modules": modules,
        })

    aggregate = []
    for module_index in range(MODULE_COUNT):
        module_rows = [
            row["modules"][module_index] for row in rows
        ]
        aggregate.append({
            "module_index": module_index,
            "all_models_finite": all(
                x["all_finite"] for x in module_rows
            ),
            "final_state_l2_norm_min": min(
                x["final_state_l2_norm"] for x in module_rows
            ),
            "final_state_l2_norm_max": max(
                x["final_state_l2_norm"] for x in module_rows
            ),
            "final_state_max_abs_max": max(
                x["final_state_max_abs"] for x in module_rows
            ),
            "max_gate_saturation_fraction": max(
                x["max_gate_saturation_fraction"] for x in module_rows
            ),
        })

    return {
        "schema": "sonicraft-dnni-recurrent-hypothesis-probe-v1",
        "truth_boundary": (
            "Numerical plausibility of one public GRU-style equation only. "
            "This does not identify the proprietary operation, gate order, "
            "bias semantics, input feature meaning, or graph direction."
        ),
        "candidate_assumptions": {
            "input_width": INPUT_WIDTH,
            "hidden_width": HIDDEN,
            "shared_slab_interpretation": "row-major 512x506 input projection",
            "matrix_grouping": {
                "input_transforms": [0, 1, 2],
                "recurrent_transforms": [3, 4, 5],
            },
            "gate_order": ["reset", "update", "candidate"],
            "reset_mode": "after-multiplication-style candidate",
            "synthetic_input": "deterministic normalized sin/cos vector; not musical conditioning",
            "initial_hidden_state": "zeros",
        },
        "model_count": len(models),
        "steps": steps,
        "aggregate": aggregate,
        "models": rows,
        "success_gate": {
            "all_models_all_modules_finite": all(
                x["all_models_finite"] for x in aggregate
            ),
            "all_models_gate_saturation_below_1_percent": all(
                x["max_gate_saturation_fraction"] < 0.01
                for x in aggregate
            ),
        },
        "next_blocker": (
            "Map real musical controls (pitch, timing, dynamics, articulation, "
            "phrase context) into the observed 506-wide input representation."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default="models/dnni")
    ap.add_argument("--registry", default="training/configs/dnni_source_labels.json")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--out")
    args = ap.parse_args()

    if args.steps < 1 or args.steps > 128:
        raise SystemExit("--steps must be between 1 and 128")

    registry = load_registry(args.registry)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(args.model_dir, recursive=True)
    result = probe_hypothesis(models, args.steps)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
