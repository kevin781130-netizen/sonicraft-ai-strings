#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from dataclasses import asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"training"))
from dnni_reference import import_four

SLOT_RE=re.compile(r"^(0[1-4])[_-].+\.tar$",re.I)

def main():
    ap=argparse.ArgumentParser(description="Import exactly four ordered DNNI tar packages from a private input directory.")
    ap.add_argument("--input",default="dnni_input")
    ap.add_argument("--out",default="datasets/dnni_four_timbres/source")
    ap.add_argument("--config",default="training/configs/dnni_four_timbres.json")
    a=ap.parse_args()
    root=Path(a.input)
    root.mkdir(parents=True,exist_ok=True)
    files=sorted(root.glob("*.tar"),key=lambda p:p.name.lower())
    if len(files)!=4:
        raise SystemExit(f"Expected exactly 4 .tar files in {root}; found {len(files)}. Name them 01_name.tar ... 04_name.tar.")
    slots={}
    for p in files:
        m=SLOT_RE.match(p.name)
        if not m:
            raise SystemExit(f"{p.name}: filename must start with 01_, 02_, 03_, or 04_.")
        slot=int(m.group(1))
        if slot in slots:
            raise SystemExit(f"duplicate slot prefix {slot:02d}")
        slots[slot]=p
    if set(slots)!={1,2,3,4}:
        raise SystemExit("Need exactly one file for each prefix 01_, 02_, 03_, 04_.")
    ordered=[slots[i] for i in range(1,5)]
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8"))
    rows=sorted(cfg.get("slots",[]),key=lambda x:int(x.get("slot",0)))
    if len(rows)!=4 or [int(x.get("slot",0)) for x in rows]!=[1,2,3,4]:
        raise SystemExit(f"{a.config}: expected slots 1..4")
    names=[str(x.get("timbre_id") or f"timbre_{i}") for i,x in enumerate(rows,1)]
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):
        manifest=out/"bundle_manifest.json"
        if manifest.exists():
            print("Existing DNNI import found:",manifest)
            print("To re-import, move/delete datasets/dnni_four_timbres/source first.")
            raise SystemExit(0)
        raise SystemExit(f"Destination exists and is not empty: {out}")
    recs=import_four(ordered,out,names)
    print("\nImported ordered DNNI slots:")
    for r in recs:
        print(f"  {r.timbre_id}: {Path(r.source_tar).name}  weights={r.weight_sha256[:16]}...")
    print("\nBundle manifest:",out/"bundle_manifest.json")

if __name__=="__main__":
    main()
