#!/usr/bin/env python3
from __future__ import annotations

"""Find exact byte-identical regions shared by multiple DNNI model cores.

The output is structural evidence only. Exact equality across instrument models can
help separate shared/global parameters from instrument-specific parameters, but it
does not assign layer names or graph semantics.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from dnni_model_shell import DnniModelCatalog, load_registry

DEFAULT_SHARED_CORE_BYTES = 126_227_640
DEFAULT_BLOCK_BYTES = 65_536


def block_hashes(model, shared_core_bytes: int, block_bytes: int) -> list[bytes]:
    weights = model.section("weights")
    if weights.size < shared_core_bytes:
        raise ValueError(f"{model.path}: weights smaller than shared core")
    out = []
    with model.path.open("rb") as f:
        f.seek(weights.offset)
        remaining = shared_core_bytes
        while remaining:
            data = f.read(min(block_bytes, remaining))
            if not data:
                raise RuntimeError(f"{model.path}: unexpected EOF")
            out.append(hashlib.sha256(data).digest())
            remaining -= len(data)
    return out


def probe_shared_regions(models, shared_core_bytes=DEFAULT_SHARED_CORE_BYTES,
                         block_bytes=DEFAULT_BLOCK_BYTES) -> dict:
    if len(models) < 2:
        raise ValueError("shared-region probe requires at least two models")
    if block_bytes <= 0:
        raise ValueError("block_bytes must be positive")

    tables = [block_hashes(m, shared_core_bytes, block_bytes) for m in models]
    count = len(tables[0])
    if any(len(t) != count for t in tables):
        raise RuntimeError("inconsistent block count")

    common = [
        all(tables[m][i] == tables[0][i] for m in range(1, len(tables)))
        for i in range(count)
    ]

    clusters = []
    i = 0
    while i < count:
        if not common[i]:
            i += 1
            continue
        j = i + 1
        while j < count and common[j]:
            j += 1
        start = i * block_bytes
        end = min(shared_core_bytes, j * block_bytes)
        clusters.append({
            "offset": start,
            "end": end,
            "bytes": end - start,
            "blocks": j - i,
        })
        i = j

    starts = [x["offset"] for x in clusters]
    deltas = [b - a for a, b in zip(starts, starts[1:])]
    delta_counts = Counter(deltas)

    total_common = sum(x["bytes"] for x in clusters)
    return {
        "schema": "sonicraft-dnni-shared-region-map-v1",
        "truth_boundary": (
            "Exact cross-model byte identity only. Shared regions are not assigned "
            "proprietary layer names or graph semantics."
        ),
        "model_count": len(models),
        "shared_core_bytes": shared_core_bytes,
        "block_bytes": block_bytes,
        "exact_common_bytes": total_common,
        "exact_common_fraction": total_common / shared_core_bytes,
        "common_clusters": clusters,
        "repeated_cluster_start_deltas": [
            {"bytes": delta, "count": n}
            for delta, n in delta_counts.most_common()
            if n >= 2
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default="models/dnni")
    ap.add_argument("--registry", default="training/configs/dnni_source_labels.json")
    ap.add_argument("--shared-core-bytes", type=int, default=DEFAULT_SHARED_CORE_BYTES)
    ap.add_argument("--block-bytes", type=int, default=DEFAULT_BLOCK_BYTES)
    ap.add_argument("--out")
    args = ap.parse_args()

    registry = load_registry(args.registry)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(args.model_dir, recursive=True)
    result = probe_shared_regions(models, args.shared_core_bytes, args.block_bytes)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
