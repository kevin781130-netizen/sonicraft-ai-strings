#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

DEFAULT_CONFIG=Path("training/configs/dnni_four_timbres.json")
DEFAULT_BUNDLE=Path("datasets/dnni_four_timbres/source/bundle_manifest.json")
DEFAULT_PLAN=Path("datasets/dnni_four_timbres/capture_plan.jsonl")
DEFAULT_RENDER=Path("datasets/dnni_four_timbres/rendered/index.jsonl")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def config_identity(path: Path):
    cfg=read_json(path)
    slots=[]
    for x in cfg.get("slots",[]):
        slots.append({
            "slot":int(x.get("slot",0)),
            "timbre_id":str(x.get("timbre_id","")),
            "instrument":int(x.get("instrument",-1)),
            "midi_low":int(x.get("midi_low",-1)),
            "midi_high":int(x.get("midi_high",-1)),
        })
    slots.sort(key=lambda x:x["slot"])
    if [x["slot"] for x in slots] != [1,2,3,4]:
        raise ValueError("timbre config must contain slots 1..4 exactly once")
    if len({x["timbre_id"] for x in slots})!=4:
        raise ValueError("timbre_id values must be unique")
    if sorted(x["instrument"] for x in slots)!=[0,1,2,3]:
        raise ValueError("DNNI four-timbre instrument IDs must be exactly 0,1,2,3")
    for x in slots:
        if not (0<=x["midi_low"]<=x["midi_high"]<=127):
            raise ValueError(f"invalid MIDI range for {x['timbre_id']}: {x['midi_low']}..{x['midi_high']}")
    return {"schema":cfg.get("schema"),"slots":slots}

def bundle_identity(path: Path):
    b=read_json(path)
    out=[]
    for x in b.get("timbres",[]):
        out.append({
            "timbre_id":x.get("timbre_id"),
            "source_tar_sha256":x.get("source_tar_sha256"),
            "manifest_source_name":x.get("manifest_source_name"),
            "source_size":x.get("source_size"),
            "magic_hex":x.get("magic_hex"),
            "version":x.get("version"),
            "header_size":x.get("header_size"),
            "weight_bytes":x.get("weight_bytes"),
            "weight_sha256":x.get("weight_sha256"),
        })
    out.sort(key=lambda x:str(x.get("timbre_id","")))
    if len(out)!=4: raise ValueError(f"expected 4 imported timbres, found {len(out)}")
    return out

def jsonl_identity(path: Path, *, drop_paths=False, drop_display=False):
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        if drop_paths:
            r={k:v for k,v in r.items() if k not in {"audio","path","file"}}
        if drop_display:
            r={k:v for k,v in r.items() if k not in {"timbre_label","articulation_name"}}
        rows.append(r)
    rows.sort(key=lambda x:str(x.get("capture_id") or x.get("audio_sha256") or ""))
    return rows

def validate_alignment(cfg, bundle, plan_rows, render_rows):
    slots={x["timbre_id"]:x for x in cfg["slots"]}
    if {x["timbre_id"] for x in bundle} != set(slots):
        raise ValueError("imported DNNI timbre IDs do not match training config")
    plan_ids=set()
    for r in plan_rows:
        tid=str(r.get("timbre_id","")); cid=str(r.get("capture_id",""))
        if tid not in slots: raise ValueError(f"capture {cid}: unknown timbre_id {tid}")
        slot=slots[tid]
        if int(r.get("instrument",-1))!=slot["instrument"]:
            raise ValueError(f"capture {cid}: instrument ID does not match config for {tid}")
        pitch=float(r.get("pitch",-999))
        if not slot["midi_low"]<=pitch<=slot["midi_high"]:
            raise ValueError(f"capture {cid}: pitch {pitch} outside configured range for {tid}")
        if not cid: raise ValueError("capture row missing capture_id")
        if cid in plan_ids: raise ValueError(f"duplicate capture_id {cid}")
        plan_ids.add(cid)
    render_ids={str(r.get("capture_id","")) for r in render_rows}
    if render_ids != plan_ids:
        missing=sorted(plan_ids-render_ids)[:5]; extra=sorted(render_ids-plan_ids)[:5]
        raise ValueError(f"render manifest/capture plan mismatch: missing={missing} extra={extra}")

def compute(config=DEFAULT_CONFIG,bundle=DEFAULT_BUNDLE,plan=DEFAULT_PLAN,render=DEFAULT_RENDER):
    config,bundle,plan,render=map(Path,(config,bundle,plan,render))
    for p in (config,bundle,plan,render):
        if not p.exists(): raise FileNotFoundError(str(p))
    cfg=config_identity(config)
    bun=bundle_identity(bundle)
    plan_rows=jsonl_identity(plan,drop_display=True)
    render_rows=jsonl_identity(render,drop_paths=True)
    validate_alignment(cfg,bun,plan_rows,render_rows)
    payload={
        "schema":"sonicraft-dnni-data-fingerprint-v3",
        "config":cfg,
        "bundle":bun,
        "capture_plan":plan_rows,
        "render_rows":render_rows,
    }
    digest=hashlib.sha256(canonical(payload)).hexdigest()
    return {
        "schema":payload["schema"],
        "fingerprint":digest,
        "config":str(config).replace("\\","/"),
        "bundle":str(bundle).replace("\\","/"),
        "plan":str(plan).replace("\\","/"),
        "render":str(render).replace("\\","/"),
        "capture_rows":len(plan_rows),
        "render_rows":len(render_rows),
        "timbres":len(bun),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default=str(DEFAULT_CONFIG))
    ap.add_argument("--bundle",default=str(DEFAULT_BUNDLE))
    ap.add_argument("--plan",default=str(DEFAULT_PLAN))
    ap.add_argument("--render",default=str(DEFAULT_RENDER))
    ap.add_argument("--out")
    ap.add_argument("--value-only",action="store_true")
    a=ap.parse_args()
    info=compute(a.config,a.bundle,a.plan,a.render)
    if a.out:
        p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding="utf-8")
    print(info["fingerprint"] if a.value_only else json.dumps(info,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
