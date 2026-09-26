#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, re
from pathlib import Path

LOG_STAGE={
    "01_codec.log":"codec",
    "02_latents.log":"codec",
    "03_renderer.log":"renderer",
    "04_distill.log":"distill",
    "05_shortcut.log":"shortcut",
}
BATCH_KEY={
    "codec":"codec.batch",
    "renderer":"renderer.batch",
    "distill":"distill.batch",
    "shortcut":"shortcut.batch",
}
ACCUM_KEY={
    "renderer":"renderer.accum",
    "distill":"distill.accum",
    "shortcut":"shortcut.accum",
}

def newest_log(root: Path):
    logs=[p for p in root.glob("*.log") if p.is_file()]
    return max(logs,key=lambda p:p.stat().st_mtime) if logs else None

def tail(path: Path, lines=160):
    try:
        xs=path.read_text(encoding="utf-8",errors="replace").splitlines()
        return "\n".join(xs[-lines:])
    except Exception:
        return ""

def infer_stage(path: Path|None, explicit: str|None):
    if explicit: return explicit
    if path and path.name in LOG_STAGE: return LOG_STAGE[path.name]
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--logs",default="logs/dnni5090")
    ap.add_argument("--log")
    ap.add_argument("--stage",choices=("codec","renderer","distill","shortcut"))
    a=ap.parse_args()
    p=Path(a.log) if a.log else newest_log(Path(a.logs))
    stage=infer_stage(p,a.stage or os.environ.get("DNNI_CURRENT_STAGE"))
    text=tail(p) if p else ""
    low=text.lower()

    print()
    print("="*66)
    print("DNNI TRAINING FAILURE DIAGNOSIS")
    print("="*66)
    print("Stage :",stage or "unknown")
    print("Log   :",p if p else "no log found")

    if any(x in low for x in ("cuda out of memory","torch.outofmemoryerror","cublas_status_alloc_failed","cuda error: out of memory")):
        print("Cause : CUDA VRAM exhaustion is likely.")
        if stage:
            print(f"Action: lower training/configs/dnni_5090_training.json -> {BATCH_KEY[stage]}.")
            if stage in ACCUM_KEY:
                print(f"        optionally raise {ACCUM_KEY[stage]} to keep a similar effective batch.")
            print(f"        then use RESET_DNNI_STAGE.bat and reset from '{stage}' before restarting.")
        print("        Close other GPU-heavy apps and check STATUS_DNNI_5090.bat before retrying.")
    elif "recipe fingerprint mismatch" in low:
        print("Cause : this stage checkpoint was created with different training recipe settings.")
        if stage: print(f"Action: use RESET_DNNI_STAGE.bat from '{stage}', then restart.")
        else: print("Action: run STATUS_DNNI_5090.bat and reset the first mismatching stage.")
    elif "data fingerprint mismatch" in low or "latents do not match" in low or "stale/mismatch" in low:
        print("Cause : DNNI source/render data changed relative to existing training artifacts.")
        print("Action: run STATUS_DNNI_5090.bat. If the change was intentional, archive/reset from the first stale stage.")
    elif "no space left on device" in low or "disk full" in low or "there is not enough space on the disk" in low:
        print("Cause : project/checkpoint drive is out of free space.")
        print("Action: free disk space; do not delete the newest valid .pt blindly. Archives can be moved to another drive.")
    elif "missing long bounce" in low or "missing " in low and "capture wav" in low:
        print("Cause : capture WAV data is incomplete.")
        print("Action: run PREPARE_DNNI_CAPTURE.bat, bounce the four long WAVs, then rerun training.")
    elif any(x in low for x in ("cuda driver version is insufficient","no kernel image is available","sm_120","torch.cuda.is_available() is false")):
        print("Cause : CUDA/PyTorch/driver environment is incompatible with the RTX 5090.")
        print("Action: run SETUP_DNNI_5090.bat and update the NVIDIA driver if preflight requests it.")
    elif "checkpoint" in low and any(x in low for x in ("corrupt","invalid","unexpected eof","pickle data was truncated")):
        print("Cause : a checkpoint may be incomplete/corrupt.")
        print("Action: run STATUS_DNNI_5090.bat. Atomic saves normally preserve the previous .pt; archive/reset only the affected stage.")
    else:
        print("Cause : not recognized automatically.")
        print("Action: inspect the end of the log below, then rerun STATUS_DNNI_5090.bat.")

    if text:
        print("-"*66)
        print("LAST LOG LINES")
        print("-"*66)
        for line in text.splitlines()[-35:]:
            print(line)
    print("="*66)

if __name__=="__main__":
    main()
