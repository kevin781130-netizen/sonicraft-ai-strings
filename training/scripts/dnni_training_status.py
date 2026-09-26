#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dnni_pipeline_fingerprint import compute as compute_fingerprint
from dnni_training_config import load as load_training_config, fingerprint as recipe_fingerprint

STAGES = [
    ("codec", Path("checkpoints/dnni4_vae64_research.pt"), 100),
    ("renderer", Path("checkpoints/dnni4_renderer_hq_research_last.pt"), 260),
    ("distill", Path("checkpoints/dnni4_frontier_research.pt"), 130),
    ("shortcut", Path("checkpoints/dnni4_frontier_shortcut_research.pt"), 55),
]

def load_checkpoint(path: Path):
    import torch
    return torch.load(path, map_location="cpu")

def validate_checkpoint(kind: str, path: Path, target: int, expected_fingerprint: str|None=None, expected_recipe: str|None=None):
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
    if expected_fingerprint and ck.get('data_fingerprint')!=expected_fingerprint:
        errors.append(f"data_fingerprint mismatch: saved={ck.get('data_fingerprint')} current={expected_fingerprint}")
    if expected_recipe and ck.get('recipe_fingerprint')!=expected_recipe:
        errors.append(f"recipe_fingerprint mismatch: saved={ck.get('recipe_fingerprint')} current={expected_recipe}")
    if errors:
        return {"kind":kind,"path":str(path),"state":"invalid","epoch":epoch,"target":target,"valid":False,"error":"; ".join(errors)}
    state="complete" if epoch>=target else "resumable"
    return {"kind":kind,"path":str(path),"state":state,"epoch":epoch,"target":target,"valid":True,
            "percent":round(min(100.0,100.0*epoch/max(1,target)),1),
            "partial_epoch":ck.get("partial_epoch"),"partial_batches":ck.get("partial_batches")}

def count_jsonl(path: Path):
    if not path.exists(): return 0
    try:
        return sum(1 for x in path.read_text(encoding="utf-8").splitlines() if x.strip())
    except Exception:
        return -1

def status():
    root=Path("datasets/dnni_four_timbres")
    bundle=root/"source/bundle_manifest.json"
    source=None
    if bundle.exists():
        try:
            b=json.loads(bundle.read_text(encoding="utf-8"))
            source={
                "imported":True,
                "path":str(bundle),
                "timbres":[{
                    "timbre_id":x.get("timbre_id"),
                    "source_tar":Path(str(x.get("source_tar",""))).name,
                    "weight_sha256":str(x.get("weight_sha256","")),
                    "weight_bytes":x.get("weight_bytes"),
                } for x in b.get("timbres",[])]
            }
        except Exception as e:
            source={"imported":False,"path":str(bundle),"error":f"{type(e).__name__}: {e}"}
    else:
        source={"imported":False,"path":str(bundle)}
    plan=root/"capture_plan.jsonl"
    batch_map=root/"batch_capture/batch_capture_map.json"
    batch_bounces=[root/f"batch_bounces/timbre_{i}.wav" for i in range(1,5)]
    raw=root/"rendered/index.jsonl"
    lat=root/"latents/index.jsonl"
    fingerprint=None; fp_error=None
    recipe=None; recipe_error=None
    try: recipe=recipe_fingerprint(load_training_config('training/configs/dnni_5090_training.json'))
    except Exception as e: recipe_error=f"{type(e).__name__}: {e}"
    if bundle.exists() and raw.exists():
        try: fingerprint=compute_fingerprint()["fingerprint"]
        except Exception as e: fp_error=f"{type(e).__name__}: {e}"
    latent_prov=root/"latents/provenance.json"
    latent_status={"exists":latent_prov.exists(),"valid":False}
    if latent_prov.exists():
        try:
            lp=json.loads(latent_prov.read_text(encoding="utf-8"))
            latent_status={"exists":True,"valid":bool(fingerprint and lp.get("source_fingerprint")==fingerprint),
                           "saved_fingerprint":lp.get("source_fingerprint"),"rows":lp.get("rows"),
                           "codec_sha256":lp.get("codec_sha256")}
        except Exception as e:
            latent_status={"exists":True,"valid":False,"error":f"{type(e).__name__}: {e}"}
    out={
        "source":source,
        "data_fingerprint":fingerprint,
        "fingerprint_error":fp_error,
        "recipe_fingerprint":recipe,
        "recipe_error":recipe_error,
        "capture_plan_rows":count_jsonl(plan),
        "batch_capture_map":batch_map.exists(),
        "batch_bounces_present":sum(1 for p in batch_bounces if p.exists()),
        "batch_bounces_expected":4,
        "render_manifest_rows":count_jsonl(raw),
        "latent_rows":count_jsonl(lat),
        "latent_provenance":latent_status,
        "stages":[validate_checkpoint(k,p,t,fingerprint,recipe) for k,p,t in STAGES],
    }
    return out

def print_human(s):
    print("="*66)
    print("SONICRAFT DNNI 4-Timbre RTX 5090 Training Status")
    print("="*66)
    src=s.get("source") or {}
    if src.get("imported"):
        print("DNNI source  : imported")
        for x in src.get("timbres",[]):
            print(f"  {str(x.get('timbre_id','?')).ljust(9)} {str(x.get('source_tar','?')).ljust(28)} {str(x.get('weight_sha256',''))[:16]}...")
    else:
        print("DNNI source  : not imported")
        if src.get("error"): print("  ERROR:",src["error"])
    print(f"Capture plan : {s['capture_plan_rows']} rows")
    print("Batch MIDI   :", "ready" if s.get("batch_capture_map") else "not prepared")
    print(f"Long bounces : {s.get('batch_bounces_present',0)}/{s.get('batch_bounces_expected',4)}")
    print(f"Render WAVs  : {s['render_manifest_rows']} manifest rows")
    print(f"Latents      : {s['latent_rows']} rows")
    if s.get("data_fingerprint"): print("Data hash    :",str(s["data_fingerprint"])[:20]+"...")
    if s.get("recipe_fingerprint"): print("Recipe hash  :",str(s["recipe_fingerprint"])[:20]+"...")
    lp=s.get("latent_provenance") or {}
    if lp.get("exists"):
        print("Latent bind  :", "MATCH" if lp.get("valid") else "STALE/MISMATCH")
    elif s.get("latent_rows"):
        print("Latent bind  : missing provenance")
    print("-"*66)
    for st in s["stages"]:
        label=st["kind"].upper().ljust(9)
        state=st["state"].upper().ljust(9)
        if st["valid"]:
            suffix=""
            if st.get("partial_epoch"):
                suffix=f"  partial epoch {st['partial_epoch']} @ batch {st.get('partial_batches')}"
            print(f"{label} {state} epoch {st['epoch']:>3}/{st['target']:<3}  {st.get('percent',0):>5.1f}%{suffix}")
        else:
            extra=f" - {st.get('error','')}" if st.get("error") else ""
            print(f"{label} {state}{extra}")
    print("-"*66)
    bad=[x for x in s["stages"] if x["state"] in ("corrupt","invalid")]
    lp=s.get("latent_provenance") or {}
    latent_bad=bool(s.get("latent_rows") and (not lp.get("exists") or not lp.get("valid")))
    if bad:
        print("ACTION: A checkpoint is invalid/stale. Do not overwrite it automatically; inspect/rename it first.")
    elif latent_bad:
        print("ACTION: Latents do not match the current four-timbre data fingerprint; rebuild latents before training.")
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
    bad_stage=any(x["state"] in ("corrupt","invalid") for x in s["stages"])
    lp=s.get("latent_provenance") or {}
    bad_latent=bool(s.get("latent_rows") and (not lp.get("exists") or not lp.get("valid")))
    raise SystemExit(2 if bad_stage or bad_latent or s.get("fingerprint_error") or s.get("recipe_error") else 0)

if __name__=="__main__":
    main()
