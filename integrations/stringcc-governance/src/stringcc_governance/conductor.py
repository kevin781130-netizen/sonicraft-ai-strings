from __future__ import annotations
from typing import Any
from .models import CandidateProposal, ConductorIntent

_BOUNDS = {
    "apex_position": (0.12, 0.88),
    "intensity_scale": (0.68, 1.34),
    "cc1_gain_scale": (0.78, 1.28),
    "cc11_micro_scale": (0.72, 1.36),
    "vibrato_depth_scale": (0.55, 1.48),
    "bow_pressure_scale": (0.76, 1.30),
    "bow_speed_scale": (0.76, 1.30),
    "pre_roll_scale": (0.72, 1.34),
}


def _clamp(name: str, value: float) -> float:
    lo, hi = _BOUNDS[name]
    return max(lo, min(hi, float(value)))


def _base(base: dict[str, Any]) -> dict[str, float]:
    defaults = {
        "apex_position": 0.58,
        "intensity_scale": 1.0,
        "cc1_gain_scale": 1.0,
        "cc11_micro_scale": 1.0,
        "vibrato_depth_scale": 1.0,
        "bow_pressure_scale": 1.0,
        "bow_speed_scale": 1.0,
        "pre_roll_scale": 1.0,
    }
    for k in defaults:
        if k in base:
            defaults[k] = _clamp(k, float(base[k]))
    return defaults


class ConductorSteerer:
    """Generate bounded, interpretable candidate families from a global intent.

    This is a clean-room implementation: candidate families are generic StringCC
    transformations and do not copy Sonicraft code or constants.
    """

    def propose(
        self,
        phrase_key: str,
        base_overrides: dict[str, Any],
        intent: ConductorIntent,
        phrase_features: dict[str, Any] | None = None,
    ) -> list[CandidateProposal]:
        i = intent.clamped(); f = phrase_features or {}; b = _base(base_overrides)
        density = max(0.0, min(1.0, float(f.get("density_norm", f.get("density", 0.5)))))
        cadence = bool(f.get("cadence", False)) or i.section_role == "cadence"
        lead = i.section_role == "lead"
        transition = i.section_role == "transition"

        proposals: list[CandidateProposal] = []

        # 1. Macro phrase shape / apex.
        shape = dict(b)
        apex_shift = (i.tension - 0.5) * 0.18 + (0.04 if transition else 0.0) - (0.05 if cadence else 0.0)
        shape["apex_position"] = _clamp("apex_position", b["apex_position"] + apex_shift)
        shape["cc1_gain_scale"] = _clamp("cc1_gain_scale", b["cc1_gain_scale"] * (0.93 + 0.22 * i.contrast))
        proposals.append(CandidateProposal(phrase_key, "shape", shape,
            "Move the phrase apex and macro-dynamic span toward the conductor trajectory.",
            ["apex_position", "cc1_gain_scale"], metadata={"intent_role": i.section_role}))

        # 2. Energy / bow drive.
        energy = dict(b)
        drive = (i.energy - 0.5) * 0.36
        energy["intensity_scale"] = _clamp("intensity_scale", b["intensity_scale"] * (1.0 + drive))
        energy["bow_speed_scale"] = _clamp("bow_speed_scale", b["bow_speed_scale"] * (1.0 + drive * 0.55))
        energy["bow_pressure_scale"] = _clamp("bow_pressure_scale", b["bow_pressure_scale"] * (0.96 + 0.20 * i.bow_weight))
        proposals.append(CandidateProposal(phrase_key, "energy", energy,
            "Adjust phrase energy through intensity, bow speed, and bow weight.",
            ["intensity_scale", "bow_speed_scale", "bow_pressure_scale"]))

        # 3. Connection / micro-expression.
        connect = dict(b)
        connect["cc11_micro_scale"] = _clamp("cc11_micro_scale", b["cc11_micro_scale"] * (0.88 + 0.28 * i.continuity))
        connect["pre_roll_scale"] = _clamp("pre_roll_scale", b["pre_roll_scale"] * (0.90 + 0.20 * i.continuity))
        # Dense passages get slightly less vibrato modulation than exposed lead lines.
        vib_target = 0.86 + 0.34 * i.vibrato_character + (0.10 if lead else 0.0) - 0.12 * density
        connect["vibrato_depth_scale"] = _clamp("vibrato_depth_scale", b["vibrato_depth_scale"] * vib_target)
        proposals.append(CandidateProposal(phrase_key, "connection", connect,
            "Shape connection, preparation, and vibrato character without changing the macro arc.",
            ["cc11_micro_scale", "pre_roll_scale", "vibrato_depth_scale"]))

        # 4. Restraint candidate deliberately reduces degrees of freedom. This is useful
        # when the external audio judge reports over-expression or unstable repairs.
        restrained = dict(b)
        r = i.restraint
        restrained["cc1_gain_scale"] = _clamp("cc1_gain_scale", 1.0 + (b["cc1_gain_scale"] - 1.0) * (0.72 - 0.25 * r))
        restrained["cc11_micro_scale"] = _clamp("cc11_micro_scale", 1.0 + (b["cc11_micro_scale"] - 1.0) * (0.68 - 0.20 * r))
        restrained["vibrato_depth_scale"] = _clamp("vibrato_depth_scale", 1.0 + (b["vibrato_depth_scale"] - 1.0) * (0.72 - 0.22 * r))
        proposals.append(CandidateProposal(phrase_key, "restraint", restrained,
            "Reduce overfitting and over-expression while preserving the current phrase identity.",
            ["cc1_gain_scale", "cc11_micro_scale", "vibrato_depth_scale"]))

        return proposals
