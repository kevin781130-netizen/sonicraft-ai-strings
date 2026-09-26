#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

DEFAULT_CONFIG=Path("training/configs/dnni_four_timbres.json")
DEFAULT_BUNDLE=Path("datasets/dnni_four_timbres/source/bundle_manifest.json")
DEFAULT_RENDER=Path("datasets/dnni_four_timbres/rendered/index.jsonl")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

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
    return sorted(out,key=lambda x:str(x.get("timbre_id","")))

def render_identity(path: Path):
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        # Absolute local paths are intentionally excluded so moving D:/ -> E:/ does
        # not invalidate an otherwise identical dataset.
        r={k:v for k,v in r.items() if k not in {"audio","path","file"}}
        rows.append(r)
    rows.sort(key=lambda x:str(x.get("capture_id") or x.get("audio_sha256") or ""))
    return rows

def compute(config=DEFAULT_CONFIG,bundle=DEFAULT_BUNDLE,render=DEFAULT_RENDER):
    config,bundle,render=Path(config),Path(bundle),Path(render)
    for p in (config,bundle,render):
        if not p.exists(): raise FileNotFoundError(str(p))
    payload={
        "schema":"sonicraft-dnni-data-fingerprint-v2",
        "config":read_json(config),
        "bundle":bundle_identity(bundle),
        "render_rows":render_identity(render),
    }
    digest=hashlib.sha256(canonical(payload)).hexdigest()
    return {
        "schema":payload["schema"],
        "fingerprint":digest,
        "config":str(config).replace("\\","/"),
        "bundle":str(bundle).replace("\\","/"),
        "render":str(render).replace("\\","/"),
        "render_rows":len(payload["render_rows"]),
        "timbres":len(payload["bundle"]),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default=str(DEFAULT_CONFIG))
    ap.add_argument("--bundle",default=str(DEFAULT_BUNDLE))
    ap.add_argument("--render",default=str(DEFAULT_RENDER))
    ap.add_argument("--out")
    ap.add_argument("--value-only",action="store_true")
    a=ap.parse_args()
    info=compute(a.config,a.bundle,a.render)
    if a.out:
        p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding="utf-8")
    print(info["fingerprint"] if a.value_only else json.dumps(info,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
