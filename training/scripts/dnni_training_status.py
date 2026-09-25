#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

STAGES = [
    ("codec", Path("checkpoints/dnni4_vae64_research.pt"), 100),
    ("renderer", Path("checkpoints/dnni4_renderer_hq_research_last.pt"), 260),
    ("distill", Path("checkpoints/dnni4_frontier_research.pt"), 130),
    ("shortcut", Path("checkpoints/dnni4_frontier_shortcut_research.pt"), 55),
]

def load_checkpoint(path: Path):
    import torch
    return torch.load(path, map_location="cpu")

def validate_checkpoint(kind: str, path: Path, target: int):
    if not path.exists():
        return {"kind":kind,"path":str(path),"state":"missing","epoch":0,"target":target,"valid":False}
    try:
        ck=load_checkpoint(path)
    except Exception as e:
        return {"kind":kind,"path":str(path),"state":"corrupt","epoch":0,"target":target,"valid":False,"error":f"{type(e).__name__}: {e}"}
    if not isinstance(ck, dict):
        return {"kind":kind,"path":str(path),"state":"invalid","epoch":0,"target":target,"valid":False,"error":"checkpoint is not a dict"}
    epoch=int(ck.get("epoch",0) or 0)
    errors=[]
    if epoch < 0: errors.append("negative epoch")
    if kind=="codec":
        if str(ck.get("codec_kind","")).lower()!="strings_vae64": errors.append("codec_kind != strings_vae64")
        if "model" not in ck: errors.append("missing model")
    elif kind=="renderer":
        if "model" not in ck: errors.append("missing model")
        if "config" not in ck: errors.append("missing config")
    elif kind=="distill":
        if "model" not in ck: errors.append("missing model")
        if "config" not in ck: errors.append("missing config")
        if "teacher" not in ck: errors.append("missing teacher")
    elif kind=="shortcut":
        if "model" not in ck: errors.append("missing model")
        if "config" not in ck: errors.append("missing config")
        if str(ck.get("sampling_family",""))!="shortcut": errors.append("sampling_family != shortcut")
    if errors:
        return {"kind":kind,"path":str(path),"state":"invalid","epoch":epoch,"target":target,"valid":False,"error":"; ".join(errors)}
    state="complete" if epoch>=target else "resumable"
    return {"kind":kind,"path":str(path),"state":state,"epoch":epoch,"target":target,"valid":True,
            "percent":round(min(100.0,100.0*epoch/max(1,target)),1)}

def count_jsonl(path: Path):
    if not path.exists(): return 0
    try:
        return sum(1 for x in path.read_text(encoding="utf-8").splitlines() if x.strip())
    except Exception:
        return -1

def status():
    root=Path("datasets/dnni_four_timbres")
    plan=root/"capture_plan.jsonl"
    raw=root/"rendered/index.jsonl"
    lat=root/"latents/index.jsonl"
    out={
        "capture_plan_rows":count_jsonl(plan),
        "render_manifest_rows":count_jsonl(raw),
        "latent_rows":count_jsonl(lat),
        "stages":[validate_checkpoint(k,p,t) for k,p,t in STAGES],
    }
    return out

def print_human(s):
    print("="*66)
    print("SONICRAFT DNNI 4-Timbre RTX 5090 Training Status")
    print("="*66)
    print(f"Capture plan : {s['capture_plan_rows']} rows")
    print(f"Render WAVs  : {s['render_manifest_rows']} manifest rows")
    print(f"Latents      : {s['latent_rows']} rows")
    print("-"*66)
    for st in s["stages"]:
        label=st["kind"].upper().ljust(9)
        state=st["state"].upper().ljust(9)
        if st["valid"]:
            print(f"{label} {state} epoch {st['epoch']:>3}/{st['target']:<3}  {st.get('percent',0):>5.1f}%")
        else:
            extra=f" - {st.get('error','')}" if st.get("error") else ""
            print(f"{label} {state}{extra}")
    print("-"*66)
    bad=[x for x in s["stages"] if x["state"] in ("corrupt","invalid")]
    if bad:
        print("ACTION: A checkpoint is invalid. Do not delete it automatically; inspect/rename it first.")
    elif s["stages"][-1]["state"]=="complete":
        print("RESULT: Training pipeline is complete.")
    else:
        print("RESULT: TRAIN_DNNI_5090.bat can start/resume from the latest valid stage.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--json",action="store_true")
    ap.add_argument("--validate",nargs=3,metavar=("KIND","PATH","TARGET"))
    a=ap.parse_args()
    if a.validate:
        kind,path,target=a.validate
        r=validate_checkpoint(kind,Path(path),int(target))
        if a.json: print(json.dumps(r,ensure_ascii=False))
        else:
            print(f"[{r['state'].upper()}] {kind} {r.get('epoch',0)}/{r.get('target',target)} {path}")
            if r.get("error"): print("ERROR:",r["error"])
        raise SystemExit(0 if r["valid"] else 2)
    s=status()
    if a.json: print(json.dumps(s,indent=2,ensure_ascii=False))
    else: print_human(s)
    raise SystemExit(2 if any(x["state"] in ("corrupt","invalid") for x in s["stages"]) else 0)

if __name__=="__main__":
    main()
