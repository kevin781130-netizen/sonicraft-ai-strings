#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

import dnni_projection_bank_probe as p
from dnni_model_shell import DnniModelHandle


def put_u64(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<Q", buf, off, value)


def build(path: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    weights_offset = 4096
    weights_size = p.BANK_STARTS[-1] + p.BANK_BYTES + 4096
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

    for bank_start in p.BANK_STARTS:
        for i in range(4):
            rel = bank_start + i * p.BANK_BLOCK_BYTES
            a = weights_offset + rel
            if i == 0:
                raw = rng.normal(0, .05, p.BANK_BLOCK_BYTES // 4).astype("<f4").tobytes()
            else:
                raw = rng.normal(0, .04, p.BANK_BLOCK_BYTES // 2).astype("<f2").tobytes()
            data[a:a + p.BANK_BLOCK_BYTES] = raw

    for module in range(p.FAMILY_MODULE_COUNT):
        start = p.FAMILY_START + module * p.FAMILY_MODULE_STRIDE
        for i in range(p.FAMILY_MATRIX_COUNT):
            rel = start + i * p.FAMILY_MATRIX_BYTES
            a = weights_offset + rel
            if i == p.FAMILY_MATRIX_COUNT - 1:
                # Final block: 506 KiB cross-model shared prefix plus 6 KiB
                # instrument-specific suffix. Modules 0-2 use FP16 suffix;
                # module 3 uses FP32 suffix.
                prefix_rng = np.random.default_rng(5000 + module)
                prefix = prefix_rng.normal(
                    0, .04, p.FAMILY_LAST_SHARED_BYTES // 2
                ).astype("<f2").tobytes()
                suffix_rng = np.random.default_rng(seed * 100 + module)
                if module < 3:
                    suffix = suffix_rng.normal(
                        0, .04, p.FAMILY_LAST_VARIABLE_BYTES // 2
                    ).astype("<f2").tobytes()
                else:
                    suffix = suffix_rng.normal(
                        0, .04, p.FAMILY_LAST_VARIABLE_BYTES // 4
                    ).astype("<f4").tobytes()
                data[a:a + p.FAMILY_MATRIX_BYTES] = prefix + suffix
            else:
                # Matrices 4 and 5 are shared across synthetic models.
                local_seed = 1000 + module * 10 + i if i in (4,5) else seed * 100 + module * 10 + i
                local_rng = np.random.default_rng(local_seed)
                raw = local_rng.normal(
                    0, .04, p.FAMILY_MATRIX_BYTES // 2
                ).astype("<f2").tobytes()
                data[a:a + p.FAMILY_MATRIX_BYTES] = raw

    data[-256:] = b"\0" * 256
    path.write_bytes(data)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        models = []
        for i in range(3):
            path = root / f"m{i}.dnni"
            build(path, 20 + i)
            models.append(DnniModelHandle(path))

        result = p.probe_projection_banks(models)
        assert result["sandwich_verified"]
        assert result["candidate_fragment"]["left_bank_dimensions"] == [128,256,256,256]
        assert result["candidate_fragment"]["right_bank_dimensions"] == [128,256,256,256]
        pattern = result["middle_family"]["last_matrix_suffix_dtype_pattern"]
        assert pattern == ["float16_le", "float16_le", "float16_le", "float32_le"]
        assert result["middle_family"]["last_matrix_split_verified"]
        for module in result["middle_family"]["modules"]:
            assert all(
                x["dtype"] == "float16_le"
                for x in module["matrices"][:-1]
            )
            assert module["matrices"][4]["exact_identity_models"] == 3
            assert module["matrices"][5]["exact_identity_models"] == 3
            assert module["matrices"][6]["exact_identity_models"] == 1
            split = module["last_matrix_split"]
            assert split["shared_prefix_exact_identity_models"] == 3
            assert split["variable_tail_exact_identity_models"] == 1
            assert split["shared_prefix"]["row_major_512_candidate_rows"] == 506
            if module["index"] < 3:
                assert split["instrument_specific_suffix"]["dtype"] == "float16_le"
                assert split["instrument_specific_suffix"]["512_wide_vector_count"] == 6
            else:
                assert split["instrument_specific_suffix"]["dtype"] == "float32_le"
                assert split["instrument_specific_suffix"]["512_wide_vector_count"] == 3
        print("dnni_projection_bank_smoke: ok")


if __name__ == "__main__":
    main()
