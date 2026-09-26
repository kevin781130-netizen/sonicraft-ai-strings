#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, shutil
from pathlib import Path

CHECKPOINT_GLOBS=("dnni4_*.pt","dnni4_*.pt.tmp","dnni4_stop_after_epoch.flag")

def move_path(src: Path, dst_root: Path, moved: list):
    if not src.exists(): return
    dst=dst_root/src
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        raise RuntimeError(f"archive destination already exists: {dst}")
    shutil.move(str(src),str(dst))
    moved.append({"from":str(src),"to":str(dst)})

def main():
    ap=argparse.ArgumentParser(description="Archive DNNI training outputs before rebuilding against changed source data.")
    ap.add_argument("--archive-root",default="archive/dnni5090")
    ap.add_argument("--include-logs",action="store_true")
    a=ap.parse_args()
    stamp=dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst=Path(a.archive_root)/stamp
    moved=[]
    for pat in CHECKPOINT_GLOBS:
        for p in Path("checkpoints").glob(pat):
            move_path(p,dst,moved)
    move_path(Path("datasets/dnni_four_timbres/latents"),dst,moved)
    if a.include_logs:
        move_path(Path("logs/dnni5090"),dst,moved)
    dst.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"sonicraft-dnni-training-archive-v1","created":stamp,"moved":moved}
    (dst/"archive_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Archived",len(moved),"training artifact(s) ->",dst)
    if not moved: print("No existing DNNI training artifacts were present.")
    print("Source DNNI packages and rendered WAV files were NOT moved.")

if __name__=="__main__":
    main()
