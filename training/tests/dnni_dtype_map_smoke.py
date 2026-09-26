#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from dnni_model_shell import DnniModelHandle
from dnni_dtype_map_probe import probe_dtype_map


def put_u64(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<Q", buf, off, value)


def build(path: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    core = 1 << 20
    window = 1 << 16
    weights_offset = 4096
    tail = 4 * window
    weights_size = core + tail
    sec3_offset = weights_offset + weights_size
    sec3_size = 64
    sec4_offset = sec3_offset + sec3_size
    sec4_size = 64
    file_size = sec4_offset + sec4_size + 256

    data = bytearray(file_size)
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

    # Shared core: plausible FP16 bulk.
    bulk = rng.normal(0.0, 0.04, core // 2).astype("<f2").tobytes()
    data[weights_offset:weights_offset + core] = bulk

    # Two 64 KiB windows of plausible FP32 at an exact known location.
    fp32_start = 4 * window
    fp32_bytes = 2 * window
    f32 = rng.normal(0.0, 0.05, fp32_bytes // 4).astype("<f4").tobytes()
    a = weights_offset + fp32_start
    data[a:a + fp32_bytes] = f32

    # Tail is irrelevant to dtype-map smoke.
    data[-256:] = b"\x00" * 256
    path.write_bytes(data)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        models = []
        for i in range(3):
            p = root / f"m{i}.dnni"
            build(p, 100 + i)
            models.append(DnniModelHandle(p))

        result = probe_dtype_map(
            models,
            shared_core_bytes=1 << 20,
            window_bytes=1 << 16,
        )
        spans = result["float32_candidate_spans"]
        assert len(spans) == 1, spans
        assert spans[0]["offset"] == 4 * (1 << 16), spans
        assert spans[0]["bytes"] == 2 * (1 << 16), spans
        assert spans[0]["element_count"] == (2 * (1 << 16)) // 4
        assert result["bulk_non_candidate_windows_fp16_plausible_fraction"] > 0.9
        print("dnni_dtype_map_smoke: ok")


if __name__ == "__main__":
    main()
