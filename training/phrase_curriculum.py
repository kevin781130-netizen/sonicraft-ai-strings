from __future__ import annotations
"""Phrase-aware curriculum helpers that preserve the REAL/MODELED lane lock.

The renderer's existing sampler owns the global 80/20 REAL/MODELED policy.  This
module only changes *relative* weights inside the modeled lane so clean-room
multi-note phrases can teach transitions without gaining extra timbre authority.
"""
from collections import defaultdict
from typing import Mapping, Sequence

from string_source_mixer import MODELED, build_curriculum_weights, source_origin

PHRASE_CURRICULUM_VERSION = "cleanroom_phrase_lane_v1"


def is_phrase_row(row: Mapping) -> bool:
    return bool(str(row.get("phrase_family") or "").strip())


def with_phrase_lane_weights(
    rows: Sequence[Mapping],
    registry: Mapping | None = None,
    *,
    target_modeled_phrase_share: float = 0.65,
) -> list[dict]:
    """Return copied rows with source_weight adjusted only inside MODELED.

    ``target_modeled_phrase_share`` is a target *within* the modeled lane, never
    a share of total sampling probability.  The normal string_source_mixer then
    renormalizes the modeled lane back to its configured mass (normally 20%).
    """
    target = float(target_modeled_phrase_share)
    if not 0.0 < target <= 1.0:
        raise ValueError("target_modeled_phrase_share must be in (0, 1]")
    out = [dict(r) for r in rows]
    phrase = [i for i, r in enumerate(out) if source_origin(r, registry) == MODELED and is_phrase_row(r)]
    other = [i for i, r in enumerate(out) if source_origin(r, registry) == MODELED and not is_phrase_row(r)]
    if not phrase:
        raise RuntimeError("phrase curriculum requested but no modeled phrase rows were found")

    # Equal base weight for non-phrase modeled rows; solve the phrase multiplier
    # so phrase rows own the requested modeled-lane mass before coverage shaping.
    if other and target < 1.0:
        phrase_weight = target * len(other) / ((1.0 - target) * len(phrase))
    else:
        phrase_weight = 1.0
    phrase_weight = max(1e-6, float(phrase_weight))

    for i in other:
        out[i]["source_weight"] = 1.0
        out[i]["phrase_curriculum_multiplier"] = 1.0
        out[i]["phrase_curriculum_version"] = PHRASE_CURRICULUM_VERSION
    for i in phrase:
        out[i]["source_weight"] = phrase_weight
        out[i]["phrase_curriculum_multiplier"] = phrase_weight
        out[i]["phrase_curriculum_version"] = PHRASE_CURRICULUM_VERSION
    return out


def phrase_probability_audit(
    rows: Sequence[Mapping],
    weights: Sequence[float],
    registry: Mapping | None = None,
) -> dict:
    if len(rows) != len(weights):
        raise ValueError("rows/weights mismatch")
    total = float(sum(weights)) or 1.0
    modeled = phrase = 0.0
    by_family: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for row, weight in zip(rows, weights):
        w = float(weight) / total
        if source_origin(row, registry) != MODELED:
            continue
        modeled += w
        family = str(row.get("phrase_family") or "").strip()
        if family:
            phrase += w
            by_family[family] += w
            counts[family] += 1
    return {
        "curriculum_version": PHRASE_CURRICULUM_VERSION,
        "modeled_probability": modeled,
        "phrase_probability_total": phrase,
        "phrase_share_within_modeled": phrase / modeled if modeled > 0 else 0.0,
        "by_family_probability": dict(sorted(by_family.items())),
        "by_family_count": dict(sorted(counts.items())),
    }


def curriculum_sweep_audit(
    rows: Sequence[Mapping],
    registry: Mapping | None = None,
    *,
    real_ratio: float = 0.80,
    modeled_ratio: float = 0.20,
) -> dict:
    out = {}
    for p in (0.0, 0.5, 1.0):
        weights = build_curriculum_weights(
            rows, registry, real_ratio, modeled_ratio, progress=p, require_modeled=True
        )
        out[str(p)] = phrase_probability_audit(rows, weights, registry)
    return out
