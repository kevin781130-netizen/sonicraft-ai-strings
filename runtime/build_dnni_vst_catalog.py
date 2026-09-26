#!/usr/bin/env python3
from __future__ import annotations

"""Build a verified local DNNI manifest for the native VST3 runtime.

Heavy hashing happens here, outside the audio plug-in. The VST3 side consumes only
validated path/layout/hash metadata and performs lightweight header/size checks.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_model_shell import DnniModelCatalog, load_registry

MAGIC = "SONICRAFT_DNNI_CATALOG_V1"

ROLE_TO_INDEX = {
    "double_bass": 0,
    "cello": 1,
    "viola": 2,
    "violin": 3,
    "piccolo": 4,
    "flute": 5,
    "oboe": 6,
    "clarinet_a": 7,
    "bassoon": 8,
    "tenor_saxophone": 9,
    "alto_saxophone": 10,
    "french_horn": 11,
    "trumpet_bb": 12,
    "tuba": 13,
    "trombone": 14,
}


def safe_field(value: object) -> str:
    text = str(value)
    if "|" in text or "\n" in text or "\r" in text:
        raise ValueError(f"manifest field contains unsupported delimiter/newline: {text!r}")
    return text


def build_manifest(model_dir: Path, registry_path: Path, out: Path) -> Path:
    registry = load_registry(registry_path)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(model_dir, recursive=True)

    rows = []
    seen = set()
    for model in models:
        match = model.registry_match
        if match is None or not match.instrument_role:
            continue
        role = match.instrument_role
        if role not in ROLE_TO_INDEX:
            continue
        idx = ROLE_TO_INDEX[role]
        if idx in seen:
            raise RuntimeError(f"duplicate model for instrument index {idx}: {role}")
        seen.add(idx)

        weights = model.section("weights")
        # Accessing these properties performs the heavyweight verification now.
        source_sha = model.source_sha256
        weights_sha = model.weights_sha256

        rows.append([
            idx,
            role,
            match.instrument_family or "",
            match.label_en or "",
            match.label_zh or "",
            match.source_uuid or "",
            str(model.path),
            model.header.file_size,
            source_sha,
            weights.offset,
            weights.size,
            weights_sha,
        ])

    rows.sort(key=lambda r: int(r[0]))
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [MAGIC]
    for row in rows:
        lines.append("|".join(safe_field(v) for v in row))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default=str(ROOT / "models" / "dnni"))
    ap.add_argument("--registry", default=str(ROOT / "training" / "configs" / "dnni_source_labels.json"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    model_dir = Path(args.model_dir).resolve()
    out = Path(args.out).resolve() if args.out else model_dir / "sonicraft_dnni_catalog.txt"
    path = build_manifest(model_dir, Path(args.registry), out)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
