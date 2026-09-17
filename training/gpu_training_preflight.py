from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from training_control import DEFAULT_PAUSE_FILE, DEFAULT_STATUS_FILE, pause_requested, read_status

ROOT = Path(__file__).resolve().parents[1]


def _resolve(value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (ROOT / p).resolve()


def _existing_parent(path: Path) -> Path:
    p = path
    while not p.exists() and p.parent != p:
        p = p.parent
    return p


def _check_output(path: Path | None, label: str, errors: list[str], facts: dict) -> None:
    if path is None:
        return
    parent = _existing_parent(path.parent)
    writable = parent.exists() and parent.is_dir() and os.access(parent, os.W_OK)
    facts[label] = {"path": str(path), "existing_parent": str(parent), "writable": bool(writable)}
    if not writable:
        errors.append(f"{label} parent is not writable: {parent}")


def _inspect_index(path: Path | None, sample_rows: int, errors: list[str], warnings: list[str], facts: dict) -> None:
    if path is None:
        errors.append("--index is required for production GPU preflight")
        return
    if not path.exists() or not path.is_file():
        errors.append(f"training index does not exist: {path}")
        return

    rows = 0
    sampled = 0
    missing_files: list[str] = []
    bad_json: list[int] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            rows += 1
            if sampled >= sample_rows:
                continue
            try:
                row = json.loads(line)
            except Exception:
                bad_json.append(lineno)
                continue
            sampled += 1
            file_value = row.get("file")
            if not file_value:
                warnings.append(f"index row {lineno} has no latent file field")
                continue
            latent = Path(str(file_value)).expanduser()
            if not latent.is_absolute():
                latent = (ROOT / latent).resolve()
            if not latent.exists():
                missing_files.append(str(latent))

    facts["index"] = {
        "path": str(path),
        "rows": rows,
        "sampled_rows": sampled,
        "sample_missing_files": missing_files,
        "bad_json_lines": bad_json,
    }
    if rows == 0:
        errors.append(f"training index is empty: {path}")
    if bad_json:
        errors.append(f"training index contains invalid JSON in sampled lines: {bad_json[:8]}")
    if missing_files:
        errors.append(f"sampled latent files are missing ({len(missing_files)}): {missing_files[:3]}")


def _inspect_resume(path: Path | None, errors: list[str], facts: dict) -> None:
    if path is None:
        return
    exists = path.exists() and path.is_file()
    facts["resume"] = {"path": str(path), "exists": bool(exists)}
    if not exists:
        errors.append(f"resume checkpoint does not exist: {path}")


def _inspect_control(errors: list[str], warnings: list[str], facts: dict) -> None:
    pending = pause_requested(DEFAULT_PAUSE_FILE)
    status = read_status(DEFAULT_STATUS_FILE)
    facts["training_control"] = {
        "pause_file": str(DEFAULT_PAUSE_FILE),
        "status_file": str(DEFAULT_STATUS_FILE),
        "pending_pause": bool(pending),
        "state": str(status.get("state", "unknown")),
        "pid": status.get("pid"),
        "message": status.get("message"),
    }
    if pending:
        errors.append(
            "a pause request is already pending; clear it with `python training/training_control.py clear` "
            "before starting a new job"
        )
    if status.get("state") in {"running", "pause_requested", "resuming"}:
        warnings.append(
            f"training-control status is {status.get('state')!r}; verify another renderer job is not already active"
        )


def _inspect_cuda(allow_no_cuda: bool, require_bf16: bool, min_vram_gb: float,
                  errors: list[str], warnings: list[str], facts: dict) -> None:
    try:
        import torch
    except Exception as exc:
        facts["torch"] = {"importable": False, "error": str(exc)}
        if not allow_no_cuda:
            errors.append(f"PyTorch import failed: {exc}")
        return

    cuda = bool(torch.cuda.is_available())
    info = {
        "importable": True,
        "version": str(getattr(torch, "__version__", "unknown")),
        "cuda_available": cuda,
        "torch_cuda_version": str(getattr(torch.version, "cuda", None)),
    }
    if not cuda:
        facts["torch"] = info
        if not allow_no_cuda:
            errors.append("CUDA is not available to PyTorch")
        return

    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    total_gb = float(props.total_memory) / (1024 ** 3)
    bf16 = bool(torch.cuda.is_bf16_supported())
    info.update({
        "device_index": int(device),
        "device_count": int(torch.cuda.device_count()),
        "device_name": str(props.name),
        "compute_capability": f"{props.major}.{props.minor}",
        "total_vram_gb": round(total_gb, 3),
        "bf16_supported": bf16,
    })
    facts["torch"] = info

    if min_vram_gb > 0 and total_gb + 1e-9 < min_vram_gb:
        errors.append(f"GPU VRAM {total_gb:.2f} GiB is below requested minimum {min_vram_gb:.2f} GiB")
    if require_bf16 and not bf16:
        errors.append("BF16 was required but torch.cuda.is_bf16_supported() is false")
    elif not bf16:
        warnings.append("BF16 is unavailable; the trainer will fall back to non-BF16 execution")


def build_report(args: argparse.Namespace, unknown: list[str]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    facts: dict = {
        "python": sys.version.split()[0],
        "repo_root": str(ROOT),
        "ignored_trainer_args": unknown,
    }

    _inspect_index(_resolve(args.index), args.sample_rows, errors, warnings, facts)
    _check_output(_resolve(args.out), "out", errors, facts)
    _check_output(_resolve(args.best_out), "best_out", errors, facts)
    _inspect_resume(_resolve(args.resume), errors, facts)
    _inspect_control(errors, warnings, facts)
    _inspect_cuda(args.allow_no_cuda, args.require_bf16, args.min_vram_gb, errors, warnings, facts)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "facts": facts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Read-only SONICRAFT GPU renderer training preflight. Unknown trainer args are ignored."
    )
    ap.add_argument("--index")
    ap.add_argument("--out")
    ap.add_argument("--best-out")
    ap.add_argument("--resume")
    ap.add_argument("--sample-rows", type=int, default=8)
    ap.add_argument("--min-vram-gb", type=float, default=0.0)
    ap.add_argument("--require-bf16", action="store_true")
    ap.add_argument("--allow-no-cuda", action="store_true", help="CI/self-test only; production launcher does not set this")
    ap.add_argument("--json", action="store_true")
    args, unknown = ap.parse_known_args()
    if args.sample_rows < 1:
        raise SystemExit("--sample-rows must be >= 1")
    if args.min_vram_gb < 0:
        raise SystemExit("--min-vram-gb must be >= 0")

    report = build_report(args, unknown)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("SONICRAFT GPU training preflight")
        torch_info = report["facts"].get("torch", {})
        if torch_info.get("cuda_available"):
            print(
                f"GPU: {torch_info.get('device_name')} | VRAM {torch_info.get('total_vram_gb')} GiB | "
                f"CUDA {torch_info.get('torch_cuda_version')} | BF16 {torch_info.get('bf16_supported')}"
            )
        idx = report["facts"].get("index")
        if idx:
            print(f"Index: {idx.get('rows')} rows | sampled {idx.get('sampled_rows')} | {idx.get('path')}")
        for warning in report["warnings"]:
            print(f"[WARN] {warning}")
        for error in report["errors"]:
            print(f"[FAIL] {error}", file=sys.stderr)
        print("PREFLIGHT PASS" if report["ok"] else "PREFLIGHT FAILED")

    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
