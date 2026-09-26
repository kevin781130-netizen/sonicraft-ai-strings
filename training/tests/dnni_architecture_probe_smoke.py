#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_model_shell import DnniModelHandle
from dnni_architecture_probe import derive_architecture


def put_u64(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<Q", buf, off, value)


def build(path: Path, groups: int) -> None:
    core = 1000
    group = 400
    sub = 100
    weights_size = core + groups * group
    weights_offset = 4096
    sec3_offset = weights_offset + weights_size
    sec3_size = 64
    sec4_offset = sec3_offset + sec3_size
    sec4_size = 64 + (groups - 8) * 12
    file_size = sec4_offset + sec4_size + 256

    data = bytearray([0x35]) * file_size
    data[0:4] = bytes.fromhex("ff00ca7f")
    struct.pack_into("<I", data, 4, 4)
    struct.pack_into("<I", data, 8, 140)
    put_u64(data, 64, 140)
    put_u64(data, 72, 128)
    put_u64(data, 80, weights_offset)
    put_u64(data, 88, weights_size)
    put_u64(data, 96, sec3_offset)
    put_u64(data, 104, sec3_size)
    put_u64(data, 112, sec4_offset)
    put_u64(data, 120, sec4_size)
    struct.pack_into("<I", data, 128, 65536)
    struct.pack_into("<I", data, 132, 200 + (groups - 8) * 12)

    w = memoryview(data)[weights_offset:weights_offset + weights_size]
    # Hard common boundary in the shared core.
    w[500:516] = b"\x00" * 16
    # Repeat a zero-run at the start of every subblock in the variable tail.
    for i in range(groups * 4):
        start = core + i * sub
        w[start:start + 40] = b"\x00" * 40

    data[-256:] = b"\x00" * 256
    path.write_bytes(data)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        models = []
        for groups in (8, 9, 11):
            p = root / f"g{groups}.dnni"
            build(p, groups)
            models.append(DnniModelHandle(p))

        result = derive_architecture(models)
        assert result["shared_core_bytes"] == 1000
        assert result["variable_tail_group_bytes"] == 400
        assert result["tail_subblock_bytes"] == 100
        assert result["subblocks_per_candidate_group"] == 4
        assert result["observed_candidate_group_counts"] == [8, 9, 11]
        assert {"offset": 500, "bytes": 16} in result["common_zero_gaps"]
        assert [x["candidate_mic_groups"] for x in result["models"]] == [8, 9, 11]
        print("dnni_architecture_probe_smoke: ok")


if __name__ == "__main__":
    main()
