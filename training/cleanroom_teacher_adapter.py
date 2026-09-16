from __future__ import annotations
"""Clean-room adapter for an authorized external audio teacher.

This module deliberately treats the teacher as an opaque renderer. It does not
parse, decrypt, copy, import, or inspect model weights. The only contract is:

    independently-authored control JSON/MIDI -> authorized runtime -> WAV

The configured command is executed as an argv vector with ``shell=False``.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess


SPEC_VERSION = "SONICRAFT-CLEANROOM-TEACHER-1.0"
_ALLOWED_PLACEHOLDERS = {
    "{control_json}", "{midi}", "{output}", "{model}", "{seed}"
}


class CleanRoomTeacherError(RuntimeError):
    pass


def _sha256_file(path: str | Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(chunk_size), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RightsDeclaration:
    authorized_runtime_use: bool = False
    output_training_allowed: bool = False
    learned_weight_release_allowed: bool = False
    commercial_use_allowed: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "RightsDeclaration":
        value = dict(value or {})
        return cls(
            authorized_runtime_use=bool(value.get("authorized_runtime_use", False)),
            output_training_allowed=bool(value.get("output_training_allowed", False)),
            learned_weight_release_allowed=bool(value.get("learned_weight_release_allowed", False)),
            commercial_use_allowed=bool(value.get("commercial_use_allowed", False)),
            notes=str(value.get("notes", "")),
        )

    @property
    def research_training_ready(self) -> bool:
        return self.authorized_runtime_use and self.output_training_allowed

    @property
    def release_training_ready(self) -> bool:
        return (
            self.research_training_ready
            and self.learned_weight_release_allowed
            and self.commercial_use_allowed
        )


@dataclass(frozen=True)
class TeacherConfig:
    name: str
    command: tuple[str, ...]
    model: str | None
    timeout_seconds: float
    fingerprint_model: bool
    rights: RightsDeclaration

    @classmethod
    def load(cls, path: str | Path) -> "TeacherConfig":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        command = tuple(str(x) for x in data.get("command", ()))
        if not command:
            raise CleanRoomTeacherError("teacher config command must be a non-empty argv list")
        if not isinstance(data.get("command"), list):
            raise CleanRoomTeacherError("teacher config command must be JSON array, not a shell string")
        for arg in command:
            for token in _ALLOWED_PLACEHOLDERS:
                arg = arg.replace(token, "")
            if "{" in arg or "}" in arg:
                raise CleanRoomTeacherError(
                    f"unknown placeholder in teacher command argument: {arg!r}"
                )
        cfg = cls(
            name=str(data.get("name") or "external_teacher"),
            command=command,
            model=(str(data["model"]) if data.get("model") else None),
            timeout_seconds=float(data.get("timeout_seconds", 180.0)),
            fingerprint_model=bool(data.get("fingerprint_model", False)),
            rights=RightsDeclaration.from_dict(data.get("rights")),
        )
        if not cfg.rights.research_training_ready:
            raise CleanRoomTeacherError(
                "external teacher is fail-closed: set both "
                "rights.authorized_runtime_use=true and "
                "rights.output_training_allowed=true only after you have verified those rights"
            )
        if any("{model}" in x for x in cfg.command) and not cfg.model:
            raise CleanRoomTeacherError("teacher command uses {model} but config has no model path")
        return cfg

    def public_identity(self) -> dict[str, Any]:
        exe = Path(self.command[0]).expanduser()
        result: dict[str, Any] = {
            "name": self.name,
            "spec_version": SPEC_VERSION,
            "command_shape_sha256": _canonical_json_hash(
                ["<MODEL>" if x == "{model}" else x for x in self.command]
            ),
            "rights": {
                "authorized_runtime_use": self.rights.authorized_runtime_use,
                "output_training_allowed": self.rights.output_training_allowed,
                "learned_weight_release_allowed": self.rights.learned_weight_release_allowed,
                "commercial_use_allowed": self.rights.commercial_use_allowed,
            },
        }
        if exe.is_file():
            result["renderer_executable_sha256"] = _sha256_file(exe)
        if self.fingerprint_model and self.model and Path(self.model).is_file():
            # A digest supports provenance without embedding or redistributing model bytes.
            result["external_model_sha256"] = _sha256_file(self.model)
        return result


class ExternalTeacher:
    def __init__(self, config: TeacherConfig):
        self.config = config

    def _argv(
        self,
        *,
        control_json: Path,
        midi: Path,
        output: Path,
        seed: int,
    ) -> list[str]:
        values = {
            "{control_json}": str(control_json),
            "{midi}": str(midi),
            "{output}": str(output),
            "{model}": str(self.config.model or ""),
            "{seed}": str(int(seed)),
        }
        argv: list[str] = []
        for raw in self.config.command:
            value = raw
            for key, replacement in values.items():
                value = value.replace(key, replacement)
            argv.append(value)
        return argv

    def render(
        self,
        *,
        control_json: str | Path,
        midi: str | Path,
        output: str | Path,
        seed: int,
    ) -> dict[str, Any]:
        control_path = Path(control_json)
        midi_path = Path(midi)
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        argv = self._argv(
            control_json=control_path,
            midi=midi_path,
            output=output_path,
            seed=seed,
        )
        try:
            proc = subprocess.run(
                argv,
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise CleanRoomTeacherError(
                f"teacher timed out after {self.config.timeout_seconds:.1f}s"
            ) from exc
        if proc.returncode != 0:
            # Keep logs short and do not persist command lines or model paths in manifests.
            stderr = (proc.stderr or proc.stdout or "").strip().replace("\r", " ")
            raise CleanRoomTeacherError(
                f"teacher renderer exited with {proc.returncode}: {stderr[-800:]}"
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise CleanRoomTeacherError("teacher renderer returned success but produced no WAV")
        return {
            "teacher_alias": self.config.name,
            "teacher_identity": self.config.public_identity(),
            "release_training_ready": self.config.rights.release_training_ready,
        }
