from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import shlex
import subprocess
import tempfile


class SonicraftExternalAdapter:
    """Optional process-boundary bridge for a separately installed Sonicraft build.

    The adapter deliberately imports no Sonicraft code. The configured executable
    owns its own licensing/installation boundary and exchanges JSON files only.
    """
    def __init__(self, command: list[str] | str, *, timeout_s: float = 120.0):
        self.command = shlex.split(command) if isinstance(command, str) else [str(x) for x in command]
        if not self.command:
            raise ValueError("Sonicraft external command is empty")
        self.timeout_s = max(1.0, float(timeout_s))

    def run(self, payload: dict[str, Any], *, workdir: str | Path | None = None) -> dict[str, Any]:
        wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="stringcc-sonicraft-"))
        wd.mkdir(parents=True, exist_ok=True)
        inp = wd / "stringcc_to_sonicraft.json"; out = wd / "sonicraft_to_stringcc.json"
        inp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = [token.format(input=str(inp.resolve()), output=str(out.resolve()), workdir=str(wd.resolve())) for token in self.command]
        proc = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, timeout=self.timeout_s, shell=False)
        if proc.returncode != 0:
            raise RuntimeError(f"External Sonicraft command failed ({proc.returncode}): {proc.stderr[-2000:]}")
        if not out.exists():
            raise FileNotFoundError(f"External Sonicraft command did not create {out}")
        result = json.loads(out.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError("External Sonicraft response must be a JSON object")
        result.setdefault("_adapter", {"returncode": proc.returncode, "stdout_tail": proc.stdout[-1000:]})
        return result
