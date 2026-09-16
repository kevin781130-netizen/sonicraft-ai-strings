from __future__ import annotations
"""Build a provenance-rich clean-room bowed-string audio dataset.

Two teacher modes are supported:

* ``internal``: SONICRAFT's independently authored physical bowed-string teacher.
* ``external``: an authorized opaque renderer invoked through
  ``cleanroom_teacher_adapter.py``. External model bytes are never parsed or copied.

The generated score/control material is deterministic and independently authored.
External-teacher rows remain release-blocked unless the teacher config explicitly
records the required rights declarations; the main dataset registry still remains
the final release gate.
"""
import argparse
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any
import hashlib
import json
import os

import mido
import numpy as np
import soundfile as sf

from cleanroom_bowed_synth import (
    ARTICULATIONS,
    BowedControls,
    random_controls,
    synthesize_section,
)
from cleanroom_teacher_adapter import (
    CleanRoomTeacherError,
    ExternalTeacher,
    SPEC_VERSION,
    TeacherConfig,
)
from sound_forge import analyze_audio, sha256_file


BUILDER_VERSION = "cleanroom_teacher_dataset_v1"
INTERNAL_DATASET_ID = "synthetic_cleanroom_bowed_v18"
EXTERNAL_DATASET_ID = "authorized_blackbox_synthetic"
INSTRUMENT_NAMES = ("violin_1", "violin_2", "viola", "cello")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sample_id(seed: int, index: int, controls: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(f"{BUILDER_VERSION}:{seed}:{index}:".encode())
    h.update(_canonical_bytes(controls))
    return h.hexdigest()[:24]


def _split(sample_id: str) -> str:
    n = int(hashlib.sha256(sample_id.encode()).hexdigest()[:8], 16) % 1000
    if n < 900:
        return "train"
    if n < 950:
        return "val"
    return "test"


def _write_midi(ctrl: BowedControls, path: Path, seconds: float, bpm: float = 60.0) -> None:
    """Write an original single-gesture MIDI/control probe for the teacher shim."""
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    tempo = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    # Generic CCs are intentionally ordinary MIDI, not copied proprietary mappings.
    track.append(mido.Message("control_change", control=1, value=int(np.clip(ctrl.bow_speed, 0, 1) * 127), time=0))
    track.append(mido.Message("control_change", control=11, value=int(np.clip(ctrl.velocity, 0, 1) * 127), time=0))
    track.append(mido.Message("control_change", control=74, value=int(np.clip(1.0-ctrl.contact_point, 0, 1) * 127), time=0))
    velocity = int(np.clip(ctrl.velocity, 0, 1) * 100 + 20)
    ticks = max(1, int(round(mido.second2tick(seconds, 480, tempo))))
    note = int(round(ctrl.pitch))
    track.append(mido.Message("note_on", note=note, velocity=min(127, velocity), time=0))
    track.append(mido.Message("note_off", note=note, velocity=0, time=ticks))
    path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(path)


def _coarse_audio_fingerprint(path: Path) -> str:
    """Intra-run duplicate fingerprint; not a copyright detector."""
    x, _ = sf.read(path, dtype="float32", always_2d=True)
    mono = np.asarray(x, np.float32).mean(axis=1)
    if mono.size == 0:
        return "empty"
    mono = mono - float(mono.mean())
    peak = float(np.max(np.abs(mono))) + 1e-9
    mono = mono / peak

    points = 64
    edges = np.linspace(0, mono.size, points + 1).astype(int)
    env = np.asarray(
        [np.sqrt(np.mean(mono[edges[i]:max(edges[i] + 1, edges[i + 1])] ** 2) + 1e-12)
         for i in range(points)],
        np.float32,
    )
    env = env / (float(env.max()) + 1e-9)

    n = min(mono.size, 131072)
    if n < 256:
        spec = np.zeros(points, np.float32)
    else:
        seg = mono[(mono.size - n)//2:(mono.size - n)//2+n]
        nfft = 1 << int(np.floor(np.log2(n)))
        mag = np.log1p(np.abs(np.fft.rfft(seg[:nfft] * np.hanning(nfft))))
        sedges = np.linspace(0, mag.size, points + 1).astype(int)
        spec = np.asarray(
            [np.mean(mag[sedges[i]:max(sedges[i] + 1, sedges[i + 1])])
             for i in range(points)],
            np.float32,
        )
        spec -= float(spec.min())
        spec /= float(spec.max()) + 1e-9

    quantized = np.rint(np.concatenate([env, spec]) * 31.0).astype(np.uint8)
    return hashlib.sha256(quantized.tobytes()).hexdigest()


def _quality_accept(path: Path) -> tuple[bool, dict[str, Any], list[str]]:
    q = analyze_audio(path)
    qd = asdict(q)
    reasons = list(q.reasons)
    accepted = bool(not q.hard_reject and q.score >= 0.45)
    return accepted, qd, reasons


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _base_controls(rng: np.random.Generator, index: int) -> BowedControls:
    # Stratify instruments/articulations before randomizing continuous controls.
    inst = index % 4
    art = (index // 4) % len(ARTICULATIONS)
    ctrl = random_controls(rng, instrument=inst, articulation=art)
    if index % 7 == 0:
        ctrl = replace(
            ctrl,
            section_players=int(rng.choice([2, 3, 4, 6, 8])),
            section_pitch_spread_cents=float(rng.uniform(2.0, 11.0)),
            section_timing_spread_ms=float(rng.uniform(2.0, 18.0)),
            section_bow_spread=float(rng.uniform(0.02, 0.16)),
        )
    return ctrl


def build(
    *,
    out_dir: Path,
    count: int,
    seed: int,
    seconds: float,
    sample_rate: int,
    teacher_config: Path | None,
    dry_run: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = out_dir / "audio"
    control_dir = out_dir / "controls"
    midi_dir = out_dir / "midi"
    accepted_path = out_dir / "index.jsonl"
    rejected_path = out_dir / "rejected.jsonl"
    for p in (accepted_path, rejected_path):
        if p.exists():
            p.unlink()

    rng = np.random.default_rng(seed)
    teacher = None
    teacher_identity: dict[str, Any]
    dataset_id = INTERNAL_DATASET_ID
    release_ready = True

    if teacher_config is not None:
        cfg = TeacherConfig.load(teacher_config)
        teacher = ExternalTeacher(cfg)
        teacher_identity = cfg.public_identity()
        dataset_id = EXTERNAL_DATASET_ID
        release_ready = cfg.rights.release_training_ready
    else:
        teacher_identity = {
            "name": "sonicraft_independent_physical_teacher",
            "spec_version": "SONICRAFT-BOWED-1.0",
            "implementation": "training/cleanroom_bowed_synth.py",
        }

    exact_hashes: set[str] = set()
    coarse_hashes: set[str] = set()
    accepted = rejected = duplicate = render_errors = 0

    for i in range(int(count)):
        ctrl = _base_controls(rng, i)
        manifest = ctrl.manifest()
        manifest["builder_version"] = BUILDER_VERSION
        manifest["probe_index"] = i
        manifest["probe_seed"] = int(seed)
        sid = _sample_id(seed, i, manifest)
        control_path = control_dir / f"{sid}.json"
        midi_path = midi_dir / f"{sid}.mid"
        audio_path = audio_dir / f"{sid}.wav"
        control_path.parent.mkdir(parents=True, exist_ok=True)
        control_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_midi(ctrl, midi_path, seconds)

        base = {
            "schema_version": 1,
            "sample_id": sid,
            "dataset": dataset_id,
            "dataset_id": dataset_id,
            "training_origin": "modeled",
            "source_kind": (
                "authorized_blackbox_synthetic"
                if teacher is not None else "modeled"
            ),
            "split": _split(sid),
            "instrument": int(ctrl.instrument),
            "instrument_name": INSTRUMENT_NAMES[int(ctrl.instrument)],
            "articulation": int(ctrl.articulation),
            "articulation_name": ARTICULATIONS[int(ctrl.articulation)],
            "control_json": str(control_path),
            "control_sha256": sha256_file(control_path),
            "midi": str(midi_path),
            "midi_sha256": sha256_file(midi_path),
            "teacher_mode": "external" if teacher is not None else "internal",
            "teacher_identity": teacher_identity,
            "cleanroom_spec_version": SPEC_VERSION,
            "independently_authored_controls": True,
            "proprietary_model_bytes_embedded": False,
            "release_blocked": bool(teacher is not None and not release_ready),
        }

        if dry_run:
            base["status"] = "dry_run"
            _append_jsonl(rejected_path, base)
            rejected += 1
            continue

        try:
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            if teacher is None:
                y = synthesize_section(
                    ctrl, seconds=seconds, sample_rate=sample_rate, seed=seed + i * 1009
                )
                sf.write(audio_path, y, sample_rate, subtype="FLOAT")
            else:
                teacher.render(
                    control_json=control_path,
                    midi=midi_path,
                    output=audio_path,
                    seed=seed + i * 1009,
                )
        except Exception as exc:
            row = dict(base)
            row.update({
                "status": "render_error",
                "error_type": type(exc).__name__,
                "error": str(exc)[-800:],
            })
            _append_jsonl(rejected_path, row)
            rejected += 1
            render_errors += 1
            continue

        try:
            exact = sha256_file(audio_path)
            coarse = _coarse_audio_fingerprint(audio_path)
            ok, quality, reasons = _quality_accept(audio_path)
        except Exception as exc:
            row = dict(base)
            row.update({
                "audio": str(audio_path),
                "status": "quality_error",
                "error_type": type(exc).__name__,
                "error": str(exc)[-800:],
            })
            _append_jsonl(rejected_path, row)
            rejected += 1
            continue

        dupe_kind = None
        if exact in exact_hashes:
            dupe_kind = "exact"
        elif coarse in coarse_hashes:
            dupe_kind = "coarse_intra_run"
        if dupe_kind:
            row = dict(base)
            row.update({
                "audio": str(audio_path),
                "audio_sha256": exact,
                "audio_coarse_fingerprint": coarse,
                "status": "duplicate",
                "duplicate_kind": dupe_kind,
                "forge_audio": quality,
                "forge_reasons": reasons,
            })
            _append_jsonl(rejected_path, row)
            rejected += 1
            duplicate += 1
            audio_path.unlink(missing_ok=True)
            continue

        exact_hashes.add(exact)
        coarse_hashes.add(coarse)
        row = dict(base)
        row.update({
            "audio": str(audio_path),
            "audio_sha256": exact,
            "audio_coarse_fingerprint": coarse,
            "status": "accepted" if ok else "quality_rejected",
            "forge_quality_score": float(quality["score"]),
            "forge_quality_tier": quality["tier"],
            "forge_audio": quality,
            "forge_reasons": reasons,
            "forge_release_eligible": bool(ok and not base["release_blocked"]),
            "final_timbre_anchor": False,
        })
        if ok:
            _append_jsonl(accepted_path, row)
            accepted += 1
        else:
            _append_jsonl(rejected_path, row)
            rejected += 1

    report = {
        "schema_version": 1,
        "builder_version": BUILDER_VERSION,
        "cleanroom_spec_version": SPEC_VERSION,
        "dataset": dataset_id,
        "teacher_mode": "external" if teacher is not None else "internal",
        "teacher_identity": teacher_identity,
        "requested": int(count),
        "accepted": accepted,
        "rejected": rejected,
        "duplicates": duplicate,
        "render_errors": render_errors,
        "seed": int(seed),
        "seconds": float(seconds),
        "sample_rate": int(sample_rate),
        "release_training_ready_from_teacher_declaration": bool(release_ready),
        "registry_gate_still_required": True,
        "notes": (
            "Coarse fingerprints detect only duplicates within this generated run; "
            "they are not copyright or memorization detectors."
        ),
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/cleanroom_teacher")
    ap.add_argument("--count", type=int, default=256)
    ap.add_argument("--seed", type=int, default=20260917)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample-rate", type=int, default=48000)
    ap.add_argument(
        "--teacher-config",
        help="JSON config for an authorized opaque renderer. Omit to use SONICRAFT's independent physical teacher.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate original controls/MIDI and provenance without rendering audio.",
    )
    args = ap.parse_args()
    if args.count < 1:
        raise SystemExit("--count must be >= 1")
    if args.seconds <= 0:
        raise SystemExit("--seconds must be > 0")
    try:
        report = build(
            out_dir=Path(args.out),
            count=args.count,
            seed=args.seed,
            seconds=args.seconds,
            sample_rate=args.sample_rate,
            teacher_config=(Path(args.teacher_config) if args.teacher_config else None),
            dry_run=args.dry_run,
        )
    except CleanRoomTeacherError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
