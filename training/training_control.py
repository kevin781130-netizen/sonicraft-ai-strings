from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAUSE_FILE = ROOT / "training" / ".pause_training"
DEFAULT_STATUS_FILE = ROOT / "training" / ".training_status.json"


def _path(value: str | Path | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value else default.resolve()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def request_pause(path: str | Path | None = None, source: str = "manual") -> Path:
    pause = _path(path, DEFAULT_PAUSE_FILE)
    _atomic_json(pause, {
        "requested": True,
        "source": str(source),
        "requested_at_unix": time.time(),
        "requested_by_pid": os.getpid(),
    })
    return pause


def clear_pause(path: str | Path | None = None) -> bool:
    pause = _path(path, DEFAULT_PAUSE_FILE)
    existed = pause.exists()
    pause.unlink(missing_ok=True)
    return existed


def pause_requested(path: str | Path | None = None) -> bool:
    return _path(path, DEFAULT_PAUSE_FILE).exists()


def write_status(payload: dict, path: str | Path | None = None) -> Path:
    target = _path(path, DEFAULT_STATUS_FILE)
    body = dict(payload)
    body["updated_at_unix"] = time.time()
    _atomic_json(target, body)
    return target


def read_status(path: str | Path | None = None) -> dict:
    target = _path(path, DEFAULT_STATUS_FILE)
    if not target.exists():
        return {
            "state": "idle",
            "message": "No pausable training status has been written yet.",
            "status_file": str(target),
            "pause_requested": pause_requested(),
        }
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("status JSON is not an object")
    except Exception as exc:
        return {
            "state": "error",
            "message": f"Cannot read training status: {exc}",
            "status_file": str(target),
            "pause_requested": pause_requested(),
        }
    data["status_file"] = str(target)
    data["pause_requested"] = pause_requested(data.get("pause_file"))
    return data


class PauseController:
    """File + signal based safe-pause request collector.

    Signal handlers do not throw. They only request a pause; the trainer checks
    `requested()` at a safe optimizer boundary, writes a checkpoint, and exits.
    """

    def __init__(self, pause_file: str | Path | None = None):
        self.pause_file = _path(pause_file, DEFAULT_PAUSE_FILE)
        self.signal_name: str | None = None
        self._installed = False

    def _handle_signal(self, signum, _frame) -> None:
        try:
            import signal
            name = signal.Signals(signum).name
        except Exception:
            name = str(signum)
        self.signal_name = name
        request_pause(self.pause_file, source=f"signal:{name}")
        print(
            f"\n[SAFE PAUSE] {name} received. Saving at the next optimizer boundary...",
            flush=True,
        )

    def install_signal_handlers(self) -> None:
        if self._installed:
            return
        import signal
        for sig_name in ("SIGINT", "SIGTERM"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                try:
                    signal.signal(sig, self._handle_signal)
                except (OSError, RuntimeError, ValueError):
                    pass
        self._installed = True

    def requested(self) -> bool:
        return self.signal_name is not None or self.pause_file.exists()

    def reason(self) -> str:
        if self.signal_name:
            return f"signal:{self.signal_name}"
        if self.pause_file.exists():
            try:
                data = json.loads(self.pause_file.read_text(encoding="utf-8"))
                return str(data.get("source") or "pause_file")
            except Exception:
                return "pause_file"
        return ""

    def consume(self) -> None:
        clear_pause(self.pause_file)
        self.signal_name = None


def _strip_resume_arg(argv: list[str]) -> list[str]:
    out: list[str] = []
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token == "--resume":
            skip_next = True
            continue
        if token.startswith("--resume="):
            continue
        out.append(token)
    return out


def resume_last(status_file: str | Path | None = None) -> subprocess.Popen:
    status = read_status(status_file)
    if status.get("state") != "paused":
        raise RuntimeError(f"Training is not paused (state={status.get('state', 'unknown')}).")
    checkpoint = str(status.get("checkpoint") or "").strip()
    if not checkpoint or not Path(checkpoint).exists():
        raise RuntimeError(f"Paused checkpoint does not exist: {checkpoint or '<missing>'}")
    argv = status.get("argv")
    if not isinstance(argv, list) or not argv:
        raise RuntimeError("Paused status has no restart command.")
    python_exe = str(status.get("python_executable") or sys.executable)
    cleaned = _strip_resume_arg([str(x) for x in argv])
    pause_file = status.get("pause_file")
    clear_pause(pause_file)
    cmd = [python_exe, *cleaned, "--resume", checkpoint]

    # Mark the status before spawning so a double-click cannot launch duplicate
    # training processes while the child is still initializing.
    status_path = _path(status_file, DEFAULT_STATUS_FILE)
    pending = dict(status)
    pending.pop("status_file", None)
    pending.pop("pause_requested", None)
    pending["state"] = "resuming"
    pending["message"] = "Resume requested; launching the saved training command."
    write_status(pending, status_path)
    try:
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, cwd=str(ROOT), creationflags=creationflags)
    except Exception:
        pending["state"] = "paused"
        pending["message"] = "Resume launch failed; checkpoint remains paused and resumable."
        write_status(pending, status_path)
        raise
    return proc


def main() -> int:
    ap = argparse.ArgumentParser(description="SONICRAFT safe training pause/resume control.")
    ap.add_argument("--pause-file")
    ap.add_argument("--status-file")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("pause")
    sub.add_parser("resume")
    sub.add_parser("status")
    sub.add_parser("clear")
    args = ap.parse_args()

    if args.command == "pause":
        path = request_pause(args.pause_file, source="cli")
        print(f"Pause requested: {path}")
        print("The trainer will save a checkpoint at the next optimizer boundary, then exit.")
        return 0
    if args.command == "clear":
        print("Cleared" if clear_pause(args.pause_file) else "No pause request was present")
        return 0
    if args.command == "status":
        print(json.dumps(read_status(args.status_file), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "resume":
        try:
            proc = resume_last(args.status_file)
        except Exception as exc:
            print(f"Resume failed: {exc}", file=sys.stderr)
            return 2
        print(f"Training resumed as PID {proc.pid}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
