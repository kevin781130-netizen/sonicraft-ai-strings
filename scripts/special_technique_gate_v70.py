from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "release" / "special_technique_status_v7.0.json"
CONTRACT_PATH = ROOT / "release" / "SPECIAL_TECHNIQUE_GATE_v7.0.md"
READINESS_PATH = ROOT / "release" / "commercial_readiness_v7.0_rc2.json"

errors: list[str] = []


def load_json(path: Path) -> dict:
    if not path.is_file():
        errors.append(f"missing {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)}: top-level JSON must be an object")
        return {}
    return value


if not CONTRACT_PATH.is_file():
    errors.append("missing release/SPECIAL_TECHNIQUE_GATE_v7.0.md")
else:
    contract = CONTRACT_PATH.read_text(encoding="utf-8", errors="ignore")
    for token in [
        "Semantic preservation is not acoustic support",
        "Rights-cleared training/evaluation material",
        "Blind acoustic review",
        "exact release model manifest SHA-256",
        "exact VST3 SHA-256",
        "semantic support must exist before acoustic promotion",
    ]:
        if token not in contract:
            errors.append(f"special technique contract missing token: {token!r}")

status = load_json(STATUS_PATH)
readiness = load_json(READINESS_PATH)

if status:
    if status.get("release") != "7.0.0-rc2":
        errors.append("special technique status release mismatch")

    techniques = status.get("techniques")
    if not isinstance(techniques, dict) or not techniques:
        errors.append("special technique status must declare techniques")
        techniques = {}

    required = {
        "col_legno",
        "sul_ponticello",
        "sul_tasto",
        "natural_harmonics",
        "artificial_harmonics",
        "con_sordino",
        "portamento_transition_variants",
    }
    missing = sorted(required - set(techniques))
    if missing:
        errors.append("special technique status missing techniques: " + ", ".join(missing))

    evidence = status.get("required_evidence")
    if not isinstance(evidence, dict):
        errors.append("special technique status missing required_evidence object")
        evidence = {}

    evidence_complete = bool(evidence) and all(value is True for value in evidence.values())

    for name, item in techniques.items():
        if not isinstance(item, dict):
            errors.append(f"technique {name}: status must be an object")
            continue
        semantic = item.get("semantic_support")
        if semantic not in (True, False):
            errors.append(f"technique {name}: semantic_support must be boolean")
        detail = str(item.get("semantic_detail") or "").strip()
        if not detail:
            errors.append(f"technique {name}: semantic_detail is required")
        approved = item.get("acoustic_release_approved")
        if approved not in (True, False):
            errors.append(f"technique {name}: acoustic_release_approved must be boolean")
            continue
        if approved and semantic is not True:
            errors.append(
                f"technique {name}: acoustic approval is forbidden until exact semantic support exists"
            )
        if approved and not evidence_complete:
            errors.append(
                f"technique {name}: acoustic approval is forbidden while required evidence is incomplete"
            )

    if status.get("status") == "PROMOTED" and not evidence_complete:
        errors.append("special technique status cannot be PROMOTED while required evidence is incomplete")

if readiness:
    prep = readiness.get("software_side_release_preparation", {})
    if prep.get("special_technique_promotion_contract") != "complete":
        errors.append("commercial readiness must record special_technique_promotion_contract=complete")

    external = readiness.get("external_release_inputs_and_evidence", {})
    if external.get("special_technique_acoustic_promotion_evidence") != (
        "required_before_claiming_special_technique_acoustic_support"
    ):
        errors.append("commercial readiness must keep special-technique acoustic evidence fail-closed")

    anti_claims = readiness.get("anti_claims", [])
    if not any("semantic-only special techniques" in str(item) for item in anti_claims):
        errors.append("commercial readiness missing semantic-only special-technique anti-claim")

if errors:
    print("SONICRAFT v7.0 SPECIAL TECHNIQUE GATE: BLOCKED")
    for error in errors:
        print(" -", error)
    raise SystemExit(2)

print("SONICRAFT v7.0 SPECIAL TECHNIQUE GATE: PASS")
print(" Semantic support is audited separately from acoustic promotion evidence.")
