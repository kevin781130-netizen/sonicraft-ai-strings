#!/usr/bin/env python3
from __future__ import annotations

"""Apply a trained symbolic Performance Planner to notes and export renderer controls."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.performance_planner import SymbolicPerformancePlanner
from performance_planner_contract import (
    ARTICULATIONS,
    CONTINUOUS_TARGETS,
    FEATURE_NAMES,
    PLANNER_SCHEMA,
    PLANNER_VERSION,
    build_note_features,
    denormalize_control,
    merge_authoritative_controls,
    note_timing,
    prediction_record,
    validate_plan,
)

FPS = 100


def load_symbolic_input(path: Path) -> tuple[list[dict], float, int, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    notes = data.get("notes")
    if notes is None and "events" in data:
        notes = data["events"]
    if not isinstance(notes, list) or not notes:
        raise RuntimeError("symbolic input requires a non-empty notes (or events) array")
    bpm = float(data.get("tempo_bpm", data.get("bpm", 68.0)))
    instrument = int(data.get("instrument", 0))
    beats_per_bar = float(data.get("beats_per_bar", 4.0))
    return notes, bpm, instrument, beats_per_bar


def load_planner(path: Path, device: str):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    if int(ck.get("schema_version", 0)) != PLANNER_SCHEMA or ck.get("planner_version") != PLANNER_VERSION:
        raise RuntimeError("unsupported Performance Planner checkpoint")
    if tuple(ck.get("feature_names", ())) != FEATURE_NAMES:
        raise RuntimeError("Performance Planner feature contract mismatch")
    if tuple(ck.get("continuous_targets", ())) != CONTINUOUS_TARGETS:
        raise RuntimeError("Performance Planner target contract mismatch")
    model = SymbolicPerformancePlanner(**ck["config"])
    model.load_state_dict(ck["model"], strict=True)
    model.to(device).eval()
    return model, ck


def apply_planner(model, notes: list[dict], bpm: float, instrument: int, beats_per_bar: float, device: str) -> list[dict]:
    features = torch.tensor(
        build_note_features(notes, bpm=bpm, instrument=instrument, beats_per_bar=beats_per_bar),
        dtype=torch.float32,
        device=device,
    )[None]
    with torch.no_grad():
        out = model(features)
        probs = torch.softmax(out["articulation_logits"], dim=-1)[0].cpu()
        continuous = out["continuous"][0].cpu()
    planned: list[dict] = []
    for i, note in enumerate(notes):
        art = int(probs[i].argmax().item())
        values = {
            name: denormalize_control(name, float(continuous[i, j]))
            for j, name in enumerate(CONTINUOUS_TARGETS)
        }
        predicted = prediction_record(art, values)
        written = note.get("written_controls")
        if written is not None and not isinstance(written, dict):
            raise RuntimeError(f"note {i} written_controls must be an object")
        merged, source = merge_authoritative_controls(predicted, written)
        planned.append({
            "pitch": float(note["pitch"]),
            **({"start_beats": float(note["start_beats"])} if "start_beats" in note else {}),
            **({"duration_beats": float(note["duration_beats"])} if "duration_beats" in note else {}),
            **({"start_sec": float(note["start_sec"])} if "start_sec" in note else {}),
            **({"duration_sec": float(note["duration_sec"])} if "duration_sec" in note else {}),
            "velocity": float(note.get("velocity", 0.7)),
            "controls": merged,
            "control_source": source,
            "planner_articulation_confidence": float(probs[i, art]),
        })
    return planned


def plan_to_curves(plan: dict) -> dict[str, np.ndarray]:
    notes = plan["notes"]
    bpm = float(plan["tempo_bpm"])
    timing = [note_timing(n, bpm) for n in notes]
    total_beats = max(timing[i][0] + timing[i][1] for i in range(len(notes)))
    total_sec = max(0.05, total_beats * 60.0 / bpm)
    frames = max(2, int(round(total_sec * FPS)))
    t = np.arange(frames, dtype=np.float32) / FPS
    z = lambda v=0.0: np.full(frames, float(v), dtype=np.float32)
    c = {
        "pitch": z(), "gate": z(), "onset": z(), "velocity": z(), "dynamics": z(.7),
        "vibrato": z(), "expression": z(.7), "legato": z(), "pitchbend": z(),
        "transition_speed": z(.5), "short_tightness": z(.45), "attack_character": z(.38),
        "note_progress": z(), "phrase_position": np.clip(t / total_sec, 0, 1).astype(np.float32),
        "prev_interval": z(.5), "next_interval": z(.5), "bow_change_prob": z(.25),
        "vibrato_onset": z(), "tempo_bpm": z(bpm), "seconds_per_beat": z(60.0 / bpm),
        "note_duration_beats": z(), "transition_target_ms": z(80), "speed_profile": z(),
        "vibrato_depth_cents": z(), "vibrato_rate_hz": z(5.2), "vibrato_onset_ms": z(),
        "vibrato_jitter": z(.03), "dynamics_known": z(1), "vibrato_known": z(1),
        "vibrato_physics_known": z(1), "expression_known": z(1), "legato_known": z(1),
        "pitchbend_known": z(), "timing_known": z(1), "articulation_known": z(1),
        "articulation_curve": z(),
    }
    pitches = [float(n["pitch"]) for n in notes]
    for i, note in enumerate(notes):
        start_beats, duration_beats = timing[i]
        start_sec = start_beats * 60.0 / bpm
        duration_sec = duration_beats * 60.0 / bpm
        a = max(0, int(round(start_sec * FPS)))
        b = min(frames, max(a + 1, int(round((start_sec + duration_sec) * FPS))))
        if a >= frames:
            continue
        ctrl = note["controls"]
        art = int(ctrl["articulation"])
        pitch = pitches[i]
        velocity = float(note.get("velocity", .7))
        if velocity > 1:
            velocity /= 127.0
        c["gate"][a:b] = 1
        c["pitch"][a:b] = pitch
        c["velocity"][a:b] = np.clip(velocity, 0, 1)
        c["onset"][a:min(frames, a + 2)] = 1
        c["articulation_curve"][a:b] = art
        c["note_duration_beats"][a:b] = duration_beats
        c["note_progress"][a:b] = np.linspace(0, 1, b - a, dtype=np.float32)
        for name in CONTINUOUS_TARGETS:
            if name in c and name in ctrl:
                c[name][a:b] = float(ctrl[name])
        c["vibrato"][a:b] = np.clip(float(ctrl["vibrato_depth_cents"]) / 60.0, 0, 1)
        c["vibrato_onset_ms"][a:b] = float(ctrl["vibrato_onset"]) * 1000.0
        prev_pitch = pitches[i - 1] if i else pitch
        next_pitch = pitches[i + 1] if i + 1 < len(pitches) else pitch
        c["prev_interval"][a:b] = np.clip((pitch - prev_pitch + 12.0) / 24.0, 0, 1)
        c["next_interval"][a:b] = np.clip((next_pitch - pitch + 12.0) / 24.0, 0, 1)
        if ARTICULATIONS[art] == "portamento" and i > 0 and b - a >= 2:
            transition_frames = int(round(float(ctrl["transition_target_ms"]) / 1000.0 * FPS))
            transition_frames = max(2, min(b - a, transition_frames))
            actual = np.full(b - a, pitch, dtype=np.float32)
            actual[:transition_frames] = np.linspace(prev_pitch, pitch, transition_frames, dtype=np.float32)
            c["pitchbend"][a:b] = (actual - pitch) / 12.0
            c["pitchbend_known"][a:b] = 1.0

    active = np.flatnonzero(c["gate"] > .5)
    if active.size:
        first, last = int(active[0]), int(active[-1])
        c["pitch"][:first] = c["pitch"][first]
        c["pitch"][last + 1:] = c["pitch"][last]
        for i in range(first + 1, last + 1):
            if c["gate"][i] < .5 and c["pitch"][i] == 0:
                c["pitch"][i] = c["pitch"][i - 1]
    return c


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply SONICRAFT's symbolic Performance Planner.")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--input", required=True, help="JSON with tempo_bpm/instrument/notes; notes may contain written_controls.")
    ap.add_argument("--out", required=True, help="Output performance-plan JSON.")
    ap.add_argument("--control-curves-out", help="Optional renderer-compatible 100-Hz NPZ sidecar.")
    ap.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = ap.parse_args()
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but CUDA is unavailable")
    notes, bpm, instrument, beats_per_bar = load_symbolic_input(Path(args.input))
    model, ck = load_planner(Path(args.checkpoint), device)
    planned = apply_planner(model, notes, bpm, instrument, beats_per_bar, device)
    plan = {
        "schema_version": PLANNER_SCHEMA,
        "planner_version": PLANNER_VERSION,
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "source_index_sha256": ck.get("source_index_sha256"),
        "tempo_bpm": bpm,
        "instrument": instrument,
        "beats_per_bar": beats_per_bar,
        "authority_policy": "explicit_written_controls_override_planner",
        "notes": planned,
    }
    validate_plan(plan)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.control_curves_out:
        cp = Path(args.control_curves_out)
        cp.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cp, **plan_to_curves(plan))
    print(json.dumps({"out": str(out), "notes": len(planned), "device": device}, indent=2))


if __name__ == "__main__":
    main()
