"""Zero-weight quartet coordination for Assist/Auto rendering.

This module deliberately does not alter written MIDI pitch, note gates, note timing,
velocity, articulation, or explicit user CC curves.  It only coordinates the hidden
bow-change probability used by the neural performance renderer.
"""
from __future__ import annotations
import numpy as np


def _frame(sample: int, start_sample: int, sample_rate: float, fps: int, n: int) -> int:
    return int(max(0, min(n - 1, round((int(sample) - int(start_sample)) / float(sample_rate) * fps))))


def quartet_coordination_curves(events, part: int, start_sample: int, end_sample: int,
                                sample_rate: float, fps: int = 100):
    """Return entry-sync, other-voice density and support-role curves in [0, 1].

    The computation is deterministic and parameter-free. `support_role` is high when
    the current voice is below another active voice, allowing inner/lower parts to
    coordinate attacks more tightly while the current top voice keeps more freedom.
    """
    duration = max(0.08, (int(end_sample) - int(start_sample)) / float(sample_rate))
    n = max(8, int(np.ceil(duration * fps)))
    gate = np.zeros((4, n), np.float32)
    pitch = np.zeros((4, n), np.float32)
    onsets = [[] for _ in range(4)]
    active = [None] * 4

    for e in sorted(events, key=lambda x: int(x.get('project_sample', 0))):
        p = int(e.get('part', -1)); typ = int(e.get('type', 0))
        if p < 0 or p >= 4 or typ not in (1, 2):
            continue
        ps=int(e.get('project_sample', start_sample)); before=ps<int(start_sample)
        idx = _frame(ps, start_sample, sample_rate, fps, n)
        if typ == 1:
            if active[p] is not None:
                a, note = active[p]
                if idx>a: gate[p, a:idx] = 1.0; pitch[p, a:idx] = float(note)
            active[p] = (0 if before else idx, int(e.get('note', 0)))
            if not before: onsets[p].append(idx)
        elif active[p] is not None:
            a, note = active[p]
            b = max(a + 1, idx)
            gate[p, a:b] = 1.0; pitch[p, a:b] = float(note)
            active[p] = None
    for p in range(4):
        if active[p] is not None:
            a, note = active[p]; gate[p, a:] = 1.0; pitch[p, a:] = float(note)

    other_gate = np.delete(gate, int(part), axis=0)
    density = np.clip(other_gate.sum(axis=0) / 3.0, 0.0, 1.0).astype(np.float32)

    entry_sync = np.zeros(n, np.float32)
    radius = max(1, int(round(0.050 * fps)))  # +/- 50 ms musical entry neighborhood
    others = [q for q in range(4) if q != int(part)]
    for idx in onsets[int(part)]:
        hits = 0
        for q in others:
            if any(abs(int(o) - int(idx)) <= radius for o in onsets[q]):
                hits += 1
        score = hits / 3.0
        if score > 0:
            a = max(0, idx - 1); b = min(n, idx + 3)
            entry_sync[a:b] = np.maximum(entry_sync[a:b], score)

    own_pitch = pitch[int(part)]
    other_pitch = np.delete(pitch, int(part), axis=0)
    highest_other = other_pitch.max(axis=0)
    support_role = ((own_pitch > 0) & (highest_other > own_pitch)).astype(np.float32)
    # Smooth only the role/density context; entry sync intentionally stays transient.
    if n >= 5:
        kernel = np.ones(5, np.float32) / 5.0
        density = np.convolve(density, kernel, mode='same').astype(np.float32)
        support_role = np.convolve(support_role, kernel, mode='same').astype(np.float32)
    return entry_sync, density, np.clip(support_role, 0.0, 1.0)


def coordinate_hidden_bow(base_bow, onset, events, part: int, start_sample: int,
                          end_sample: int, sample_rate: float, assist_strength: float,
                          fps: int = 100):
    """Coordinate only hidden bow intent; Manual mode (strength=0) is bit-identical."""
    base = np.asarray(base_bow, dtype=np.float32)
    if float(assist_strength) <= 0.0 or not events:
        return base
    sync, density, support = quartet_coordination_curves(
        events, part, start_sample, end_sample, sample_rate, fps=fps)
    on = np.asarray(onset, dtype=np.float32)
    # Coordinated ensemble entries get a stronger shared re-bow cue. Supporting voices
    # follow the ensemble slightly more tightly; top voice retains expressive freedom.
    delta = on * float(assist_strength) * (
        0.16 * sync * (0.65 + 0.35 * support) + 0.05 * density * support
    )
    return np.clip(base + delta, 0.0, 1.0).astype(np.float32)


def coordinate_hidden_ensemble(base_bow, base_vibrato_onset, gate, onset, events, part: int,
                               start_sample: int, end_sample: int, sample_rate: float,
                               assist_strength: float, fps: int = 100):
    """Coordinate hidden ensemble physics without touching any written/user lane.

    Returns ``(bow_change_prob, vibrato_onset)``. Manual (strength <= 0) is exactly
    identity. Assist/Auto adds two deterministic priors:

    1. shared re-bow intent at ensemble entries (existing v1.6 behavior),
    2. small part/role/density-dependent vibrato-onset staggering so four voices do not
       bloom vibrato at the same instant like a phase-locked ensemble patch.

    No random state and no learned weights are used, so cache determinism is preserved.
    """
    bow=np.asarray(base_bow,dtype=np.float32)
    von=np.asarray(base_vibrato_onset,dtype=np.float32)
    if float(assist_strength)<=0.0 or not events:
        return bow, von
    sync,density,support=quartet_coordination_curves(
        events,part,start_sample,end_sample,sample_rate,fps=fps)
    on=np.asarray(onset,dtype=np.float32)
    gt=np.asarray(gate,dtype=np.float32)
    # Keep the exact v1.6 bow rule so this upgrade is monotonic for existing behavior.
    delta = on * float(assist_strength) * (
        0.16 * sync * (0.65 + 0.35 * support) + 0.05 * density * support
    )
    bow_out=np.clip(bow+delta,0.0,1.0).astype(np.float32)

    # Normalized seconds-like onset prior (0.10 ~= 100 ms in the current control scale).
    # Fixed per-part staggering is intentionally small; density/support add natural spread,
    # while tightly synchronized entries shorten the bloom slightly instead of locking it.
    part_offset=(0.000,0.020,0.045,0.070)[max(0,min(3,int(part)))]
    target=gt*(0.085+part_offset+0.045*density+0.025*support-0.015*sync)
    target=np.clip(target,0.0,0.30).astype(np.float32)
    von_out=np.maximum(von,target*float(assist_strength)).astype(np.float32)
    return bow_out, von_out
