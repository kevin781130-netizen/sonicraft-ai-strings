#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, shutil
from pathlib import Path

ORDER=("codec","renderer","distill","shortcut")
STAGE_PATHS={
    "codec":[
        Path("checkpoints/dnni4_vae64_research.pt"),
        Path("checkpoints/dnni4_vae64_decoder_research.pt"),
        Path("datasets/dnni_four_timbres/latents"),
    ],
    "renderer":[
        Path("checkpoints/dnni4_renderer_hq_research_last.pt"),
        Path("checkpoints/dnni4_renderer_hq_research_best.pt"),
    ],
    "distill":[Path("checkpoints/dnni4_frontier_research.pt")],
    "shortcut":[Path("checkpoints/dnni4_frontier_shortcut_research.pt")],
}
LOG_PATHS={
    "codec":[Path("logs/dnni5090/01_codec.log"),Path("logs/dnni5090/02_latents.log")],
    "renderer":[Path("logs/dnni5090/03_renderer.log")],
    "distill":[Path("logs/dnni5090/04_distill.log")],
    "shortcut":[Path("logs/dnni5090/05_shortcut.log")],
}

def move_path(src: Path, dst_root: Path, moved: list):
    if not src.exists(): return
    dst=dst_root/src
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        raise RuntimeError(f"archive destination already exists: {dst}")
    shutil.move(str(src),str(dst))
    moved.append({"from":str(src),"to":str(dst)})

def main():
    ap=argparse.ArgumentParser(description="Archive DNNI training outputs without deleting source DNNI/WAV data.")
    ap.add_argument("--archive-root",default="archive/dnni5090")
    ap.add_argument("--from-stage",choices=ORDER,default="codec",
                    help="Archive this stage and all downstream stages. codec = full training-state reset.")
    ap.add_argument("--include-logs",action="store_true")
    a=ap.parse_args()
    stamp=dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst=Path(a.archive_root)/f"{stamp}_{a.from_stage}"
    moved=[]
    start=ORDER.index(a.from_stage)
    stages=ORDER[start:]
    for stage in stages:
        for p in STAGE_PATHS[stage]: move_path(p,dst,moved)
        if a.include_logs:
            for p in LOG_PATHS[stage]: move_path(p,dst,moved)
    # Stop/request/temp state is never useful after a reset.
    for p in (
        Path("checkpoints/dnni4_stop_after_epoch.flag"),
        Path("checkpoints/dnni4_training_recipe.cmd"),
    ):
        move_path(p,dst,moved)
    dst.mkdir(parents=True,exist_ok=True)
    manifest={
        "schema":"sonicraft-dnni-training-archive-v2",
        "created":stamp,
        "from_stage":a.from_stage,
        "stages":list(stages),
        "moved":moved,
    }
    (dst/"archive_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Archived",len(moved),"training artifact(s) ->",dst)
    print("Stages reset:",", ".join(stages))
    if not moved: print("No matching existing DNNI training artifacts were present.")
    print("DNNI source packages, capture plan, batch bounces and rendered capture WAVs were NOT moved.")

if __name__=="__main__":
    main()
