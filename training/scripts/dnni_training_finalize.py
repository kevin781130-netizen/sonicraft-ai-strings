#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from dnni_training_status import status

CHECKPOINTS={
    "codec":"checkpoints/dnni4_vae64_research.pt",
    "renderer_last":"checkpoints/dnni4_renderer_hq_research_last.pt",
    "renderer_best":"checkpoints/dnni4_renderer_hq_research_best.pt",
    "distill":"checkpoints/dnni4_frontier_research.pt",
    "shortcut":"checkpoints/dnni4_frontier_shortcut_research.pt",
}
DEFAULT_OUT=Path("checkpoints/dnni4_training_complete.json")

def sha256_file(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8<<20),b""): h.update(b)
    return h.hexdigest()

def build_manifest():
    s=status()
    bad=[x for x in s["stages"] if x["state"]!="complete" or not x["valid"]]
    if bad:
        raise RuntimeError("training is not complete: "+", ".join(f"{x['kind']}={x['state']} {x.get('epoch')}/{x.get('target')}" for x in bad))
    files={}
    for name,pstr in CHECKPOINTS.items():
        p=Path(pstr)
        if not p.exists(): raise RuntimeError(f"missing expected checkpoint: {p}")
        files[name]={"path":pstr.replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha256_file(p)}
    return {
        "schema":"sonicraft-dnni-four-timbres-training-complete-v1",
        "created_at":dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "research_only":True,
        "commercial_cleanroom_eligible":False,
        "data_fingerprint":s.get("data_fingerprint"),
        "recipe_fingerprint":s.get("recipe_fingerprint"),
        "recipe_stage_fingerprints":s.get("recipe_stage_fingerprints"),
        "source":s.get("source"),
        "capture_plan_rows":s.get("capture_plan_rows"),
        "render_manifest_rows":s.get("render_manifest_rows"),
        "latent_rows":s.get("latent_rows"),
        "stages":s.get("stages"),
        "checkpoints":files,
        "final_checkpoint":files["shortcut"],
    }

def verify(path: Path):
    m=json.loads(path.read_text(encoding="utf-8"))
    problems=[]
    for name,info in m.get("checkpoints",{}).items():
        p=Path(info["path"])
        if not p.exists():
            problems.append(f"{name}: missing {p}");continue
        got=sha256_file(p)
        if got!=info.get("sha256"): problems.append(f"{name}: SHA mismatch {got} != {info.get('sha256')}")
    current=status()
    if m.get("data_fingerprint")!=current.get("data_fingerprint"):
        problems.append("data fingerprint differs from completion manifest")
    if m.get("recipe_fingerprint")!=current.get("recipe_fingerprint"):
        problems.append("recipe fingerprint differs from completion manifest")
    if problems:
        print("VERIFY FAILED")
        for x in problems: print(" -",x)
        raise SystemExit(2)
    print("VERIFY PASS:",path)
    print("Final checkpoint:",m["final_checkpoint"]["path"])
    print("SHA-256:",m["final_checkpoint"]["sha256"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(DEFAULT_OUT))
    ap.add_argument("--verify",action="store_true")
    a=ap.parse_args();p=Path(a.out)
    if a.verify:
        if not p.exists(): raise SystemExit(f"missing completion manifest: {p}")
        verify(p);return
    m=build_manifest()
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding="utf-8")
    print("TRAINING COMPLETE MANIFEST ->",p)
    print("Final checkpoint SHA-256:",m["final_checkpoint"]["sha256"])

if __name__=="__main__":
    main()
