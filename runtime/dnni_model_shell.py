#!/usr/bin/env python3
from __future__ import annotations

"""SONICRAFT DNNI model shell.

Research/interoperability loader for user-provided DNNI v4 containers.

This module intentionally treats payload sections as opaque byte ranges. It does not
guess tensor names/shapes, decrypt protected content, bypass signatures/licensing, or
claim compatibility with a proprietary renderer.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, BinaryIO
import argparse
import hashlib
import json
import struct

MAGIC = bytes.fromhex("ff00ca7f")
SUPPORTED_VERSION = 4
V4_HEADER_SIZE = 140
V4_SECTION_TABLE_OFFSET = 64
V4_SECTION_COUNT = 4
V4_FOOTER_BYTES = 256
DEFAULT_CHUNK = 8 << 20

SECTION_NAMES = ("section1", "weights", "section3", "section4")


class DnniFormatError(RuntimeError):
    pass


@dataclass(frozen=True)
class DnniSection:
    name: str
    offset: int
    size: int

    @property
    def end(self) -> int:
        return self.offset + self.size


@dataclass(frozen=True)
class DnniHeader:
    magic_hex: str
    version: int
    header_size: int
    sections: tuple[DnniSection, ...]
    opaque_prefix_hex: str
    opaque_tail_hex: str
    footer_offset: int
    footer_size: int
    file_size: int

    def section(self, name: str) -> DnniSection:
        aliases = {"section2": "weights", "weights_fp16": "weights"}
        target = aliases.get(name, name)
        for s in self.sections:
            if s.name == target:
                return s
        raise KeyError(name)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["sections"] = [asdict(s) | {"end": s.end} for s in self.sections]
        return out


@dataclass(frozen=True)
class RegistryMatch:
    source_uuid: str | None
    label_zh: str | None
    label_en: str | None
    instrument_role: str | None
    instrument_family: str | None
    identity_status: str | None
    identity_authority: str | None
    match_method: str

    def to_dict(self) -> dict:
        return asdict(self)


class SectionStream:
    """Bounded file reader for one DNNI section."""

    def __init__(self, path: str | Path, section: DnniSection):
        self.path = Path(path)
        self.section = section
        self._fh: BinaryIO | None = None
        self._remaining = section.size

    def __enter__(self) -> "SectionStream":
        self._fh = self.path.open("rb")
        self._fh.seek(self.section.offset)
        self._remaining = self.section.size
        return self

    def read(self, size: int = -1) -> bytes:
        if self._fh is None:
            raise RuntimeError("SectionStream must be used as a context manager")
        if self._remaining <= 0:
            return b""
        if size is None or size < 0:
            size = self._remaining
        size = min(int(size), self._remaining)
        data = self._fh.read(size)
        self._remaining -= len(data)
        return data

    @property
    def remaining(self) -> int:
        return self._remaining

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            self._fh.close()
        self._fh = None


def _sha256_range(path: Path, offset: int, size: int, chunk_size: int = DEFAULT_CHUNK) -> str:
    h = hashlib.sha256()
    remaining = int(size)
    with path.open("rb") as f:
        f.seek(int(offset))
        while remaining:
            b = f.read(min(chunk_size, remaining))
            if not b:
                raise DnniFormatError(
                    f"{path}: unexpected EOF while hashing range offset={offset} size={size}"
                )
            h.update(b)
            remaining -= len(b)
    return h.hexdigest()


def sha256_file(path: str | Path, chunk_size: int = DEFAULT_CHUNK) -> str:
    p = Path(path)
    return _sha256_range(p, 0, p.stat().st_size, chunk_size)


def parse_dnni_header(path: str | Path) -> DnniHeader:
    p = Path(path)
    file_size = p.stat().st_size
    if file_size < V4_HEADER_SIZE + V4_FOOTER_BYTES:
        raise DnniFormatError(f"{p}: too small to be a DNNI v4 container")

    with p.open("rb") as f:
        header = f.read(V4_HEADER_SIZE)
    if len(header) != V4_HEADER_SIZE:
        raise DnniFormatError(f"{p}: short header")

    if header[:4] != MAGIC:
        raise DnniFormatError(
            f"{p}: bad magic {header[:4].hex()}, expected {MAGIC.hex()}"
        )
    version = struct.unpack_from("<I", header, 4)[0]
    header_size = struct.unpack_from("<I", header, 8)[0]
    if version != SUPPORTED_VERSION:
        raise DnniFormatError(f"{p}: unsupported DNNI version {version}")
    if header_size != V4_HEADER_SIZE:
        raise DnniFormatError(
            f"{p}: unexpected v4 header size {header_size}, expected {V4_HEADER_SIZE}"
        )

    sections = []
    cursor = V4_SECTION_TABLE_OFFSET
    for name in SECTION_NAMES:
        offset, size = struct.unpack_from("<QQ", header, cursor)
        cursor += 16
        if size <= 0:
            raise DnniFormatError(f"{p}: {name} has non-positive size {size}")
        if offset < header_size:
            raise DnniFormatError(f"{p}: {name} starts inside header")
        if offset + size > file_size:
            raise DnniFormatError(f"{p}: {name} exceeds file bounds")
        sections.append(DnniSection(name=name, offset=offset, size=size))

    ordered = sorted(sections, key=lambda s: s.offset)
    if ordered != sections:
        raise DnniFormatError(f"{p}: section table is not ordered by offset")
    for prev, cur in zip(ordered, ordered[1:]):
        if prev.end > cur.offset:
            raise DnniFormatError(f"{p}: overlapping sections {prev.name}/{cur.name}")

    footer_offset = sections[-1].end
    footer_size = file_size - footer_offset
    if footer_size != V4_FOOTER_BYTES:
        raise DnniFormatError(
            f"{p}: unexpected footer/trailer size {footer_size}, expected {V4_FOOTER_BYTES}"
        )

    return DnniHeader(
        magic_hex=MAGIC.hex(),
        version=version,
        header_size=header_size,
        sections=tuple(sections),
        opaque_prefix_hex=header[12:64].hex(),
        opaque_tail_hex=header[128:140].hex(),
        footer_offset=footer_offset,
        footer_size=footer_size,
        file_size=file_size,
    )


def load_registry(path: str | Path) -> dict:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    rows = data.get("sources")
    if not isinstance(rows, list):
        raise ValueError(f"{p}: registry sources must be a list")
    return data


class DnniModelHandle:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.header = parse_dnni_header(self.path)
        self._source_sha256: str | None = None
        self._section_hashes: dict[str, str] = {}
        self.registry_match: RegistryMatch | None = None

    @property
    def source_sha256(self) -> str:
        if self._source_sha256 is None:
            self._source_sha256 = sha256_file(self.path)
        return self._source_sha256

    def section(self, name: str) -> DnniSection:
        return self.header.section(name)

    def open_section(self, name: str) -> SectionStream:
        return SectionStream(self.path, self.section(name))

    def iter_section_chunks(self, name: str, chunk_size: int = DEFAULT_CHUNK) -> Iterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        with self.open_section(name) as stream:
            while stream.remaining:
                b = stream.read(min(chunk_size, stream.remaining))
                if not b:
                    break
                yield b

    def hash_section(self, name: str) -> str:
        canonical = self.section(name).name
        if canonical not in self._section_hashes:
            s = self.section(canonical)
            self._section_hashes[canonical] = _sha256_range(
                self.path, s.offset, s.size
            )
        return self._section_hashes[canonical]

    @property
    def weights_sha256(self) -> str:
        return self.hash_section("weights")

    def match_registry(self, registry: dict) -> RegistryMatch | None:
        rows = registry.get("sources") or []
        full_hash = self.source_sha256
        for row in rows:
            if str(row.get("source_dnni_sha256") or "").lower() == full_hash:
                self.registry_match = _registry_match(row, "source_sha256")
                return self.registry_match

        weights_hash = self.weights_sha256
        candidates = [
            row for row in rows
            if str(row.get("weights_sha256") or "").lower() == weights_hash
        ]
        if len(candidates) == 1:
            self.registry_match = _registry_match(candidates[0], "weights_sha256")
            return self.registry_match
        if len(candidates) > 1:
            raise DnniFormatError(
                f"{self.path}: registry has duplicate weights_sha256 identities"
            )

        self.registry_match = None
        return None

    def summary(self, include_hashes: bool = True) -> dict:
        out = {
            "path": str(self.path),
            "filename": self.path.name,
            "header": self.header.to_dict(),
        }
        if include_hashes:
            out["source_sha256"] = self.source_sha256
            out["weights_sha256"] = self.weights_sha256
        out["identity"] = (
            self.registry_match.to_dict() if self.registry_match is not None else None
        )
        return out


def _registry_match(row: dict, method: str) -> RegistryMatch:
    return RegistryMatch(
        source_uuid=row.get("source_uuid"),
        label_zh=row.get("label_zh"),
        label_en=row.get("label_en"),
        instrument_role=row.get("instrument_role"),
        instrument_family=row.get("instrument_family"),
        identity_status=row.get("identity_status"),
        identity_authority=row.get("identity_authority"),
        match_method=method,
    )


class DnniModelCatalog:
    def __init__(self, registry: dict | None = None):
        self.registry = registry
        self.models: list[DnniModelHandle] = []

    def scan(self, directory: str | Path, recursive: bool = False) -> list[DnniModelHandle]:
        root = Path(directory)
        pattern = "**/*.dnni" if recursive else "*.dnni"
        found = []
        for path in sorted(root.glob(pattern)):
            model = DnniModelHandle(path)
            if self.registry is not None:
                model.match_registry(self.registry)
            found.append(model)
        self.models = found
        return found

    def by_role(self) -> dict[str, DnniModelHandle]:
        out: dict[str, DnniModelHandle] = {}
        for model in self.models:
            if model.registry_match and model.registry_match.instrument_role:
                role = model.registry_match.instrument_role
                if role in out:
                    raise DnniFormatError(f"duplicate instrument role in catalog: {role}")
                out[role] = model
        return out


def _default_registry() -> Path:
    return Path(__file__).resolve().parents[1] / "training" / "configs" / "dnni_source_labels.json"


def _human_summary(model: DnniModelHandle) -> str:
    ident = model.registry_match
    lines = [
        f"file: {model.path}",
        f"dnni: v{model.header.version}  size={model.header.file_size:,}  magic={model.header.magic_hex}",
    ]
    if ident:
        lines.append(
            "identity: "
            f"{ident.label_en or '?'} / {ident.label_zh or '?'} "
            f"[{ident.instrument_role or '?'}] via {ident.match_method}"
        )
    else:
        lines.append("identity: unknown")
    lines.append(f"source_sha256: {model.source_sha256}")
    lines.append(f"weights_sha256: {model.weights_sha256}")
    for s in model.header.sections:
        lines.append(f"{s.name}: offset={s.offset:,} size={s.size:,} end={s.end:,}")
    lines.append(
        f"footer: offset={model.header.footer_offset:,} size={model.header.footer_size:,}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inspect and catalog DNNI v4 model containers.")
    ap.add_argument("--registry", default=str(_default_registry()))
    sub = ap.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Inspect one DNNI file.")
    p_inspect.add_argument("path")
    p_inspect.add_argument("--json", action="store_true")

    p_scan = sub.add_parser("scan", help="Scan a directory of DNNI files.")
    p_scan.add_argument("directory")
    p_scan.add_argument("--recursive", action="store_true")
    p_scan.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    registry = load_registry(args.registry)

    if args.command == "inspect":
        model = DnniModelHandle(args.path)
        model.match_registry(registry)
        if args.json:
            print(json.dumps(model.summary(), indent=2, ensure_ascii=False))
        else:
            print(_human_summary(model))
        return 0

    if args.command == "scan":
        catalog = DnniModelCatalog(registry)
        models = catalog.scan(args.directory, recursive=args.recursive)
        if args.json:
            print(json.dumps([m.summary() for m in models], indent=2, ensure_ascii=False))
        else:
            for i, m in enumerate(models):
                if i:
                    print()
                print(_human_summary(m))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
