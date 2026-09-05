from __future__ import annotations
"""Origin-aware sampling for SONICRAFT string training.

The release rule is intentionally stronger than a raw 80/20 file count:
80% of sampling probability belongs to rights-cleared REAL strings, while at
most 20% belongs to SONICRAFT/permissive physical-model data. Within each lane
we retain source-quality weights so the best real recordings remain the timbre
anchor.
"""
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import math

REAL = "real"
MODELED = "modeled"

CURRICULUM_V19 = "lane_locked_quality_coverage_forge_v19"

DEFAULT_SOURCE_QUALITY = {
    "custom_owned_session": 14.0,
    "iowa_mis": 4.0,
    "good_sounds_cora_2025": 5.5,
    "tinysol": 1.0,
    "ghent_ar_violin_2023": 1.75,
    "sanidha": 1.25,
    "sorbonne_violin_acoustics_2025": .75,
    "synthetic_cleanroom_bowed_v18": 1.0,
}


def load_registry(path: str | Path | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_id(row: Mapping) -> str:
    return str(row.get("dataset") or row.get("dataset_id") or "unknown").strip().lower()


def source_origin(row: Mapping, registry: Mapping | None = None) -> str:
    explicit = row.get("training_origin") or row.get("source_kind") or row.get("model_origin")
    if explicit:
        v = str(explicit).strip().lower()
        if v in {MODELED, "synthetic", "physics", "physical", "cleanroom"}:
            return MODELED
        return REAL
    sid = source_id(row)
    item = (registry or {}).get(sid, {})
    v = str(item.get("training_origin", REAL)).strip().lower()
    return MODELED if v in {MODELED, "synthetic", "physics", "physical", "cleanroom"} else REAL


def source_quality(row: Mapping, registry: Mapping | None = None, base_weights: Mapping | None = None) -> float:
    sid = source_id(row)
    item = (registry or {}).get(sid, {})
    if row.get("source_weight") is not None:
        base = max(1e-8, float(row["source_weight"]))
    elif item.get("source_weight") is not None:
        base = max(1e-8, float(item["source_weight"]))
    else:
        weights = dict(DEFAULT_SOURCE_QUALITY)
        if base_weights:
            weights.update({str(k).lower(): float(v) for k, v in base_weights.items()})
        base = max(1e-8, float(weights.get(sid, 1.0)))
    # v1.9 Sound Forge quality is a lane-internal multiplier only. Missing Forge
    # metadata preserves v1.8 behavior for backwards-compatible experiments.
    if row.get("forge_quality_score") is not None:
        try:
            q=max(0.0,min(1.0,float(row["forge_quality_score"])))
            if row.get("forge_release_eligible") is False: q=0.0
            base *= max(1e-4, 0.45 + 0.55*q)
        except (TypeError,ValueError):
            pass
    return max(1e-8, base)


def build_mixture_weights(
    rows: Sequence[Mapping],
    registry: Mapping | None = None,
    real_ratio: float = .80,
    modeled_ratio: float = .20,
    base_weights: Mapping | None = None,
    require_modeled: bool = False,
) -> list[float]:
    if not rows:
        return []
    if real_ratio < 0 or modeled_ratio < 0 or real_ratio + modeled_ratio <= 0:
        raise ValueError("invalid real/modeled mixture")
    origins = [source_origin(r, registry) for r in rows]
    quality = [source_quality(r, registry, base_weights) for r in rows]
    groups = {REAL: [], MODELED: []}
    for i, origin in enumerate(origins):
        groups[origin].append(i)
    if not groups[REAL]:
        raise RuntimeError("80/20 string training requires at least one rights-cleared real row")
    if require_modeled and not groups[MODELED]:
        raise RuntimeError("modeled lane required but no modeled rows were found")

    active = {REAL: float(real_ratio), MODELED: float(modeled_ratio) if groups[MODELED] else 0.0}
    if active[MODELED] == 0:
        active[REAL] = 1.0
    else:
        norm = active[REAL] + active[MODELED]
        active = {k: v / norm for k, v in active.items()}

    out = [0.0] * len(rows)
    for origin, idxs in groups.items():
        if not idxs or active[origin] <= 0:
            continue
        denom = sum(quality[i] for i in idxs)
        for i in idxs:
            out[i] = active[origin] * quality[i] / max(denom, 1e-12)
    return out



def _scalar_tag(row: Mapping, name: str, default=-1):
    """Best-effort scalar metadata lookup without making training depend on it.

    Renderer indexes commonly keep instrument/articulation inside the latent NPZ.
    We read those scalars once when building the curriculum so rare-technique
    balancing works even when the JSONL row only stores ``file`` + ``dataset``.
    """
    if row.get(name) is not None:
        try: return int(row[name])
        except (TypeError, ValueError): return default
    f=row.get("file")
    if f:
        try:
            import numpy as np
            with np.load(f, allow_pickle=False) as d:
                if name in d.files:
                    v=d[name]
                    return int(v.item() if getattr(v,"ndim",0)==0 else v.reshape(-1)[0])
        except Exception:
            pass
    return default


def hydrate_sampling_metadata(rows: Sequence[Mapping]) -> list[dict]:
    out=[]
    for row in rows:
        r=dict(row)
        if r.get("instrument") is None: r["instrument"]=_scalar_tag(r,"instrument",-1)
        if r.get("articulation") is None: r["articulation"]=_scalar_tag(r,"articulation",-1)
        out.append(r)
    return out


def build_curriculum_weights(
    rows: Sequence[Mapping],
    registry: Mapping | None = None,
    real_ratio: float = .80,
    modeled_ratio: float = .20,
    *,
    progress: float = 0.0,
    base_weights: Mapping | None = None,
    require_modeled: bool = False,
) -> list[float]:
    """80/20 lane-locked Forge quality + rare-technique curriculum.

    Lane probability is *always* normalized back to the requested REAL/MODELED
    mass.  Early training emphasizes instrument/articulation coverage; late
    training increases trust in source quality so owned/pro recordings become
    the final acoustic anchor.  This changes curriculum *inside* each lane and
    can therefore never turn 80/20 into an accidental dataset-size ratio.
    """
    if not rows: return []
    p=float(min(1.0,max(0.0,progress)))
    meta=hydrate_sampling_metadata(rows)
    origins=[source_origin(r,registry) for r in meta]
    groups={REAL:[],MODELED:[]}
    for i,o in enumerate(origins): groups[o].append(i)
    if not groups[REAL]: raise RuntimeError("80/20 string training requires at least one rights-cleared real row")
    if require_modeled and not groups[MODELED]: raise RuntimeError("modeled lane required but no modeled rows were found")

    lane_mass={REAL:float(real_ratio),MODELED:float(modeled_ratio) if groups[MODELED] else 0.0}
    if lane_mass[MODELED]<=0: lane_mass={REAL:1.0,MODELED:0.0}
    else:
        n=lane_mass[REAL]+lane_mass[MODELED]
        lane_mass={k:v/n for k,v in lane_mass.items()}

    # Early: flatten source-quality differences and strongly cover rare cells.
    # Late: let the best real recordings dominate timbre while retaining a
    # smaller anti-collapse coverage pressure.
    quality_power=.50+.50*p
    coverage_power=.80-.55*p
    raw=[0.0]*len(meta)
    for origin,idxs in groups.items():
        if not idxs or lane_mass[origin]<=0: continue
        counts={}
        for i in idxs:
            key=(int(meta[i].get("instrument",-1)),int(meta[i].get("articulation",-1)))
            counts[key]=counts.get(key,0)+1
        vals=[]
        for i in idxs:
            q=source_quality(meta[i],registry,base_weights)**quality_power
            key=(int(meta[i].get("instrument",-1)),int(meta[i].get("articulation",-1)))
            # Unknown tags get neutral coverage instead of an artificial boost.
            cov=1.0 if -1 in key else (1.0/math.sqrt(max(1,counts[key])))**coverage_power
            vals.append(max(1e-12,q*cov))
        denom=sum(vals)
        for i,v in zip(idxs,vals): raw[i]=lane_mass[origin]*v/max(denom,1e-12)
    return raw


def coverage_audit(rows: Sequence[Mapping], weights: Sequence[float], registry: Mapping | None = None) -> dict:
    meta=hydrate_sampling_metadata(rows)
    total=float(sum(weights)) or 1.0
    cells={}
    for r,w in zip(meta,weights):
        key=f"{source_origin(r,registry)}:i{int(r.get('instrument',-1))}:a{int(r.get('articulation',-1))}"
        cells[key]=cells.get(key,0.0)+float(w)/total
    active=[v for k,v in cells.items() if ':i-1:' not in k and ':a-1' not in k]
    return {"cells":cells,"known_cells":len(active),"min_known_probability":min(active) if active else 0.0,"max_known_probability":max(active) if active else 0.0}

def mixture_audit(rows: Sequence[Mapping], weights: Sequence[float], registry: Mapping | None = None) -> dict:
    if len(rows) != len(weights):
        raise ValueError("rows/weights mismatch")
    total = float(sum(weights)) or 1.0
    out = {"count": len(rows), "real_count": 0, "modeled_count": 0, "real_probability": 0.0, "modeled_probability": 0.0}
    by_source = {}
    for row, w in zip(rows, weights):
        origin = source_origin(row, registry)
        out[f"{origin}_count"] += 1
        out[f"{origin}_probability"] += float(w) / total
        sid = source_id(row)
        entry = by_source.setdefault(sid, {"origin": origin, "count": 0, "probability": 0.0})
        entry["count"] += 1
        entry["probability"] += float(w) / total
    out["by_source"] = by_source
    return out


def modeled_mask(rows: Sequence[Mapping], registry: Mapping | None = None, *, device=None):
    import torch
    return torch.tensor([source_origin(r, registry) == MODELED for r in rows], dtype=torch.bool, device=device)
