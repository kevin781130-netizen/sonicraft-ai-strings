#!/usr/bin/env python3
from __future__ import annotations

"""High-precision numeric-layout probe for the observed DNNI shared core.

The probe looks for regions whose bytes are consistently much more plausible as
little-endian float32 than float16 across multiple user-provided models. It emits
only offsets/statistics/shape candidates; it does not invent tensor names or graph ops.
"""

import argparse
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np

from dnni_model_shell import DnniModelCatalog, load_registry

DEFAULT_SHARED_CORE_BYTES = 126_227_640
DEFAULT_WINDOW_BYTES = 65_536
COMMON_DIMS = (32, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048)


@dataclass
class WindowStats:
    fp16_exp31_fraction: float
    fp16_median_abs: float
    fp16_p95_abs: float
    fp32_finite_fraction: float
    fp32_median_abs: float
    fp32_p95_abs: float


def numeric_stats(data: bytes) -> WindowStats:
    b2 = data[: (len(data) // 2) * 2]
    u16 = np.frombuffer(b2, dtype="<u2")
    exp16 = (u16 >> 10) & 31
    f16 = u16.view("<f2").astype(np.float32)
    finite16 = np.isfinite(f16)
    a16 = np.abs(f16[finite16])

    b4 = data[: (len(data) // 4) * 4]
    f32 = np.frombuffer(b4, dtype="<f4")
    finite32 = np.isfinite(f32)
    a32 = np.abs(f32[finite32])

    return WindowStats(
        fp16_exp31_fraction=float(np.mean(exp16 == 31)) if len(exp16) else 1.0,
        fp16_median_abs=float(np.median(a16)) if len(a16) else math.inf,
        fp16_p95_abs=float(np.quantile(a16, 0.95)) if len(a16) else math.inf,
        fp32_finite_fraction=float(np.mean(finite32)) if len(finite32) else 0.0,
        fp32_median_abs=float(np.median(a32)) if len(a32) else math.inf,
        fp32_p95_abs=float(np.quantile(a32, 0.95)) if len(a32) else math.inf,
    )


def fp32_candidate(stats: WindowStats) -> bool:
    return (
        stats.fp16_exp31_fraction >= 0.004
        and stats.fp32_finite_fraction >= 0.9999
        and stats.fp32_median_abs <= 5.0
        and stats.fp32_p95_abs <= 50.0
    )


def fp16_plausible(stats: WindowStats) -> bool:
    return (
        stats.fp16_exp31_fraction <= 0.001
        and stats.fp16_median_abs <= 2.0
        and stats.fp16_p95_abs <= 10.0
    )


def median_stats(rows: list[WindowStats]) -> WindowStats:
    fields = WindowStats.__dataclass_fields__.keys()
    values = {}
    for field in fields:
        values[field] = float(np.median([getattr(r, field) for r in rows]))
    return WindowStats(**values)


def shape_candidates(element_count: int) -> list[list[int]]:
    out = []
    for a in COMMON_DIMS:
        if element_count % a:
            continue
        b = element_count // a
        if b in COMMON_DIMS and a <= b:
            out.append([a, b])
    return out


def probe_dtype_map(models, shared_core_bytes: int = DEFAULT_SHARED_CORE_BYTES,
                    window_bytes: int = DEFAULT_WINDOW_BYTES) -> dict:
    if len(models) < 2:
        raise ValueError("dtype probe requires at least two models")
    if window_bytes <= 0 or window_bytes % 4:
        raise ValueError("window_bytes must be a positive multiple of 4")

    per_model: list[list[WindowStats]] = []
    for model in models:
        weights = model.section("weights")
        if weights.size < shared_core_bytes:
            raise ValueError(f"{model.path}: weights smaller than shared core")
        windows = []
        with model.path.open("rb") as f:
            f.seek(weights.offset)
            remaining = shared_core_bytes
            while remaining:
                data = f.read(min(window_bytes, remaining))
                if not data:
                    raise RuntimeError(f"{model.path}: unexpected EOF in shared core")
                windows.append(numeric_stats(data))
                remaining -= len(data)
        per_model.append(windows)

    count = len(per_model[0])
    if any(len(x) != count for x in per_model):
        raise RuntimeError("inconsistent shared-core window count")

    consensus = [median_stats([m[i] for m in per_model]) for i in range(count)]
    flags = [fp32_candidate(x) for x in consensus]

    spans = []
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i + 1
        while j < len(flags) and flags[j]:
            j += 1
        start = i * window_bytes
        end = min(shared_core_bytes, j * window_bytes)
        # Keep only persistent regions; isolated windows are too easy to misclassify.
        if end - start >= 2 * window_bytes:
            elements = (end - start) // 4
            spans.append({
                "offset": start,
                "end": end,
                "bytes": end - start,
                "dtype_candidate": "float32_le",
                "element_count": elements,
                "shape_candidates": shape_candidates(elements),
                "consensus_stats": asdict(median_stats(consensus[i:j])),
            })
        i = j

    covered = set()
    for s in spans:
        a = s["offset"] // window_bytes
        b = math.ceil(s["end"] / window_bytes)
        covered.update(range(a, b))
    bulk = [x for idx, x in enumerate(consensus) if idx not in covered]
    bulk_fp16_fraction = (
        float(np.mean([fp16_plausible(x) for x in bulk])) if bulk else 0.0
    )

    return {
        "schema": "sonicraft-dnni-dtype-map-v1",
        "truth_boundary": (
            "Numeric plausibility only. Spans are dtype candidates, not decoded tensor names, "
            "shapes, layer semantics, or executable graph operations."
        ),
        "model_count": len(models),
        "shared_core_bytes": shared_core_bytes,
        "window_bytes": window_bytes,
        "bulk_non_candidate_windows_fp16_plausible_fraction": bulk_fp16_fraction,
        "float32_candidate_spans": spans,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default="models/dnni")
    ap.add_argument("--registry", default="training/configs/dnni_source_labels.json")
    ap.add_argument("--shared-core-bytes", type=int, default=DEFAULT_SHARED_CORE_BYTES)
    ap.add_argument("--window-bytes", type=int, default=DEFAULT_WINDOW_BYTES)
    ap.add_argument("--out")
    args = ap.parse_args()

    registry = load_registry(args.registry)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(args.model_dir, recursive=True)
    result = probe_dtype_map(models, args.shared_core_bytes, args.window_bytes)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
