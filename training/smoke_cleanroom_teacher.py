from __future__ import annotations
"""Small local smoke test for the clean-room dataset builder (no external teacher)."""
from pathlib import Path
import json
import tempfile

from build_cleanroom_teacher_dataset import build


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="sonicraft_cleanroom_") as td:
        out = Path(td) / "run"
        report = build(
            out_dir=out,
            count=8,
            seed=1337,
            seconds=0.35,
            sample_rate=48000,
            teacher_config=None,
            dry_run=False,
        )
        assert report["requested"] == 8
        assert report["render_errors"] == 0
        index = out / "index.jsonl"
        assert index.is_file()
        rows = [json.loads(x) for x in index.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert rows
        assert all(r["dataset"] == "synthetic_cleanroom_bowed_v18" for r in rows)
        assert all(r["proprietary_model_bytes_embedded"] is False for r in rows)
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
