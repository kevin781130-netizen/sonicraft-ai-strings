#!/usr/bin/env python3
from __future__ import annotations

"""Build note-level Performance Planner supervision from clean-room phrase data.

This v1 builder intentionally accepts only SONICRAFT's independently-authored
clean-room phrase corpus. It teaches symbolic performance behavior, not acoustic
truth, and is marked modeled/bootstrap throughout its output provenance.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from performance_planner_contract import (
    CONTINUOUS_TARGETS,
    FEATURE_NAMES,
    PLANNER_SCHEMA,
    PLANNER_VERSION,
    build_note_features,
    normalize_control,
)

SOURCE_DATASET = "synthetic_cleanroom_bowed_v18"
SOURCE_PHRASE_VERSION = "cleanroom_phrase_corpus_v1"
CONTROL_FPS = 100
DATASET_VERSION = "performance_planner_cleanroom_v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        raise RuntimeError(f"source index is empty: {path}")
    return rows


def note_target(curves: np.lib.npyio.NpzFile, event: dict, frames: int) -> list[float]:
    a = max(0, int(round(float(event["start_sec"]) * CONTROL_FPS)))
    b = min(frames, max(a + 1, int(round((float(event["start_sec"]) + float(event["duration_sec"])) * CONTROL_FPS))))
    if a >= frames:
        raise RuntimeError("event begins outside control-curve range")
    out: list[float] = []
    for name in CONTINUOUS_TARGETS:
        if name not in curves.files:
            raise RuntimeError(f"control sidecar missing planner target: {name}")
        values = np.asarray(curves[name][a:b], dtype=np.float32)
        if values.size == 0:
            raise RuntimeError(f"empty target slice for {name}")
        out.append(normalize_control(name, float(np.mean(values))))
    return out


def build_dataset(source_index: Path, out_dir: Path) -> dict:
    rows = load_rows(source_index)
    examples = out_dir / "examples"
    examples.mkdir(parents=True, exist_ok=True)
    out_rows: list[dict] = []
    coverage: Counter[tuple[int, str]] = Counter()

    for row in rows:
        if str(row.get("dataset_id") or row.get("dataset")) != SOURCE_DATASET:
            raise RuntimeError(f"planner v1 source must be {SOURCE_DATASET}: {row.get('sample_id')}")
        if str(row.get("phrase_version")) != SOURCE_PHRASE_VERSION:
            raise RuntimeError(f"unexpected phrase version: {row.get('phrase_version')}")
        if not bool(row.get("independently_authored_controls")):
            raise RuntimeError(f"source row lacks independent-control provenance: {row.get('sample_id')}")
        if str(row.get("training_origin", "")).lower() != "modeled":
            raise RuntimeError("clean-room planner bootstrap rows must remain training_origin=modeled")

        event_path = Path(row["events_json"])
        curve_path = Path(row["control_curves"])
        if not event_path.exists() or not curve_path.exists():
            raise FileNotFoundError(f"missing phrase artifacts for {row.get('sample_id')}")
        identity = json.loads(event_path.read_text(encoding="utf-8"))
        events = list(identity.get("events") or [])
        if not events:
            raise RuntimeError(f"phrase has no events: {event_path}")
        bpm = float(identity.get("bpm", row.get("tempo_bpm", 68.0)))
        instrument = int(identity.get("instrument", row.get("instrument", 0)))
        features = np.asarray(build_note_features(events, bpm=bpm, instrument=instrument), dtype=np.float32)
        articulation = np.asarray([int(e["articulation"]) for e in events], dtype=np.int64)

        with np.load(curve_path, allow_pickle=False) as curves:
            frame_key = next((k for k in CONTINUOUS_TARGETS if k in curves.files), None)
            if frame_key is None:
                raise RuntimeError(f"no planner target curves found: {curve_path}")
            frames = int(len(curves[frame_key]))
            continuous = np.asarray([note_target(curves, e, frames) for e in events], dtype=np.float32)

        if features.shape != (len(events), len(FEATURE_NAMES)):
            raise RuntimeError(f"feature shape mismatch: {features.shape}")
        if continuous.shape != (len(events), len(CONTINUOUS_TARGETS)):
            raise RuntimeError(f"target shape mismatch: {continuous.shape}")

        sample_id = str(row["sample_id"])
        target = examples / f"{sample_id}.npz"
        np.savez_compressed(
            target,
            features=features,
            articulation=articulation,
            continuous=continuous,
        )
        family = str(row.get("phrase_family") or identity.get("family") or "unknown")
        split = str(row.get("split") or "train")
        out_rows.append({
            "schema_version": PLANNER_SCHEMA,
            "planner_version": PLANNER_VERSION,
            "dataset_version": DATASET_VERSION,
            "sample_id": sample_id,
            "split": split,
            "file": str(target.resolve()),
            "note_count": len(events),
            "instrument": instrument,
            "phrase_family": family,
            "source_dataset": SOURCE_DATASET,
            "source_phrase_version": SOURCE_PHRASE_VERSION,
            "source_sample_id": sample_id,
            "source_events_sha256": sha256_file(event_path),
            "source_control_curves_sha256": sha256_file(curve_path),
            "training_origin": "modeled",
            "planner_supervision_kind": "cleanroom_symbolic_bootstrap",
            "final_expression_anchor": False,
            "commercial_safe": bool(row.get("commercial_safe", False)),
            "release_blocked": bool(row.get("release_blocked", False)),
        })
        coverage[(instrument, family)] += 1

    index_path = out_dir / "index.jsonl"
    index_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + "\n", encoding="utf-8")
    report = {
        "schema_version": PLANNER_SCHEMA,
        "planner_version": PLANNER_VERSION,
        "dataset_version": DATASET_VERSION,
        "source_dataset": SOURCE_DATASET,
        "source_index": str(source_index.resolve()),
        "source_index_sha256": sha256_file(source_index),
        "output_index": str(index_path.resolve()),
        "output_index_sha256": sha256_file(index_path),
        "examples": len(out_rows),
        "notes": int(sum(r["note_count"] for r in out_rows)),
        "feature_names": list(FEATURE_NAMES),
        "continuous_targets": list(CONTINUOUS_TARGETS),
        "splits": dict(Counter(r["split"] for r in out_rows)),
        "coverage": {f"{inst}:{family}": int(n) for (inst, family), n in sorted(coverage.items())},
        "training_origin": "modeled",
        "final_expression_anchor": False,
        "policy_note": "Clean-room symbolic bootstrap only; do not claim human-performance parity from this dataset.",
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Build note-level Performance Planner data from SONICRAFT clean-room phrases.")
    ap.add_argument("--source-index", default="datasets/generated/cleanroom_phrases_v1/index.jsonl")
    ap.add_argument("--out", default="datasets/processed/performance_planner_cleanroom_v1")
    args = ap.parse_args()
    report = build_dataset(Path(args.source_index), Path(args.out))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
