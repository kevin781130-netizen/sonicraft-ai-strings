from __future__ import annotations

"""Local-only DNNI package quarantine/import helpers.

This module deliberately does *not* claim to decode the proprietary DNNI tensor map.
It preserves four user-supplied packages as separate timbre references, validates the
known v4 container layout, records hashes, and keeps them out of the commercial
clean-room/release path.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import os
import tarfile
from typing import Iterable

import numpy as np

EXPECTED_MAGIC = "ff00ca7f"
EXPECTED_HEADER_SIZE = 140
EXPECTED_WEIGHT_BYTES = 132_502_456


@dataclass
class Fp16Probe:
    sampled: int
    finite_fraction: float
    nan_fraction: float
    inf_fraction: float
    abs_le_1_fraction: float
    abs_le_10_fraction: float
    min_finite: float | None
    max_finite: float | None


@dataclass
class DnniImportRecord:
    timbre_id: str
    source_tar: str
    source_tar_sha256: str
    manifest_source_name: str | None
    source_size: int | None
    magic_hex: str | None
    version: int | None
    header_size: int | None
    weight_file: str
    weight_bytes: int
    weight_sha256: str
    fp16_probe: dict
    tensor_map_status: str = "unknown"
    training_role: str = "quarantined_reference_only"
    release_blocked: bool = True
    commercial_safe: bool = False
    cleanroom_eligible: bool = False


def sha256_file(path: str | Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _safe_members(tf: tarfile.TarFile, root: Path):
    root_r = root.resolve()
    for member in tf.getmembers():
        dest = (root / member.name).resolve()
        if os.path.commonpath([str(root_r), str(dest)]) != str(root_r):
            raise RuntimeError(f"unsafe tar member: {member.name}")
        if member.issym() or member.islnk():
            raise RuntimeError(f"links are not accepted in DNNI quarantine tar: {member.name}")
        yield member


def extract_tar(source_tar: str | Path, out_dir: str | Path) -> Path:
    source_tar = Path(source_tar)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_tar, "r:*") as tf:
        tf.extractall(out_dir, members=list(_safe_members(tf, out_dir)))
    return out_dir


def _find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one {name} under {root}, found {len(hits)}")
    return hits[0]


def load_manifest(root: str | Path) -> dict:
    p = _find_one(Path(root), "manifest.json")
    return json.loads(p.read_text(encoding="utf-8"))


def _manifest_scalar(m: dict, *keys, default=None):
    for k in keys:
        if k in m:
            return m[k]
    return default


def probe_fp16(path: str | Path, samples: int = 1_000_000) -> Fp16Probe:
    path = Path(path)
    count = path.stat().st_size // 2
    if count <= 0:
        raise RuntimeError(f"empty fp16 payload: {path}")
    arr = np.memmap(path, dtype="<f2", mode="r")
    n = min(samples, len(arr))
    idx = np.linspace(0, len(arr) - 1, n, dtype=np.int64)
    x = np.asarray(arr[idx], dtype=np.float32)
    finite = np.isfinite(x)
    xf = x[finite]
    return Fp16Probe(
        sampled=int(n),
        finite_fraction=float(finite.mean()),
        nan_fraction=float(np.isnan(x).mean()),
        inf_fraction=float(np.isinf(x).mean()),
        abs_le_1_fraction=float(np.mean(np.abs(xf) <= 1.0)) if len(xf) else 0.0,
        abs_le_10_fraction=float(np.mean(np.abs(xf) <= 10.0)) if len(xf) else 0.0,
        min_finite=float(xf.min()) if len(xf) else None,
        max_finite=float(xf.max()) if len(xf) else None,
    )


def import_one(source_tar: str | Path, out_root: str | Path, timbre_id: str) -> DnniImportRecord:
    source_tar = Path(source_tar)
    slot = Path(out_root) / timbre_id
    if slot.exists() and any(slot.iterdir()):
        raise RuntimeError(f"destination is not empty: {slot}")
    extract_tar(source_tar, slot)
    m = load_manifest(slot)
    weights = _find_one(slot, "weights_fp16.bin")
    magic = str(_manifest_scalar(m, "magic_hex", default="")).lower() or None
    header_size = _manifest_scalar(m, "header_size", "declared_header_size")
    version = _manifest_scalar(m, "version", "version_le_u32")
    source_size = _manifest_scalar(m, "source_size")
    source_name = _manifest_scalar(m, "source", "source_file")

    errors = []
    if magic and magic != EXPECTED_MAGIC:
        errors.append(f"magic={magic}")
    if header_size is not None and int(header_size) != EXPECTED_HEADER_SIZE:
        errors.append(f"header_size={header_size}")
    if weights.stat().st_size != EXPECTED_WEIGHT_BYTES:
        errors.append(f"weight_bytes={weights.stat().st_size}")
    if errors:
        raise RuntimeError("unexpected DNNI layout: " + ", ".join(errors))

    return DnniImportRecord(
        timbre_id=timbre_id,
        source_tar=str(source_tar.resolve()),
        source_tar_sha256=sha256_file(source_tar),
        manifest_source_name=str(source_name) if source_name else None,
        source_size=int(source_size) if source_size is not None else None,
        magic_hex=magic,
        version=int(version) if version is not None else None,
        header_size=int(header_size) if header_size is not None else None,
        weight_file=str(weights.resolve()),
        weight_bytes=int(weights.stat().st_size),
        weight_sha256=sha256_file(weights),
        fp16_probe=asdict(probe_fp16(weights)),
    )


def import_four(sources: Iterable[str | Path], out_root: str | Path, names: Iterable[str] | None = None) -> list[DnniImportRecord]:
    sources = list(sources)
    if len(sources) != 4:
        raise RuntimeError(f"exactly four DNNI tar packages are required, got {len(sources)}")
    names = list(names or [f"timbre_{i}" for i in range(1, 5)])
    if len(names) != 4 or len(set(names)) != 4:
        raise RuntimeError("four unique timbre names are required")
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    records = [import_one(src, out_root, name) for src, name in zip(sources, names)]
    bundle = {
        "schema": "sonicraft-dnni-four-timbres-reference-v1",
        "warning": "DNNI tensor names/shapes are not decoded. These files are quarantined references and are not clean-room training data.",
        "release_blocked": True,
        "commercial_safe": False,
        "cleanroom_eligible": False,
        "timbres": [asdict(r) for r in records],
    }
    (out_root / "bundle_manifest.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return records
