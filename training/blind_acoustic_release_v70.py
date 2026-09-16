from __future__ import annotations

"""Generate hash-bound v7.0 blind-acoustic release evidence from a frozen protocol.

This tool never invents acceptance thresholds. The protocol must be frozen before
scoring and must contain explicit criteria. The resulting evidence is suitable for
runtime/release_gate_v70.py only when the actual study passes every frozen criterion.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PRODUCT = "SONICRAFT AI Strings Q4"
RELEASE = "7.0.0-rc2"
SCHEMA = 1


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def is_pos_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_protocol(protocol: dict, *, allow_template: bool = False) -> list[str]:
    errors: list[str] = []
    if protocol.get("schema") != SCHEMA:
        errors.append("protocol schema must be 1")
    if not str(protocol.get("study_id") or "").strip():
        errors.append("protocol requires study_id")
    for key in ("double_blind", "randomized", "negative_control"):
        if protocol.get(key) is not True:
            errors.append(f"protocol {key} must be true")

    criteria = protocol.get("criteria")
    if not isinstance(criteria, dict):
        return errors + ["protocol requires criteria object"]

    for key in ("min_listeners", "min_total_trials"):
        value = criteria.get(key)
        if value is None and allow_template:
            continue
        if not is_pos_int(value):
            errors.append(f"criteria.{key} must be a positive integer")

    realism = criteria.get("realism") or {}
    if realism.get("metric") != "mean_rating":
        errors.append("criteria.realism.metric must be mean_rating")
    for key in ("scale_min", "scale_max", "min_mean"):
        value = realism.get(key)
        if value is None and allow_template:
            continue
        if not is_number(value):
            errors.append(f"criteria.realism.{key} must be numeric")
    if all(is_number(realism.get(k)) for k in ("scale_min", "scale_max", "min_mean")):
        lo = float(realism["scale_min"])
        hi = float(realism["scale_max"])
        threshold = float(realism["min_mean"])
        if not lo < hi:
            errors.append("realism scale_min must be less than scale_max")
        if not lo <= threshold <= hi:
            errors.append("realism min_mean must fall inside the rating scale")

    for section in ("technique_identity", "negative_control"):
        spec = criteria.get(section) or {}
        if spec.get("metric") != "accuracy":
            errors.append(f"criteria.{section}.metric must be accuracy")
        value = spec.get("min_accuracy")
        if value is None and allow_template:
            continue
        if not is_number(value) or not 0.0 <= float(value) <= 1.0:
            errors.append(f"criteria.{section}.min_accuracy must be between 0 and 1")

    return errors


def validate_trial_plan(plan: dict) -> list[str]:
    errors: list[str] = []
    if plan.get("schema") != 1:
        errors.append("trial plan schema must be 1")
    trials = plan.get("trials")
    if not isinstance(trials, list) or not trials:
        return errors + ["trial plan requires a non-empty trials array"]
    seen: set[str] = set()
    kinds: set[str] = set()
    for i, trial in enumerate(trials):
        if not isinstance(trial, dict):
            errors.append(f"trial {i} must be an object")
            continue
        tid = str(trial.get("trial_id") or "").strip()
        kind = str(trial.get("task") or "").strip()
        if not tid:
            errors.append(f"trial {i} missing trial_id")
        elif tid in seen:
            errors.append(f"duplicate trial_id: {tid}")
        else:
            seen.add(tid)
        if kind not in {"realism", "technique_identity", "negative_control"}:
            errors.append(f"trial {tid or i}: unsupported task {kind!r}")
        else:
            kinds.add(kind)
        if any(k in trial for k in ("source_name", "is_sonicraft", "truth_label")):
            errors.append(f"trial {tid or i}: public trial plan leaks source identity")
    for required in ("realism", "technique_identity", "negative_control"):
        if required not in kinds:
            errors.append(f"trial plan missing {required} trials")
    return errors


def score(protocol: dict, plan: dict, raw: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    criteria = protocol["criteria"]
    trials = {str(t["trial_id"]): t for t in plan["trials"]}
    responses = raw.get("responses")
    if not isinstance(responses, list) or not responses:
        return {}, ["raw results require a non-empty responses array"]

    listeners: set[str] = set()
    realism_values: list[float] = []
    technique = [0, 0]
    negative = [0, 0]
    accepted = 0

    scale_min = float(criteria["realism"]["scale_min"])
    scale_max = float(criteria["realism"]["scale_max"])

    for i, row in enumerate(responses):
        if not isinstance(row, dict):
            errors.append(f"response {i} must be an object")
            continue
        lid = str(row.get("listener_id") or "").strip()
        tid = str(row.get("trial_id") or "").strip()
        if not lid or tid not in trials:
            errors.append(f"response {i} has missing listener_id or unknown trial_id")
            continue
        task = str(trials[tid]["task"])
        listeners.add(lid)
        if task == "realism":
            rating = row.get("rating")
            if not is_number(rating) or not scale_min <= float(rating) <= scale_max:
                errors.append(f"response {i} has invalid realism rating")
                continue
            realism_values.append(float(rating))
        else:
            correct = row.get("correct")
            if not isinstance(correct, bool):
                errors.append(f"response {i} requires boolean correct for {task}")
                continue
            bucket = technique if task == "technique_identity" else negative
            bucket[0] += int(correct)
            bucket[1] += 1
        accepted += 1

    listener_count = len(listeners)
    trial_count = accepted
    realism_mean = sum(realism_values) / len(realism_values) if realism_values else None
    technique_accuracy = technique[0] / technique[1] if technique[1] else None
    negative_accuracy = negative[0] / negative[1] if negative[1] else None

    size_pass = (
        listener_count >= int(criteria["min_listeners"])
        and trial_count >= int(criteria["min_total_trials"])
    )
    realism_pass = realism_mean is not None and realism_mean >= float(criteria["realism"]["min_mean"])
    technique_pass = (
        technique_accuracy is not None
        and technique_accuracy >= float(criteria["technique_identity"]["min_accuracy"])
    )
    negative_pass = (
        negative_accuracy is not None
        and negative_accuracy >= float(criteria["negative_control"]["min_accuracy"])
    )

    results = {
        "sample_size": {
            "status": "PASS" if size_pass else "FAIL",
            "listener_count": listener_count,
            "trial_count": trial_count,
            "min_listeners": criteria["min_listeners"],
            "min_total_trials": criteria["min_total_trials"],
        },
        "realism": {
            "status": "PASS" if realism_pass else "FAIL",
            "mean_rating": realism_mean,
            "rating_count": len(realism_values),
            "min_mean": criteria["realism"]["min_mean"],
            "scale_min": criteria["realism"]["scale_min"],
            "scale_max": criteria["realism"]["scale_max"],
        },
        "technique_identity": {
            "status": "PASS" if technique_pass else "FAIL",
            "accuracy": technique_accuracy,
            "correct": technique[0],
            "trials": technique[1],
            "min_accuracy": criteria["technique_identity"]["min_accuracy"],
        },
        "negative_control": {
            "status": "PASS" if negative_pass else "FAIL",
            "accuracy": negative_accuracy,
            "correct": negative[0],
            "trials": negative[1],
            "min_accuracy": criteria["negative_control"]["min_accuracy"],
        },
    }
    return results, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    vp = sub.add_parser("validate-protocol")
    vp.add_argument("protocol")
    vp.add_argument("--allow-template", action="store_true")

    ep = sub.add_parser("emit-evidence")
    ep.add_argument("--protocol", required=True)
    ep.add_argument("--trial-plan", required=True)
    ep.add_argument("--raw-results", required=True)
    ep.add_argument("--plugin", required=True)
    ep.add_argument("--model-manifest", required=True)
    ep.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.command == "validate-protocol":
        protocol = load_json(Path(args.protocol))
        errors = validate_protocol(protocol, allow_template=args.allow_template)
        if errors:
            for error in errors:
                print(" -", error)
            return 2
        print("blind acoustic protocol contract: PASS")
        return 0

    protocol_path = Path(args.protocol)
    plan_path = Path(args.trial_plan)
    raw_path = Path(args.raw_results)
    plugin_path = Path(args.plugin)
    model_manifest_path = Path(args.model_manifest)
    out_path = Path(args.out)

    for path in (protocol_path, plan_path, raw_path, plugin_path, model_manifest_path):
        if not path.is_file():
            print(f"missing required input: {path}")
            return 2

    protocol = load_json(protocol_path)
    plan = load_json(plan_path)
    raw = load_json(raw_path)
    errors = validate_protocol(protocol)
    errors += validate_trial_plan(plan)
    if errors:
        for error in errors:
            print(" -", error)
        return 2

    results, score_errors = score(protocol, plan, raw)
    if score_errors:
        for error in score_errors:
            print(" -", error)
        return 2

    overall_pass = all(
        (results.get(name) or {}).get("status") == "PASS"
        for name in ("sample_size", "realism", "technique_identity", "negative_control")
    )
    evidence = {
        "schema": 1,
        "product": PRODUCT,
        "release": RELEASE,
        "overall": "PASS" if overall_pass else "FAIL",
        "plugin_sha256": sha256(plugin_path),
        "model_manifest_sha256": sha256(model_manifest_path),
        "protocol_sha256": sha256(protocol_path),
        "trial_plan_sha256": sha256(plan_path),
        "raw_results_sha256": sha256(raw_path),
        "protocol": {
            "study_id": protocol["study_id"],
            "double_blind": True,
            "randomized": True,
            "negative_control": True,
            "listener_count": results["sample_size"]["listener_count"],
            "trial_count": results["sample_size"]["trial_count"],
        },
        "results": results,
        "anti_claim": "Evidence is valid only for the exact hashed protocol, raw results, model manifest, and VST3 binary.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
