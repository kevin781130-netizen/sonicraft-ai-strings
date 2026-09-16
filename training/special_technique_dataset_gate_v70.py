from __future__ import annotations

"""Validate commercial provenance and coverage for v7 special-technique audio.

The source tree ships only the contract/template. A real manifest is expected to be
produced with the rights-cleared dataset and may be stored outside the repository.
"""

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_TECHNIQUES = {
    "col_legno",
    "sul_ponticello",
    "sul_tasto",
    "natural_harmonics",
    "artificial_harmonics",
    "con_sordino",
    "portamento_transition_variants",
}
FORBIDDEN_RIGHTS = {"ambiguous", "unknown", "noncommercial", "evaluation_only", "research_only"}


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON must be an object")
    return value


def valid_sha256(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(c in "0123456789abcdef" for c in text)


def validate(manifest: dict, *, allow_template: bool = False) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != 1:
        errors.append("schema must be 1")
    if manifest.get("product") != "SONICRAFT AI Strings Q4":
        errors.append("product mismatch")
    if manifest.get("release") != "7.0.0-rc2":
        errors.append("release mismatch")

    rights = manifest.get("rights_clearance") or {}
    status = str(rights.get("status") or "").lower()
    if allow_template and status == "fill_before_promotion":
        pass
    elif status != "approved_for_commercial_training_and_distribution":
        errors.append("rights_clearance.status must approve commercial training and distribution")
    if not allow_template:
        for key in ("reviewer", "reviewed_at", "evidence_reference"):
            if not str(rights.get(key) or "").strip():
                errors.append(f"rights_clearance.{key} is required")

    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        if allow_template:
            sources = []
        else:
            errors.append("sources must be a non-empty array")
            sources = []
    source_ids: set[str] = set()
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"source {i} must be an object")
            continue
        sid = str(source.get("source_id") or "").strip()
        if not sid:
            errors.append(f"source {i} missing source_id")
        elif sid in source_ids:
            errors.append(f"duplicate source_id: {sid}")
        else:
            source_ids.add(sid)
        basis = str(source.get("rights_basis") or "").strip().lower()
        if not basis:
            errors.append(f"source {sid or i} missing rights_basis")
        if basis in FORBIDDEN_RIGHTS:
            errors.append(f"source {sid or i} has forbidden rights_basis={basis}")
        if source.get("commercial_training_allowed") is not True:
            errors.append(f"source {sid or i} is not approved for commercial training")
        if source.get("model_distribution_allowed") is not True:
            errors.append(f"source {sid or i} is not approved for model distribution")
        if not str(source.get("evidence_reference") or "").strip():
            errors.append(f"source {sid or i} missing evidence_reference")
        index_sha = source.get("asset_index_sha256")
        if not valid_sha256(index_sha):
            errors.append(f"source {sid or i} missing valid asset_index_sha256")

    coverage = manifest.get("technique_coverage")
    if not isinstance(coverage, dict):
        errors.append("technique_coverage must be an object")
        coverage = {}
    missing = sorted(REQUIRED_TECHNIQUES - set(coverage))
    if missing and not allow_template:
        errors.append("missing technique coverage: " + ", ".join(missing))
    for name in sorted(REQUIRED_TECHNIQUES & set(coverage)):
        item = coverage[name]
        if not isinstance(item, dict):
            errors.append(f"technique_coverage.{name} must be an object")
            continue
        samples = item.get("sample_count")
        duration = item.get("duration_seconds")
        source_refs = item.get("source_ids")
        if allow_template and samples is None and duration is None:
            continue
        if not isinstance(samples, int) or isinstance(samples, bool) or samples <= 0:
            errors.append(f"technique_coverage.{name}.sample_count must be positive")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            errors.append(f"technique_coverage.{name}.duration_seconds must be positive")
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"technique_coverage.{name}.source_ids must be non-empty")
        elif source_ids and any(str(ref) not in source_ids for ref in source_refs):
            errors.append(f"technique_coverage.{name} references unknown source_id")
        if item.get("annotation_verified") is not True:
            errors.append(f"technique_coverage.{name}.annotation_verified must be true")

    for key in ("dataset_index_sha256", "annotation_index_sha256"):
        value = manifest.get(key)
        if allow_template and value is None:
            continue
        if not valid_sha256(value):
            errors.append(f"{key} must be a valid SHA-256")

    if manifest.get("commercial_promotion_approved") is True and errors:
        errors.append("commercial_promotion_approved=true is forbidden while provenance/coverage errors exist")
    if manifest.get("commercial_promotion_approved") is True and status != "approved_for_commercial_training_and_distribution":
        errors.append("commercial promotion requires approved rights clearance")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--allow-template", action="store_true")
    args = ap.parse_args()
    try:
        manifest = load(Path(args.manifest))
    except Exception as exc:
        print(f"SPECIAL TECHNIQUE DATASET GATE: BLOCKED - {exc}")
        return 2
    errors = validate(manifest, allow_template=args.allow_template)
    if errors:
        print("SPECIAL TECHNIQUE DATASET GATE: BLOCKED")
        for error in errors:
            print(" -", error)
        return 2
    print("SPECIAL TECHNIQUE DATASET GATE: PASS")
    if args.allow_template:
        print(" Template structure only; no commercial dataset approval is claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
