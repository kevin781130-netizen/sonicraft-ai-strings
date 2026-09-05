from __future__ import annotations
"""SONICRAFT v1.9 Sound Forge: deterministic, fail-closed dataset intake.

This module intentionally does *not* infer legal permission from a filename, URL,
or license-like string. Commercial eligibility is inherited only from the audited
``dataset_registry.json`` entry. DSP quality scoring then decides whether an
otherwise-cleared recording is suitable for acoustic training.

The Forge never changes the product's REAL80/MODEL20 policy. It only ranks and
filters material *inside* those two lanes.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence
import hashlib
import json
import math

import numpy as np
import soundfile as sf

FORGE_SCHEMA = 1
FORGE_VERSION = "sound_forge_v19"
REAL = "real"
MODELED = "modeled"


def _dataset_id(row: Mapping) -> str:
    return str(row.get("dataset") or row.get("dataset_id") or "unknown").strip().lower()


def _origin(row: Mapping, registry: Mapping) -> str:
    explicit = row.get("training_origin") or row.get("source_kind")
    if explicit is not None:
        s = str(explicit).strip().lower()
        return MODELED if s in {"modeled", "synthetic", "physics", "cleanroom", "physical"} else REAL
    item = registry.get(_dataset_id(row), {})
    s = str(item.get("training_origin", REAL)).strip().lower()
    return MODELED if s in {"modeled", "synthetic", "physics", "cleanroom", "physical"} else REAL


def _audio_path(row: Mapping) -> Path:
    raw = row.get("audio") or row.get("path") or row.get("file")
    if not raw:
        raise ValueError("manifest row has no audio/path/file")
    return Path(raw)


def sha256_file(path: Path, chunk: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _frame_rms(x: np.ndarray, frame: int = 2048, hop: int = 1024) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if x.size == 0:
        return np.zeros(1, np.float32)
    if x.size < frame:
        return np.asarray([float(np.sqrt(np.mean(x * x) + 1e-12))], np.float32)
    count = 1 + (x.size - frame) // hop
    out = np.empty(count, np.float32)
    for i in range(count):
        s = x[i * hop:i * hop + frame]
        out[i] = np.sqrt(np.mean(s * s) + 1e-12)
    return out


def _spectral_ratios(x: np.ndarray, sr: int) -> tuple[float, float, float]:
    """Return sub-40Hz ratio, >18kHz ratio and normalized spectral centroid."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if x.size < 64 or not np.any(x):
        return 0.0, 0.0, 0.0
    n = int(min(x.size, 262144))
    # Evenly spread the inspected window across the clip without loading plugins.
    if x.size > n:
        start = max(0, (x.size - n) // 2)
        x = x[start:start + n]
    # Power-of-two FFT gives stable, dependency-free metrics.
    nfft = 1 << int(math.floor(math.log2(max(64, x.size))))
    x = x[:nfft]
    win = np.hanning(nfft).astype(np.float32)
    p = np.abs(np.fft.rfft(x * win)) ** 2
    f = np.fft.rfftfreq(nfft, 1.0 / float(sr))
    total = float(p.sum()) + 1e-20
    low = float(p[f < 40.0].sum() / total)
    high = float(p[f > 18000.0].sum() / total) if sr > 36000 else 0.0
    centroid = float((p * f).sum() / total / max(1.0, sr * 0.5))
    return low, high, centroid


@dataclass
class AudioQuality:
    sample_rate: int
    channels: int
    duration_sec: float
    peak: float
    rms_dbfs: float
    crest_db: float
    dc_abs: float
    clipping_ratio: float
    silence_frame_ratio: float
    snr_proxy_db: float
    sub40_ratio: float
    over18k_ratio: float
    spectral_centroid_nyquist: float
    score: float
    tier: str
    hard_reject: bool
    reasons: list[str]


def analyze_audio(path: str | Path, *, max_analysis_seconds: float = 30.0) -> AudioQuality:
    path = Path(path)
    info = sf.info(path)
    sr = int(info.samplerate)
    channels = int(info.channels)
    frames = int(info.frames)
    duration = frames / max(1, sr)
    # Read a deterministic leading+middle+trailing sample for long recordings.
    cap = int(max(1.0, max_analysis_seconds) * sr)
    if frames <= cap:
        audio, _ = sf.read(path, dtype="float32", always_2d=True)
    else:
        thirds = cap // 3
        chunks = []
        for st in (0, max(0, frames // 2 - thirds // 2), max(0, frames - thirds)):
            with sf.SoundFile(path) as f:
                f.seek(st)
                chunks.append(f.read(thirds, dtype="float32", always_2d=True))
        audio = np.concatenate(chunks, axis=0)
    mono = np.asarray(audio, np.float32).mean(axis=1) if audio.size else np.zeros(1, np.float32)
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    rms = float(np.sqrt(np.mean(mono * mono) + 1e-12))
    rms_db = float(20.0 * np.log10(max(rms, 1e-12)))
    crest = float(20.0 * np.log10(max(peak, 1e-12) / max(rms, 1e-12)))
    dc = float(abs(np.mean(mono)))
    clipping = float(np.mean(np.abs(mono) >= 0.999))
    fr = _frame_rms(mono)
    fr_db = 20.0 * np.log10(np.maximum(fr, 1e-12))
    silence = float(np.mean(fr_db < -60.0))
    active = fr_db[fr_db > -60.0]
    if active.size >= 4:
        snr_proxy = float(np.percentile(active, 90) - np.percentile(active, 10))
    elif active.size:
        snr_proxy = float(np.max(active) - np.min(active))
    else:
        snr_proxy = 0.0
    low, high, centroid = _spectral_ratios(mono, sr)

    score = 1.0
    reasons: list[str] = []
    hard = False
    if duration < 0.10:
        hard = True; reasons.append("too_short")
    elif duration < 0.35:
        score -= 0.12; reasons.append("short_clip")
    if peak < 1e-5 or rms_db < -75.0:
        hard = True; reasons.append("near_silence")
    elif rms_db < -55.0:
        score -= 0.15; reasons.append("very_low_level")
    if clipping > 0.02:
        hard = True; reasons.append("heavy_clipping")
    elif clipping > 0.001:
        score -= min(0.30, 8.0 * clipping); reasons.append("clipping")
    if dc > 0.05:
        hard = True; reasons.append("large_dc_offset")
    elif dc > 0.01:
        score -= min(0.15, dc * 3.0); reasons.append("dc_offset")
    if silence > 0.995:
        hard = True; reasons.append("mostly_silent")
    elif silence > 0.90:
        score -= 0.12; reasons.append("large_silence_fraction")
    if sr < 44100:
        score -= 0.12; reasons.append("sample_rate_below_44k1")
    # These are soft diagnostics only: bowed strings may legitimately have large
    # dynamics and bright harmonics. They must not become destructive gates.
    if active.size >= 4 and snr_proxy < 8.0:
        score -= 0.08; reasons.append("low_dynamic_separation")
    if low > 0.22:
        score -= 0.06; reasons.append("subsonic_energy")
    if high > 0.32:
        score -= 0.06; reasons.append("ultrasonic_noise_risk")
    score = float(max(0.0, min(1.0, score)))
    if hard or score < 0.45:
        tier = "REJECT"
    elif score >= 0.88:
        tier = "A"
    elif score >= 0.72:
        tier = "B"
    else:
        tier = "C"
    return AudioQuality(sr, channels, duration, peak, rms_db, crest, dc, clipping,
                        silence, snr_proxy, low, high, centroid, score, tier, hard, reasons)


def source_clearance(row: Mapping, registry: Mapping) -> tuple[bool, list[str], dict]:
    sid = _dataset_id(row)
    item = dict(registry.get(sid) or {})
    reasons: list[str] = []
    if not item:
        reasons.append("unknown_dataset")
    else:
        if item.get("release_blocked", True):
            reasons.append("registry_release_blocked")
        if not item.get("commercial_safe", False):
            reasons.append("registry_not_commercial_safe")
        if not item.get("enabled", False):
            # Disabled can mean optional rather than illegal. Fail closed for a
            # production Forge; explicit enablement is a human audit action.
            reasons.append("registry_not_enabled")
    if row.get("release_blocked"):
        reasons.append("row_release_blocked")
    return not reasons, reasons, item


def forge_row(row: Mapping, registry: Mapping, *, hash_audio: bool = True) -> dict:
    out = dict(row)
    sid = _dataset_id(out)
    out["dataset_id"] = sid
    out["training_origin"] = _origin(out, registry)
    clear, rights_reasons, reg_item = source_clearance(out, registry)
    path = _audio_path(out)
    reasons = list(rights_reasons)
    try:
        if not path.is_file():
            raise FileNotFoundError(path)
        q = analyze_audio(path)
        qd = asdict(q)
        reasons += q.reasons
        digest = sha256_file(path) if hash_audio else None
    except Exception as e:
        qd = None
        digest = None
        reasons.append(f"audio_error:{type(e).__name__}")
    eligible = bool(clear and qd and not qd["hard_reject"] and qd["score"] >= 0.45)
    out.update({
        "forge_schema": FORGE_SCHEMA,
        "forge_version": FORGE_VERSION,
        "forge_release_eligible": eligible,
        "forge_quality_score": float(qd["score"]) if qd else 0.0,
        "forge_quality_tier": qd["tier"] if qd else "REJECT",
        "forge_sha256": digest,
        "forge_reasons": reasons,
        "forge_audio": qd,
        "forge_registry_license": reg_item.get("license") if reg_item else None,
        "forge_final_timbre_anchor": bool(reg_item.get("final_timbre_anchor", False)) if reg_item else False,
    })
    # Modeled material can never inherit final-timbre authority even if a row is
    # hand-edited incorrectly.
    if out["training_origin"] == MODELED:
        out["forge_final_timbre_anchor"] = False
    return out


def build_forge(rows: Sequence[Mapping], registry: Mapping, *, hash_audio: bool = True, curriculum: str = 'lane_locked_quality_coverage_forge_v19') -> tuple[list[dict], dict]:
    forged = [forge_row(r, registry, hash_audio=hash_audio) for r in rows]
    seen: dict[str, int] = {}
    duplicates = 0
    for i, r in enumerate(forged):
        dig = r.get("forge_sha256")
        if not dig:
            continue
        if dig in seen:
            duplicates += 1
            r["forge_release_eligible"] = False
            r.setdefault("forge_reasons", []).append(f"duplicate_audio_of_row:{seen[dig]}")
        else:
            seen[dig] = i

    eligible = [r for r in forged if r.get("forge_release_eligible")]
    rejected = [r for r in forged if not r.get("forge_release_eligible")]
    real = [r for r in eligible if r.get("training_origin") == REAL]
    modeled = [r for r in eligible if r.get("training_origin") == MODELED]
    tiers = {k: 0 for k in ("A", "B", "C", "REJECT")}
    sources: dict[str, dict] = {}
    cells: dict[str, int] = {}
    rights_failures = 0
    audio_failures = 0
    for r in forged:
        tiers[str(r.get("forge_quality_tier", "REJECT"))] = tiers.get(str(r.get("forge_quality_tier", "REJECT")), 0) + 1
        sid = _dataset_id(r)
        s = sources.setdefault(sid, {"count": 0, "eligible": 0, "origin": r.get("training_origin")})
        s["count"] += 1; s["eligible"] += int(bool(r.get("forge_release_eligible")))
        rr = r.get("forge_reasons") or []
        if any(str(x).startswith("registry_") or x in ("unknown_dataset", "row_release_blocked") for x in rr):
            rights_failures += 1
        if any(str(x).startswith("audio_error:") for x in rr):
            audio_failures += 1
        if r.get("forge_release_eligible"):
            key = f"{r.get('training_origin')}:i{r.get('instrument',-1)}:a{r.get('articulation',-1)}"
            cells[key] = cells.get(key, 0) + 1
    report = {
        "schema": FORGE_SCHEMA,
        "forge_version": FORGE_VERSION,
        "release_pass": bool(real and modeled and rights_failures == 0 and audio_failures == 0),
        "input_files": len(forged),
        "eligible_files": len(eligible),
        "rejected_files": len(rejected),
        "eligible_real_files": len(real),
        "eligible_modeled_files": len(modeled),
        "duplicate_audio": duplicates,
        "rights_failures": rights_failures,
        "audio_failures": audio_failures,
        "quality_tiers": tiers,
        "sources": sources,
        "coverage_cells": cells,
        "training_policy": {
            "real_probability": 0.80,
            "modeled_probability": 0.20,
            "modeled_timbre_anchor": False,
            "modeled_adversarial_target": False,
            "curriculum": str(curriculum),
            "cleanroom_modeled_only": True,
        },
        "notes": "Forge eligibility is legal+technical intake only. Acoustic superiority still requires held-out blind listening.",
    }
    return forged, report


def read_jsonl(path: str | Path) -> list[dict]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def write_jsonl(path: str | Path, rows: Iterable[Mapping]) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(dict(r), ensure_ascii=False, separators=(",", ":")) + "\n")
