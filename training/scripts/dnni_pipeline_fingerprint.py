#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

DEFAULT_PARTS = [
    Path("training/configs/dnni_four_timbres.json"),
    Path("datasets/dnni_four_timbres/source/bundle_manifest.json"),
    Path("datasets/dnni_four_timbres/rendered/index.jsonl"),
]

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8<<20),b""): h.update(b)
    return h.hexdigest()

def compute(parts):
    h=hashlib.sha256(); rows=[]
    for p in parts:
        p=Path(p)
        if not p.exists():
            raise FileNotFoundError(str(p))
        digest=sha256_file(p)
        rows.append({"path":str(p).replace("\\","/"),"sha256":digest,"bytes":p.stat().st_size})
        h.update(rows[-1]["path"].encode("utf-8"));h.update(b"\0")
        h.update(digest.encode("ascii"));h.update(b"\0")
    return {"schema":"sonicraft-dnni-data-fingerprint-v1","fingerprint":h.hexdigest(),"parts":rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--part",action="append")
    ap.add_argument("--out")
    ap.add_argument("--value-only",action="store_true")
    a=ap.parse_args()
    info=compute(a.part or DEFAULT_PARTS)
    if a.out:
        p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding="utf-8")
    if a.value_only: print(info["fingerprint"])
    else: print(json.dumps(info,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
