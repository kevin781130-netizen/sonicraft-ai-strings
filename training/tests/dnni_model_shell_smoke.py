#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_model_shell import DnniModelHandle, DnniModelCatalog, DnniFormatError

MAGIC = bytes.fromhex("ff00ca7f")

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def build(path: Path, footer_byte: int = 0xA5):
    section1 = b"META" * 7
    weights = b"\x00\x3c\x00\x40" * 31
    section3 = b"CTRL" * 9
    section4 = b"ROOM" * 5

    off1 = 140
    off2 = 256
    off3 = off2 + len(weights) + 16
    off4 = off3 + len(section3)
    footer = bytes([footer_byte]) * 256

    size = off4 + len(section4) + len(footer)
    data = bytearray(size)
    data[0:4] = MAGIC
    struct.pack_into("<I", data, 4, 4)
    struct.pack_into("<I", data, 8, 140)

    pos = 64
    for off, n in (
        (off1, len(section1)),
        (off2, len(weights)),
        (off3, len(section3)),
        (off4, len(section4)),
    ):
        struct.pack_into("<QQ", data, pos, off, n)
        pos += 16

    data[off1:off1+len(section1)] = section1
    data[off2:off2+len(weights)] = weights
    data[off3:off3+len(section3)] = section3
    data[off4:off4+len(section4)] = section4
    data[-256:] = footer
    path.write_bytes(data)
    return bytes(data), weights

def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p1 = root / "known.dnni"
        raw1, weights = build(p1, 0xA5)
        registry = {"sources": [{
            "source_uuid": "synthetic-1",
            "source_dnni_sha256": sha(raw1),
            "weights_sha256": sha(weights),
            "label_zh": "測試",
            "label_en": "Synthetic",
            "instrument_role": "synthetic",
            "instrument_family": "test",
            "identity_status": "confirmed",
            "identity_authority": "test",
        }]}

        model = DnniModelHandle(p1)
        match = model.match_registry(registry)
        assert match and match.match_method == "source_sha256"
        assert model.section("weights").size == len(weights)

        with model.open_section("weights") as stream:
            assert stream.read(7) == weights[:7]
            assert stream.remaining == len(weights) - 7
            assert stream.read() == weights[7:]
            assert stream.read() == b""

        p2 = root / "fallback.dnni"
        build(p2, 0x5A)
        fallback = DnniModelHandle(p2)
        match2 = fallback.match_registry(registry)
        assert match2 and match2.match_method == "weights_sha256"

        catalog = DnniModelCatalog(registry)
        found = catalog.scan(root)
        assert len(found) == 2
        assert all(x.registry_match is not None for x in found)

        bad = root / "bad.dnni"
        bad.write_bytes(b"not dnni")
        try:
            DnniModelHandle(bad)
        except DnniFormatError:
            pass
        else:
            raise AssertionError("invalid file must fail closed")

        print("dnni_model_shell_smoke: ok")

if __name__ == "__main__":
    main()
