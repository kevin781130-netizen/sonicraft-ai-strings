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
from dnni_tensor_shape_probe import (
    MODULE_COUNT,
    MODULE_STRIDE_BYTES,
    MATRIX_BYTES,
    probe_tensor_shapes,
)


def put_u64(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<Q", buf, off, value)


def build_model(path: Path, bases, seed: int) -> None:
    rng = np.random.default_rng(seed)
    weights_offset = 4096
    weights_size = MODULE_COUNT * MODULE_STRIDE_BYTES
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

    for module in range(MODULE_COUNT):
        module_base = weights_offset + module * MODULE_STRIDE_BYTES
        mats = bases[module]

        # Matrix 0: model-specific column ordering.
        col_perm = rng.permutation(512)
        m0 = mats[0][:, col_perm]

        # Matrices 1-3: model-specific row ordering.
        variable = [m0]
        for i in (1, 2, 3):
            variable.append(mats[i][rng.permutation(512), :])

        # Matrices 4-6: exact shared bytes.
        all_mats = variable + [mats[i] for i in (4, 5, 6)]
        for i, mat in enumerate(all_mats):
            a = module_base + i * MATRIX_BYTES
            data[a:a + MATRIX_BYTES] = mat.astype("<u2", copy=False).tobytes()

    data[-256:] = b"\x00" * 256
    path.write_bytes(data)


def main() -> None:
    rng = np.random.default_rng(42)
    bases = [
        [
            rng.integers(0, 65535, size=(512, 512), dtype=np.uint16)
            for _ in range(7)
        ]
        for _ in range(MODULE_COUNT)
    ]

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        models = []
        for i in range(3):
            p = root / f"m{i}.dnni"
            build_model(p, bases, 100 + i)
            models.append(DnniModelHandle(p))

        result = probe_tensor_shapes(models)
        assert result["unique_verified_shape"] == {"rows": 512, "cols": 512}
        survivors = [
            (x["rows"], x["cols"])
            for x in result["candidate_shapes"]
            if x["survives_all_modules"]
        ]
        assert survivors == [(512, 512)], survivors

        for module in result["modules"]:
            assert all(
                m["same_fp16_value_multiset_across_models"]
                for m in module["variable_matrices"]
            )
            assert all(
                m["exact_byte_identity_across_models"]
                for m in module["shared_matrices"]
            )

        print("dnni_tensor_shape_smoke: ok")


if __name__ == "__main__":
    main()
