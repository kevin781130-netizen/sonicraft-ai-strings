from __future__ import annotations

"""Read-only v7.0 RC evidence preflight.

This is a diagnostic dashboard, not an approval gate. FINAL_GATE_V70 and
PUBLIC_RELEASE_GATE_V70 remain authoritative and perform deeper hash/provenance checks.
"""

import argparse
import json
from pathlib import Path
from typing import Any

RELEASE = "7.0.0-rc2"
PRODUCT = "SONICRAFT AI Strings Q4"


def load_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(value, dict):
        return None, "top-level JSON is not an object"
    return value, None


def evidence_check(path: Path, predicate, detail) -> dict[str, Any]:
    value, error = load_json(path)
    if error:
        return {"status": "MISSING" if error == "missing" else "INVALID", "path": str(path), "detail": error}
    release_ok = value.get("release") == RELEASE
    passed = bool(release_ok and predicate(value))
    return {
        "status": "PASS" if passed else "BLOCKED",
        "path": str(path),
        "detail": detail(value) if release_ok else f"release mismatch: {value.get('release')!r}",
    }


def locate_plugin(root: Path) -> Path | None:
    bundle = root / "release" / "SONICRAFT AI Strings Q4.vst3" / "Contents" / "x86_64-win"
    if not bundle.is_dir():
        return None
    return next(iter(sorted(bundle.glob("*.vst3"))), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--public", action="store_true", help="include Authenticode as a required readiness item")
    ap.add_argument("--strict", action="store_true", help="return exit code 2 when required items are not ready")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON only")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    ev = root / "release" / "rc_evidence"
    model = root / "release" / "prebuilt" / "Models" / "release_model_manifest.json"
    plugin = locate_plugin(root)

    checks: dict[str, dict[str, Any]] = {}
    checks["release_vst3"] = {
        "status": "PASS" if plugin is not None else "MISSING",
        "path": str(plugin) if plugin else str(root / "release" / "SONICRAFT AI Strings Q4.vst3"),
        "detail": "release VST3 binary located" if plugin else "release VST3 binary not found",
    }

    model_obj, model_error = load_json(model)
    if model_error:
        checks["final_model"] = {
            "status": "MISSING" if model_error == "missing" else "INVALID",
            "path": str(model),
            "detail": model_error,
        }
    else:
        model_ok = (
            model_obj.get("product") == PRODUCT
            and model_obj.get("release") == RELEASE
            and model_obj.get("commercial_safe") is True
            and model_obj.get("release_approved") is True
            and model_obj.get("training_data_rights_status") == "approved_for_commercial_training_and_distribution"
        )
        checks["final_model"] = {
            "status": "PASS" if model_ok else "BLOCKED",
            "path": str(model),
            "detail": "approved commercial release-model declaration present" if model_ok else "final model is not fully approved/commercial-safe with approved rights status",
        }

    checks["build_provenance"] = evidence_check(
        ev / "build-provenance.json",
        lambda x: x.get("status") == "PASS",
        lambda x: f"status={x.get('status')!r}",
    )
    checks["steinberg_validator"] = evidence_check(
        ev / "validator-pass.json",
        lambda x: x.get("passed") is True,
        lambda x: f"passed={x.get('passed')!r}",
    )
    checks["cubase"] = evidence_check(
        ev / "host-qa-cubase.json",
        lambda x: x.get("overall") == "PASS",
        lambda x: f"overall={x.get('overall')!r}; host={x.get('host_version')!r}",
    )
    checks["studio_one"] = evidence_check(
        ev / "host-qa-studio-one.json",
        lambda x: x.get("overall") == "PASS",
        lambda x: f"overall={x.get('overall')!r}; host={x.get('host_version')!r}",
    )
    checks["rtx_acoustic"] = evidence_check(
        ev / "acoustic-qa.json",
        lambda x: x.get("overall") == "PASS",
        lambda x: f"overall={x.get('overall')!r}; model_manifest_sha256={'present' if x.get('model_manifest_sha256') else 'missing'}",
    )
    checks["blind_acoustic"] = evidence_check(
        ev / "blind-acoustic-qa.json",
        lambda x: x.get("overall") == "PASS",
        lambda x: f"overall={x.get('overall')!r}; listeners={(x.get('protocol') or {}).get('listener_count')!r}; trials={(x.get('protocol') or {}).get('trial_count')!r}",
    )

    if args.public:
        checks["authenticode"] = evidence_check(
            ev / "authenticode-pass.json",
            lambda x: x.get("status") == "Valid",
            lambda x: f"status={x.get('status')!r}",
        )

    semantic_path = root / "release" / "special_technique_status_v7.0.json"
    semantic, semantic_error = load_json(semantic_path)
    parity_gaps: list[str] = []
    if semantic and not semantic_error:
        for name, item in (semantic.get("techniques") or {}).items():
            if isinstance(item, dict) and item.get("semantic_support") is not True:
                parity_gaps.append(f"{name}: semantic_support=false")
            elif isinstance(item, dict) and item.get("acoustic_release_approved") is not True:
                parity_gaps.append(f"{name}: acoustic_release_approved=false")

    blockers = [name for name, value in checks.items() if value["status"] != "PASS"]
    result = {
        "schema": 1,
        "product": PRODUCT,
        "release": RELEASE,
        "mode": "public" if args.public else "rc",
        "preflight_ready": not blockers,
        "authoritative_gate_required": True,
        "checks": checks,
        "blocking_items": blockers,
        "non_base_release_parity_gaps": parity_gaps,
        "note": "This preflight is diagnostic only. FINAL_GATE_V70/PUBLIC_RELEASE_GATE_V70 remain authoritative and re-check hashes/provenance.",
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"SONICRAFT {RELEASE} RELEASE EVIDENCE PREFLIGHT")
        for name, value in checks.items():
            print(f" [{value['status']:<7}] {name}: {value['detail']}")
        if blockers:
            print("\nBlocking items: " + ", ".join(blockers))
        else:
            print("\nPreflight: READY FOR AUTHORITATIVE FINAL GATE")
        if parity_gaps:
            print("\nNon-base-release parity gaps:")
            for item in parity_gaps:
                print(" -", item)
        print("\nDiagnostic only; run FINAL_GATE_V70.bat / PUBLIC_RELEASE_GATE_V70.bat for approval.")

    return 2 if args.strict and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
