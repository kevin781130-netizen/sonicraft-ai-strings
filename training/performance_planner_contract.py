from __future__ import annotations

"""Stable note-level contract for SONICRAFT's symbolic Performance Planner.

The planner is advisory: explicit score/MIDI/keyswitch/CC controls are authoritative
and must override predicted values before controls reach the renderer.
"""

from typing import Any, Iterable

PLANNER_SCHEMA = 1
PLANNER_VERSION = "symbolic_performance_planner_v1"

ARTICULATIONS = (
    "sustain", "legato", "portamento", "expressive_long", "marcato", "staccato",
    "spiccato", "tremolo", "pizzicato", "trill", "harmonic", "flautando",
)
ARTICULATION_TO_ID = {name: i for i, name in enumerate(ARTICULATIONS)}

FEATURE_NAMES = (
    "pitch_norm",
    "duration_beats_norm",
    "velocity",
    "tempo_norm",
    "beat_phase",
    "bar_position",
    "phrase_position",
    "prev_interval_norm",
    "next_interval_norm",
    "gap_before_norm",
    "gap_after_norm",
    "instrument_norm",
    "phrase_start",
    "phrase_end",
)

# Physical/control-space values emitted by the planner. Training normalizes each
# range to [0, 1]; speed_profile is still represented in its renderer range [-1,1]
# after decoding.
CONTINUOUS_RANGES = {
    "dynamics": (0.0, 1.0),
    "expression": (0.0, 1.0),
    "legato": (0.0, 1.0),
    "bow_change_prob": (0.0, 1.0),
    "transition_speed": (0.0, 1.0),
    "short_tightness": (0.0, 1.0),
    "attack_character": (0.0, 1.0),
    "vibrato_onset": (0.0, 1.0),
    "vibrato_depth_cents": (0.0, 60.0),
    "vibrato_rate_hz": (3.0, 8.0),
    "vibrato_jitter": (0.0, 0.20),
    "transition_target_ms": (20.0, 300.0),
    "speed_profile": (-1.0, 1.0),
}
CONTINUOUS_TARGETS = tuple(CONTINUOUS_RANGES)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(value)))


def normalize_control(name: str, value: float) -> float:
    lo, hi = CONTINUOUS_RANGES[name]
    if hi <= lo:
        raise ValueError(f"invalid range for {name}")
    return (clamp(value, lo, hi) - lo) / (hi - lo)


def denormalize_control(name: str, value: float) -> float:
    lo, hi = CONTINUOUS_RANGES[name]
    return lo + clamp(value, 0.0, 1.0) * (hi - lo)


def articulation_id(value: Any) -> int:
    if isinstance(value, str):
        key = value.strip().lower()
        if key not in ARTICULATION_TO_ID:
            raise ValueError(f"unknown articulation: {value}")
        return ARTICULATION_TO_ID[key]
    out = int(value)
    if not 0 <= out < len(ARTICULATIONS):
        raise ValueError(f"articulation id out of range: {out}")
    return out


def _velocity(value: Any) -> float:
    x = float(value if value is not None else 0.7)
    if x > 1.0:
        x /= 127.0
    return clamp(x, 0.0, 1.0)


def note_timing(note: dict[str, Any], bpm: float) -> tuple[float, float]:
    """Return (start_beats, duration_beats) from beat- or second-based note data."""
    bpm = max(1e-6, float(bpm))
    if "start_beats" in note:
        start = float(note["start_beats"])
    else:
        start = float(note.get("start_sec", 0.0)) * bpm / 60.0
    if "duration_beats" in note:
        duration = float(note["duration_beats"])
    else:
        duration = float(note.get("duration_sec", 0.25)) * bpm / 60.0
    return max(0.0, start), max(1e-4, duration)


def build_note_features(
    notes: Iterable[dict[str, Any]],
    *,
    bpm: float = 68.0,
    instrument: int = 0,
    beats_per_bar: float = 4.0,
) -> list[list[float]]:
    """Build deterministic symbolic features without looking at audio."""
    seq = list(notes)
    if not seq:
        raise ValueError("performance planner requires at least one note")
    inst = int(instrument)
    if not 0 <= inst <= 3:
        raise ValueError("instrument must be 0..3 (violin I, violin II, viola, cello)")
    bpm = float(bpm)
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    beats_per_bar = max(1.0, float(beats_per_bar))

    timing = [note_timing(n, bpm) for n in seq]
    pitches = [float(n["pitch"]) for n in seq]
    starts = [x[0] for x in timing]
    durations = [x[1] for x in timing]
    phrase_end = max(starts[i] + durations[i] for i in range(len(seq)))

    features: list[list[float]] = []
    for i, note in enumerate(seq):
        pitch = pitches[i]
        start = starts[i]
        dur = durations[i]
        prev_pitch = pitches[i - 1] if i else pitch
        next_pitch = pitches[i + 1] if i + 1 < len(seq) else pitch
        prev_end = starts[i - 1] + durations[i - 1] if i else start
        next_start = starts[i + 1] if i + 1 < len(seq) else start + dur
        gap_before = max(0.0, start - prev_end)
        gap_after = max(0.0, next_start - (start + dur))
        center = start + 0.5 * dur
        vec = [
            clamp((pitch - 36.0) / 60.0, 0.0, 1.0),
            clamp(dur / 4.0, 0.0, 1.0),
            _velocity(note.get("velocity", 0.7)),
            clamp((bpm - 40.0) / 160.0, 0.0, 1.0),
            (start % 1.0),
            ((start % beats_per_bar) / beats_per_bar),
            clamp(center / max(phrase_end, 1e-6), 0.0, 1.0),
            clamp((pitch - prev_pitch + 12.0) / 24.0, 0.0, 1.0),
            clamp((next_pitch - pitch + 12.0) / 24.0, 0.0, 1.0),
            clamp(gap_before / 2.0, 0.0, 1.0),
            clamp(gap_after / 2.0, 0.0, 1.0),
            inst / 3.0,
            1.0 if i == 0 else 0.0,
            1.0 if i + 1 == len(seq) else 0.0,
        ]
        features.append(vec)
    return features


def prediction_record(articulation: Any, controls: dict[str, Any]) -> dict[str, Any]:
    art = articulation_id(articulation)
    out = {
        "articulation": art,
        "articulation_name": ARTICULATIONS[art],
    }
    for name in CONTINUOUS_TARGETS:
        if name in controls:
            lo, hi = CONTINUOUS_RANGES[name]
            out[name] = clamp(float(controls[name]), lo, hi)
    return out


def merge_authoritative_controls(
    predicted: dict[str, Any],
    written_controls: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Merge planner output with explicit written controls.

    Any key explicitly present in `written_controls` wins. This is the central
    authority rule: a planner may fill missing expression, but never rewrites a
    user's keyswitch/CC/score instruction.
    """
    merged = dict(predicted)
    source = {k: "planner" for k in merged}
    written = dict(written_controls or {})
    if "articulation_name" in written and "articulation" not in written:
        written["articulation"] = written["articulation_name"]
    if "articulation" in written:
        art = articulation_id(written["articulation"])
        merged["articulation"] = art
        merged["articulation_name"] = ARTICULATIONS[art]
        source["articulation"] = "written"
        source["articulation_name"] = "written"
    for name in CONTINUOUS_TARGETS:
        if name in written:
            lo, hi = CONTINUOUS_RANGES[name]
            merged[name] = clamp(float(written[name]), lo, hi)
            source[name] = "written"
    return merged, source


def validate_plan(plan: dict[str, Any]) -> None:
    if int(plan.get("schema_version", 0)) != PLANNER_SCHEMA:
        raise ValueError("unsupported performance plan schema")
    notes = plan.get("notes")
    if not isinstance(notes, list) or not notes:
        raise ValueError("performance plan must contain notes")
    for i, note in enumerate(notes):
        if not isinstance(note, dict):
            raise ValueError(f"note {i} is not an object")
        if "pitch" not in note:
            raise ValueError(f"note {i} missing pitch")
        controls = note.get("controls")
        if not isinstance(controls, dict):
            raise ValueError(f"note {i} missing controls")
        articulation_id(controls.get("articulation", controls.get("articulation_name", 0)))
        for name, value in controls.items():
            if name in CONTINUOUS_RANGES:
                lo, hi = CONTINUOUS_RANGES[name]
                x = float(value)
                if x < lo - 1e-6 or x > hi + 1e-6:
                    raise ValueError(f"note {i} {name} out of range: {x}")
