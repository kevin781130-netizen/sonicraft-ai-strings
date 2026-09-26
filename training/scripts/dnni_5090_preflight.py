#!/usr/bin/env python3
from __future__ import annotations
import json, platform, shutil, subprocess, sys
from pathlib import Path

def vtuple(s):
    out=[]
    for p in str(s).split("."):
        n=""
        for ch in p:
            if ch.isdigit(): n+=ch
            else: break
        if n: out.append(int(n))
        else: break
    return tuple(out)

def driver_info():
    try:
        p=subprocess.run(
            ["nvidia-smi","--query-gpu=name,driver_version,memory.total,memory.free","--format=csv,noheader,nounits"],
            capture_output=True,text=True,check=True
        )
        line=p.stdout.strip().splitlines()[0]
        name,drv,mem,free=[x.strip() for x in line.split(",",3)]
        return {"name":name,"driver":drv,"memory_mib":int(float(mem)),"memory_free_mib":int(float(free))}
    except Exception as e:
        return {"error":f"{type(e).__name__}: {e}"}

def main():
    report={"python":platform.python_version(),"executable":sys.executable}
    problems=[]; warnings=[]
    if sys.version_info < (3,10):
        problems.append("Python 3.10+ is required by current PyTorch.")
    try:
        import torch
        report["torch"]=torch.__version__
        report["torch_cuda"]=torch.version.cuda
        report["cuda_available"]=bool(torch.cuda.is_available())
        if not torch.cuda.is_available():
            problems.append("torch.cuda.is_available() is false.")
        else:
            report["gpu_name"]=torch.cuda.get_device_name(0)
            report["capability"]=list(torch.cuda.get_device_capability(0))
            report["bf16"]=bool(torch.cuda.is_bf16_supported())
            props=torch.cuda.get_device_properties(0)
            report["vram_gib"]=round(props.total_memory/(1024**3),2)
            if "5090" not in report["gpu_name"].upper():
                warnings.append(f"GPU is {report['gpu_name']!r}, not an RTX 5090; training may still work.")
            if tuple(report["capability"]) < (12,0) and "5090" in report["gpu_name"].upper():
                problems.append(f"RTX 5090 reported unexpected compute capability {report['capability']}.")
            if not report["bf16"]:
                warnings.append("BF16 is unavailable; training will fall back from the intended 5090 BF16 path.")
        if vtuple(torch.__version__) < (2,7):
            problems.append("PyTorch 2.7+ is required for official Blackwell support.")
        cuda=vtuple(torch.version.cuda or "0")
        if report.get("gpu_name") and "5090" in report["gpu_name"].upper() and cuda < (12,8):
            problems.append(f"RTX 5090 needs a Blackwell-capable PyTorch CUDA build; found CUDA {torch.version.cuda}.")
    except Exception as e:
        problems.append(f"PyTorch import failed: {type(e).__name__}: {e}")

    smi=driver_info(); report["nvidia_smi"]=smi
    drv=smi.get("driver")
    # NVIDIA CUDA 13.x minor-version compatibility requires an R580 (580+) driver.
    if drv and str(report.get("torch_cuda","")).startswith("13.") and vtuple(drv) < (580,):
        problems.append(f"NVIDIA driver {drv} is too old for CUDA 13.x; need NVIDIA driver 580+.")
    if smi.get("memory_mib") and smi.get("memory_free_mib") is not None:
        free_ratio=float(smi["memory_free_mib"])/max(1,float(smi["memory_mib"]))
        report["gpu_free_ratio"]=round(free_ratio,3)
        if free_ratio < 0.70:
            warnings.append(f"Only {smi['memory_free_mib']/1024:.1f} GiB of {smi['memory_mib']/1024:.1f} GiB GPU memory is free. Close GPU-heavy apps before long training.")

    free=shutil.disk_usage(Path.cwd()).free/(1024**3)
    report["disk_free_gib"]=round(free,1)
    if free < 30:
        warnings.append(f"Only {free:.1f} GiB free on the project drive; 30+ GiB is recommended for captures, latents and checkpoints.")

    print("="*66)
    print("SONICRAFT RTX 5090 PREFLIGHT")
    print("="*66)
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if warnings:
        print("\nWARNINGS:")
        for x in warnings: print(" -",x)
    if problems:
        print("\nFAILED:")
        for x in problems: print(" -",x)
        raise SystemExit(2)
    print("\nPASS: CUDA/PyTorch environment is viable for the DNNI research trainer.")

if __name__=="__main__":
    main()
