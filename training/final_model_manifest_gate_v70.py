from __future__ import annotations

"""Fail-closed provenance validator for the v7.0 release model manifest."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PRODUCT = "SONICRAFT AI Strings Q4"
RELEASE = "7.0.0-rc2"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def valid_sha256(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(c in "0123456789abcdef" for c in text)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON must be an object")
    return value


def validate(manifest: dict, model_root: Path | None, *, allow_template: bool = False) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != 1:
        errors.append("schema must be 1")
    if manifest.get("product") != PRODUCT:
        errors.append("product mismatch")
    if manifest.get("release") != RELEASE:
        errors.append("release mismatch")

    if allow_template:
        if manifest.get("commercial_safe") not in (False, None):
            errors.append("template commercial_safe must remain false")
        if manifest.get("release_approved") not in (False, None):
            errors.append("template release_approved must remain false")
    else:
        if manifest.get("commercial_safe") is not True:
            errors.append("commercial_safe must be true")
        if manifest.get("release_approved") is not True:
            errors.append("release_approved must be true")

    rights = str(manifest.get("training_data_rights_status") or "").lower()
    if allow_template and rights == "fill_before_release":
        pass
    elif rights != "approved_for_commercial_training_and_distribution":
        errors.append("training_data_rights_status is not commercially approved")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
        provenance = {}
    for key in (
        "dataset_manifest_sha256",
        "training_run_manifest_sha256",
        "model_card_sha256",
        "rights_review_sha256",
        "final_checkpoint_sha256",
    ):
        value = provenance.get(key)
        if allow_template and value is None:
            continue
        if not valid_sha256(value):
            errors.append(f"provenance.{key} must be a valid SHA-256")

    for key in ("training_run_id", "approved_by", "approved_at"):
        value = provenance.get(key)
        if allow_template and not value:
            continue
        if not str(value or "").strip():
            errors.append(f"provenance.{key} is required")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        if allow_template:
            files = []
        else:
            errors.append("files must be a non-empty array")
            files = []
    names: set[str] = set()
    for i, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"files[{i}] must be an object")
            continue
        name = str(item.get("name") or "").strip()
        expected = str(item.get("sha256") or "").lower()
        if not name:
            errors.append(f"files[{i}] missing name")
            continue
        if name in names:
            errors.append(f"duplicate model file: {name}")
        names.add(name)
        if not valid_sha256(expected):
            errors.append(f"model file {name} missing valid SHA-256")
            continue
        if model_root is not None:
            path = model_root / name
            if not path.is_file():
                errors.append(f"model file missing: {name}")
            elif sha256(path).lower() != expected:
                errors.append(f"model file hash mismatch: {name}")

    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        errors.append("capabilities must be an object")
    else:
        techniques = capabilities.get("special_techniques")
        if not isinstance(techniques, dict):
            errors.append("capabilities.special_techniques must be an object")
        else:
            for name, status in techniques.items():
                if status not in ("trained", "unsupported", "semantic_only"):
                    errors.append(
                        f"capabilities.special_techniques.{name} must be trained, unsupported, or semantic_only"
                    )

    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--model-root")
    ap.add_argument("--allow-template", action="store_true")
    args = ap.parse_args()
    path = Path(args.manifest)
    if not path.is_file():
        print(f"FINAL MODEL MANIFEST GATE: BLOCKED - missing {path}")
        return 2
    try:
        manifest = load(path)
    except Exception as exc:
        print(f"FINAL MODEL MANIFEST GATE: BLOCKED - {exc}")
        return 2
    model_root = Path(args.model_root) if args.model_root else None
    errors = validate(manifest, model_root, allow_template=args.allow_template)
    if errors:
        print("FINAL MODEL MANIFEST GATE: BLOCKED")
        for error in errors:
            print(" -", error)
        return 2
    print("FINAL MODEL MANIFEST GATE: PASS")
    if args.allow_template:
        print(" Template structure only; no trained model approval is claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
