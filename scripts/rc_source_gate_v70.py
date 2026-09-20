from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def need(rel: str, token: str | None = None) -> str:
    p = ROOT / rel
    if not p.is_file():
        errors.append(f"missing {rel}")
        return ""
    text = p.read_text(encoding="utf-8", errors="ignore")
    if token is not None and token not in text:
        errors.append(f"{rel}: missing token {token!r}")
    return text


def read_json(rel: str) -> dict:
    text = need(rel)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except Exception as exc:
        errors.append(f"invalid JSON {rel}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{rel}: top-level JSON must be an object")
        return {}
    return value


# Version / pinned build contract.
if (ROOT / "VERSION").read_text().strip() != "7.0.0-rc2":
    errors.append("VERSION is not 7.0.0-rc2")
need("CMakeLists.txt", "project(SonicraftAIStringsQ4 VERSION 7.0.0")
build = need("installer/build_release_windows.ps1", "9fad9770f2ae8542ab1a548a68c1ad1ac690abe0")
for token in ["checkout", "--detach", "submodule", "validator-pass.json", "build-provenance.json"]:
    if token not in build:
        errors.append(f"Windows builder missing reproducibility token: {token}")
if re.search(r"git\s+clone[^\n]+vst3sdk[^\n]+(?:master|main)", build, re.I):
    errors.append("Windows builder still clones moving VST3 branch explicitly")

for rel in [
    "installer/rc_v70/BUILD_RC_V70.ps1",
    "installer/rc_v70/RUN_HOST_QA_V70.ps1",
    "installer/rc_v70/RUN_ACOUSTIC_QA_V70.ps1",
    "installer/rc_v70/FINAL_GATE_V70.ps1",
    "RC_BUILD_V70.bat",
    "QA_CUBASE_V70.bat",
    "QA_STUDIO_ONE_V70.bat",
    "QA_RTX5090_ACOUSTIC_V70.bat",
    "FINAL_GATE_V70.bat",
]:
    need(rel)

need("installer/inno/SONICRAFT_AI_Strings.iss", '#define AppVersion "7.0.0-rc2"')
need("installer/BUILD_FINAL_INNO_INSTALLER.ps1", "[string]$Version='7.0.0-rc2'")
need("installer/GENERATE_PREBUILT_MANIFEST.ps1", "version='7.0.0-rc2'")
need("resource/SONICRAFT_AI_Strings_Q4.uidesc", 'tag="828"')

# Consumer packaging contract. The optional StringCC bridge is source-tree interoperability,
# not part of the signed consumer product payload.
collect = need("installer/COLLECT_PREBUILT_APP.ps1", "Frontend\\editor_server.py")
for token in [
    "Frontend\\index.html",
    "Tools\\OPEN_INSTRUMENT_EDITOR.bat",
    "COMPILE_MUSICXML_STRINGS_v62.bat",
    "AUTO_LOOP_STRINGS_v62.bat",
    "PERFORMANCE_CHECKPOINT_V62.bat",
]:
    if token not in collect:
        errors.append(f"prebuilt collector missing frontend/runtime token: {token}")
if "stringcc-governance" in collect.lower() or "integrations\\stringcc" in collect.lower():
    errors.append("optional StringCC governance bridge must not be bundled into consumer prebuilt payload")

need("installer/tools/verify_prebuilt_layout.py", "Frontend/index.html")
need("manager_release.ps1", "OPEN_INSTRUMENT_EDITOR.bat")
for rel in ["COMPILE_MUSICXML_STRINGS_v62.bat", "AUTO_LOOP_STRINGS_v62.bat", "PERFORMANCE_CHECKPOINT_V62.bat"]:
    bt = need(rel, "%ROOT%..\\Runtime\\")
    if "runtime\\venv\\Scripts\\python.exe" not in bt:
        errors.append(f"{rel}: installed runtime Python fallback missing")
need("runtime/smoke_frontend_packaging_v70.py", "consumer-packaging smoke PASS")

# Frontend source/layout lock.
need("FRONTEND_LAYOUT_GATE_V70.bat", "frontend_layout_gate_v70.py")
layout_gate = ROOT / "runtime" / "frontend_layout_gate_v70.py"
if not layout_gate.is_file():
    errors.append("missing runtime/frontend_layout_gate_v70.py")
else:
    cp = subprocess.run([sys.executable, str(layout_gate)], cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        errors.append("frontend layout gate failed: " + ((cp.stdout + "\n" + cp.stderr).strip()[-3000:]))

# Final release-gate contracts remain fail-closed and provenance-bound.
gate = need("runtime/release_gate_v70.py", "acoustic evidence is not bound to a model manifest hash")
for token in ["host_exe_sha256", "expected_sdk", "9fad9770f2ae8542ab1a548a68c1ad1ac690abe0"]:
    if token not in gate:
        errors.append(f"final gate missing provenance token: {token}")
need("installer/rc_v70/RUN_ACOUSTIC_QA_V70.ps1", "model_manifest_sha256")
need("installer/rc_v70/RUN_HOST_QA_V70.ps1", "host_exe_sha256")

runtime_install = need("installer/INSTALL_AI_RUNTIME_RELEASE.ps1", "Python.Python.3.11")
for token in ["onnxruntime==1.29.0", "torch==2.8.0", "not(Compatible-Python $VenvPy)"]:
    if token not in runtime_install:
        errors.append(f"release runtime installer missing compatibility token: {token}")
if "Python.Python.3.10" in runtime_install or "Python310" in runtime_install:
    errors.append("release runtime installer still targets incompatible Python 3.10")
need("runtime/smoke_runtime_installer_contract_v70.py", "runtime installer compatibility contract PASS")

# Repository / distribution licensing boundaries.
root_license = need("LICENSE", "All rights reserved")
for token in ["integrations/stringcc-governance/", "licenses/THIRD_PARTY_NOTICES.txt", "proprietary"]:
    if token not in root_license:
        errors.append(f"LICENSE missing commercial boundary token: {token}")
need("licenses/THIRD_PARTY_NOTICES.txt")
need("integrations/stringcc-governance/LICENSE", "MIT License")
bridge_readme = need("integrations/stringcc-governance/README.md", "JSON/subprocess boundary")
if "SONICRAFT" not in bridge_readme or "MIT" not in bridge_readme:
    errors.append("StringCC bridge README does not preserve explicit integration/license boundary")
bridge_validation = read_json("integrations/stringcc-governance/VALIDATION_v11.json")
if bridge_validation:
    sonicraft_review = bridge_validation.get("sonicraft_review", {})
    tests = bridge_validation.get("tests", {})
    if sonicraft_review.get("copied_source") is not False:
        errors.append("StringCC validation must record copied_source=false")
    if tests.get("status") != "passed-in-isolated-batches":
        errors.append("StringCC validation record is not passed-in-isolated-batches")

# Historical freeze stays historical; post-freeze integration lineage is explicit.
freeze = read_json("release/SOURCE_FREEZE_v7.0.json")
if freeze:
    if freeze.get("release") != "7.0.0-rc2":
        errors.append("SOURCE_FREEZE_v7.0 release mismatch")
    if freeze.get("status") != "RC2_FRONTEND_LOCK_SOURCE_FROZEN":
        errors.append("SOURCE_FREEZE_v7.0 historical status changed unexpectedly")
    if freeze.get("feature_freeze") is not True:
        errors.append("SOURCE_FREEZE_v7.0 must remain feature frozen")

readiness = read_json("release/commercial_readiness_v7.0_rc2.json")
if readiness:
    if readiness.get("source_commercial_ready") is not True:
        errors.append("commercial readiness must declare source_commercial_ready=true")
    if readiness.get("commercial_binary_approved") is not False:
        errors.append("commercial readiness must not pre-approve the binary")
    if readiness.get("public_release_approved") is not False:
        errors.append("commercial readiness must not pre-approve public release")
    scope = readiness.get("release_scope", {})
    if scope.get("rc2_product_baseline_commit") != "4f9f1915d6179ffb3d669bbb3a483c4e30643fbf":
        errors.append("commercial readiness RC2 product baseline commit mismatch")
    if scope.get("stringcc_bridge_merge_commit") != "5c2f16816d40edaba1e9dcbee7ce43467d0a8f27":
        errors.append("commercial readiness StringCC merge commit mismatch")

front = read_json("release/frontier_status_v7.0.json")
if front:
    if front.get("commercial_binary_approved") is True:
        errors.append("frontier_status_v7.0 incorrectly claims commercial approval before host/acoustic gates")
    if front.get("source_commercial_ready") is not True:
        errors.append("frontier_status_v7.0 must declare source_commercial_ready=true after hardening")

need("docs/COMMERCIAL_RELEASE_READINESS_v7.0_RC2.md", "software-side commercial-release ready")

# Approval markers/evidence are generated externally and must never be fabricated in source.
for rel in [
    "release/rc_evidence/RC_APPROVED.txt",
    "release/rc_evidence/PUBLIC_RELEASE_APPROVED.txt",
]:
    if (ROOT / rel).exists():
        errors.append(f"source tree must not commit generated approval marker: {rel}")

if errors:
    print("SONICRAFT v7.0 RC SOURCE GATE: BLOCKED")
    for error in errors:
        print(" -", error)
    raise SystemExit(2)

print("SONICRAFT v7.0 RC SOURCE GATE: PASS")
print(" Frontend layout/source lock: PASS")
print(" Pinned VST3 SDK 3.8.0 commit contract: PASS")
print(" Fail-closed Validator/Host/Acoustic gate harness: PASS")
print(" Commercial licensing and StringCC separation: PASS")
print(" Software-side commercial readiness: PASS")
print(" Commercial binary approval remains FALSE until external release evidence exists.")
