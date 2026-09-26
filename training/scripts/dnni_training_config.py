#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

DEFAULT=Path("training/configs/dnni_5090_training.json")

def load(path):
    c=json.loads(Path(path).read_text(encoding="utf-8"))
    for k in ("codec","renderer","distill","shortcut","cuda"):
        if k not in c: raise ValueError(f"missing config section: {k}")
    if int(c["codec"]["width"])<=0: raise ValueError("codec.width must be >0")
    for s in ("codec","renderer","distill","shortcut"):
        if int(c[s]["epochs"])<=0 or int(c[s]["batch"])<=0: raise ValueError(f"invalid {s} epochs/batch")
    for s in ("renderer","distill","shortcut"):
        if int(c[s]["accum"])<=0: raise ValueError(f"invalid {s}.accum")
    ms=int(c["shortcut"]["max_steps"]); rs=int(c["shortcut"]["recommend_steps"])
    if ms<2 or (ms & (ms-1)): raise ValueError("shortcut.max_steps must be power of two >=2")
    if rs<1 or ms%rs: raise ValueError("shortcut.recommend_steps must divide max_steps")
    return c

def recipe_identity(c):
    # Target epoch counts are intentionally excluded so training can be extended later
    # without invalidating an otherwise compatible checkpoint.
    return {
        "schema":c.get("schema"),
        "codec":{"width":int(c["codec"]["width"]),"batch":int(c["codec"]["batch"])},
        "renderer":{"preset":str(c["renderer"]["preset"]),"batch":int(c["renderer"]["batch"]),"accum":int(c["renderer"]["accum"])},
        "distill":{"preset":str(c["distill"]["preset"]),"batch":int(c["distill"]["batch"]),"accum":int(c["distill"]["accum"])},
        "shortcut":{"preset":str(c["shortcut"]["preset"]),"batch":int(c["shortcut"]["batch"]),"accum":int(c["shortcut"]["accum"]),
                    "max_steps":int(c["shortcut"]["max_steps"]),"recommend_steps":int(c["shortcut"]["recommend_steps"])},
    }

def fingerprint(c):
    raw=json.dumps(recipe_identity(c),sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def q(v):
    return str(v).replace('"','')

def cmd_lines(c):
    fp=fingerprint(c)
    vals={
        "DNNI_CODEC_WIDTH":c["codec"]["width"],"DNNI_CODEC_EPOCHS":c["codec"]["epochs"],"DNNI_CODEC_BATCH":c["codec"]["batch"],
        "DNNI_RENDER_PRESET":c["renderer"]["preset"],"DNNI_RENDER_EPOCHS":c["renderer"]["epochs"],"DNNI_RENDER_BATCH":c["renderer"]["batch"],"DNNI_RENDER_ACCUM":c["renderer"]["accum"],
        "DNNI_DISTILL_PRESET":c["distill"]["preset"],"DNNI_DISTILL_EPOCHS":c["distill"]["epochs"],"DNNI_DISTILL_BATCH":c["distill"]["batch"],"DNNI_DISTILL_ACCUM":c["distill"]["accum"],
        "DNNI_SHORTCUT_PRESET":c["shortcut"]["preset"],"DNNI_SHORTCUT_EPOCHS":c["shortcut"]["epochs"],"DNNI_SHORTCUT_BATCH":c["shortcut"]["batch"],"DNNI_SHORTCUT_ACCUM":c["shortcut"]["accum"],
        "DNNI_SHORTCUT_MAX_STEPS":c["shortcut"]["max_steps"],"DNNI_SHORTCUT_RECOMMEND_STEPS":c["shortcut"]["recommend_steps"],
        "PYTORCH_CUDA_ALLOC_CONF":c["cuda"].get("allocator",""),"CUDA_MODULE_LOADING":c["cuda"].get("module_loading","LAZY"),
        "SONICRAFT_RECIPE_FINGERPRINT":fp,
    }
    return [f'set "{k}={q(v)}"' for k,v in vals.items()]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--config",default=str(DEFAULT));ap.add_argument("--write-cmd");ap.add_argument("--fingerprint",action="store_true")
    a=ap.parse_args();c=load(a.config)
    if a.fingerprint: print(fingerprint(c));return
    lines=cmd_lines(c)
    if a.write_cmd:
        p=Path(a.write_cmd);p.parent.mkdir(parents=True,exist_ok=True);p.write_text("\r\n".join(lines)+"\r\n",encoding="utf-8")
        print("training recipe cmd ->",p,"fingerprint",fingerprint(c))
    else:
        print("\n".join(lines))

if __name__=="__main__":main()
