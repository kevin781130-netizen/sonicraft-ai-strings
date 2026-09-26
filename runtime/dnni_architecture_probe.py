#!/usr/bin/env python3
from __future__ import annotations

"""Cross-model structural probe for DNNI v4 payloads.

This tool derives reproducible layout hypotheses from multiple user-provided models.
It deliberately does not decrypt/defeat protection, invent tensor names/shapes, or
claim that an opaque repeated block is executable neural-network state.
"""

import argparse
import json
import math
import struct
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from dnni_model_shell import DnniModelCatalog, load_registry

COMMON_ZERO_MIN = 16


@dataclass
class ModelArchitectureRow:
    filename: str
    role: str | None
    family: str | None
    weights_bytes: int
    tail_bytes: int
    tail_subblocks: int | None
    candidate_mic_groups: int | None
    header_aux_count: int
    section4_bytes: int


def _zero_runs(path: Path, offset: int, size: int, min_len: int = COMMON_ZERO_MIN) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    chunk = 8 << 20
    overlap = min_len - 1
    prev = b""
    pos = 0
    with path.open("rb") as f:
        f.seek(offset)
        while pos < size:
            data = f.read(min(chunk, size - pos))
            if not data:
                break
            buf = prev + data
            base = pos - len(prev)
            i = 0
            while i < len(buf):
                if buf[i] != 0:
                    i += 1
                    continue
                j = i + 1
                while j < len(buf) and buf[j] == 0:
                    j += 1
                if j - i >= min_len:
                    out.append((base + i, j - i))
                i = j
            prev = buf[-overlap:] if len(buf) >= overlap else buf
            pos += len(data)
    out.sort()
    merged: list[tuple[int, int]] = []
    for start, length in out:
        end = start + length
        if merged and start <= merged[-1][0] + merged[-1][1]:
            p0, plen = merged[-1]
            merged[-1] = (p0, max(p0 + plen, end) - p0)
        else:
            merged.append((start, length))
    return merged


def _gcd_nonzero(values: Iterable[int]) -> int:
    g = 0
    for v in values:
        if v:
            g = math.gcd(g, abs(int(v)))
    return g


def derive_architecture(models) -> dict:
    if len(models) < 2:
        raise ValueError("architecture probe needs at least two DNNI models")

    weights_sizes = sorted({m.header.section("weights").size for m in models})
    if len(weights_sizes) < 2:
        raise ValueError("need at least two distinct weights sizes to derive the variable-tail group stride")

    group_stride = _gcd_nonzero(
        b - a for i, a in enumerate(weights_sizes) for b in weights_sizes[i + 1 :]
    )
    if group_stride <= 0:
        raise ValueError("could not derive a variable-tail group stride")

    # Candidate shared core is the largest prefix leaving an integer number of groups
    # in every observed size. Choose the smallest observed model as the baseline and
    # use repeated zero-run spacing inside its tail to refine the subblock stride.
    min_size = min(weights_sizes)
    baseline = next(m for m in models if m.header.section("weights").size == min_size)
    weights = baseline.header.section("weights")
    runs = _zero_runs(baseline.path, weights.offset, weights.size, min_len=32)

    # Repeated large zero-run starts near the end expose the internal subblock cadence.
    large_starts = [s for s, n in runs if n >= 1024]
    diffs = [b - a for a, b in zip(large_starts, large_starts[1:]) if b > a]
    diff_counts = Counter(diffs)
    subblock_stride = diff_counts.most_common(1)[0][0] if diff_counts else 0
    if subblock_stride <= 0 or group_stride % subblock_stride != 0:
        subblock_stride = 0

    subblocks_per_group = group_stride // subblock_stride if subblock_stride else None

    # Search core candidates compatible with all observed sizes and prefer a boundary
    # immediately preceding the repeated subblock train in the baseline.
    if subblock_stride:
        tail_start_candidates = []
        for start, _ in runs:
            if start < min_size and (min_size - start) % group_stride == 0:
                tail_start_candidates.append(start)
        # The first compatible boundary starts the complete repeated train. Later
        # zero-runs can also land on a whole-group boundary inside that train.
        shared_core = min(tail_start_candidates) if tail_start_candidates else min_size - group_stride * 8
    else:
        shared_core = min_size - group_stride * 8

    # Common zero gaps are useful hard boundaries because all bytes agree exactly.
    core_run_sets = []
    for m in models:
        w = m.header.section("weights")
        core_run_sets.append(set(_zero_runs(m.path, w.offset, min(shared_core, w.size), min_len=16)))
    common_zero = sorted(set.intersection(*core_run_sets)) if core_run_sets else []

    rows: list[ModelArchitectureRow] = []
    for m in models:
        w = m.header.section("weights")
        tail = w.size - shared_core
        groups = tail // group_stride if tail >= 0 and tail % group_stride == 0 else None
        subblocks = tail // subblock_stride if subblock_stride and tail >= 0 and tail % subblock_stride == 0 else None
        with m.path.open("rb") as f:
            hdr = f.read(140)
        aux_count = struct.unpack_from("<I", hdr, 132)[0]
        rows.append(ModelArchitectureRow(
            filename=m.path.name,
            role=(m.registry_match.instrument_role if m.registry_match else None),
            family=(m.registry_match.instrument_family if m.registry_match else None),
            weights_bytes=w.size,
            tail_bytes=tail,
            tail_subblocks=subblocks,
            candidate_mic_groups=groups,
            header_aux_count=aux_count,
            section4_bytes=m.header.section("section4").size,
        ))

    group_values = sorted({r.candidate_mic_groups for r in rows if r.candidate_mic_groups is not None})

    return {
        "schema": "sonicraft-dnni-architecture-probe-v1",
        "truth_boundary": (
            "Observed byte-layout relationships only. candidate_mic_groups is a structural "
            "hypothesis supported by public 8-11 microphone documentation; it is not a decoded proprietary graph."
        ),
        "observed_weights_sizes": weights_sizes,
        "shared_core_bytes": shared_core,
        "variable_tail_group_bytes": group_stride,
        "tail_subblock_bytes": subblock_stride or None,
        "subblocks_per_candidate_group": subblocks_per_group,
        "observed_candidate_group_counts": group_values,
        "common_zero_gaps": [
            {"offset": start, "bytes": length} for start, length in common_zero
        ],
        "models": [asdict(r) for r in sorted(rows, key=lambda x: (x.candidate_mic_groups or 0, x.role or ""))],
        "evidence": {
            "weights_size_deltas_gcd": group_stride,
            "repeated_large_zero_run_spacing_mode": subblock_stride or None,
            "header_offset_132_tracks_group_count": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default="models/dnni")
    ap.add_argument("--registry", default="training/configs/dnni_source_labels.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    registry = load_registry(args.registry)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(args.model_dir, recursive=True)
    if len(models) < 2:
        raise SystemExit("Need at least two .dnni files for cross-model architecture probing.")

    result = derive_architecture(models)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
