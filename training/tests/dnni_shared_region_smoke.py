#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_model_shell import DnniModelHandle
from dnni_shared_region_probe import probe_shared_regions


def put_u64(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<Q", buf, off, value)


def build(path: Path, variant: int) -> None:
    block = 65536
    core_blocks = 8
    core = block * core_blocks
    weights_offset = 4096
    weights_size = core + block
    sec3_offset = weights_offset + weights_size
    sec3_size = 64
    sec4_offset = sec3_offset + sec3_size
    sec4_size = 64
    file_size = sec4_offset + sec4_size + 256

    data = bytearray(file_size)
    data[0:4] = bytes.fromhex("ff00ca7f")
    struct.pack_into("<I", data, 4, 4)
    struct.pack_into("<I", data, 8, 140)
    put_u64(data, 64, 140); put_u64(data, 72, 128)
    put_u64(data, 80, weights_offset); put_u64(data, 88, weights_size)
    put_u64(data, 96, sec3_offset); put_u64(data, 104, sec3_size)
    put_u64(data, 112, sec4_offset); put_u64(data, 120, sec4_size)

    # Blocks 1-2 and 5 are identical in all models. Others vary by model.
    for i in range(core_blocks):
        value = 0x33 if i in (1, 2, 5) else ((variant * 17 + i) & 0xFF)
        a = weights_offset + i * block
        data[a:a + block] = bytes([value]) * block
    data[-256:] = b"\x00" * 256
    path.write_bytes(data)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        models = []
        for i in range(3):
            p = root / f"m{i}.dnni"
            build(p, i + 1)
            models.append(DnniModelHandle(p))

        result = probe_shared_regions(
            models,
            shared_core_bytes=8 * 65536,
            block_bytes=65536,
        )
        clusters = result["common_clusters"]
        assert clusters == [
            {"offset": 65536, "end": 196608, "bytes": 131072, "blocks": 2},
            {"offset": 327680, "end": 393216, "bytes": 65536, "blocks": 1},
        ], clusters
        assert result["exact_common_bytes"] == 196608
        assert abs(result["exact_common_fraction"] - 0.375) < 1e-12
        print("dnni_shared_region_smoke: ok")


if __name__ == "__main__":
    main()
