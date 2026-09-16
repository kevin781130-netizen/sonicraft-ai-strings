from __future__ import annotations

import json
import tempfile
from pathlib import Path

from training_control import PauseController, _strip_resume_arg, clear_pause, pause_requested, read_status, request_pause, write_status


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sonicraft_pause_smoke_") as td:
        root = Path(td)
        pause_file = root / "pause.json"
        status_file = root / "status.json"

        assert not pause_requested(pause_file)
        request_pause(pause_file, source="smoke")
        assert pause_requested(pause_file)
        raw = json.loads(pause_file.read_text(encoding="utf-8"))
        assert raw["requested"] is True
        assert raw["source"] == "smoke"

        ctl = PauseController(pause_file)
        assert ctl.requested()
        assert ctl.reason() == "smoke"
        ctl.consume()
        assert not pause_requested(pause_file)

        write_status({
            "state": "paused",
            "message": "smoke",
            "checkpoint": str(root / "checkpoint.pt"),
            "pause_file": str(pause_file),
            "epoch": 3,
            "global_step": 42,
        }, status_file)
        status = read_status(status_file)
        assert status["state"] == "paused"
        assert status["epoch"] == 3
        assert status["global_step"] == 42
        assert status["pause_requested"] is False

        request_pause(pause_file, source="smoke_again")
        assert read_status(status_file)["pause_requested"] is True
        assert clear_pause(pause_file)
        assert not clear_pause(pause_file)

        args = ["training/train.py", "--resume", "old.pt", "--epochs", "100", "--resume=older.pt"]
        assert _strip_resume_arg(args) == ["training/train.py", "--epochs", "100"]

    repo = Path(__file__).resolve().parents[1]
    for rel in (
        "training/training_control.py",
        "training/training_control_panel.py",
        "training/train_ballad_renderer_pausable.py",
    ):
        src = (repo / rel).read_text(encoding="utf-8")
        compile(src, rel, "exec")

    trainer = (repo / "training/train_ballad_renderer_pausable.py").read_text(encoding="utf-8")
    assert "optimizer_boundary" in trainer
    assert "safe_pause(ep" in trainer
    assert '"optimizer": opt.state_dict()' in trainer
    assert '"scheduler": sched.state_dict()' in trainer
    assert '"rng_state": rng_state()' in trainer

    launcher = (repo / "TRAIN_RENDERER_GPU.bat").read_text(encoding="utf-8")
    assert "train_ballad_renderer_pausable.py" in launcher
    assert "training_control_panel.py --open" in launcher
    assert "--out Models\\ballad_renderer_hq_v20_last.pt" in launcher
    assert "--best-out Models\\ballad_renderer_hq_v20_best.pt" in launcher

    pause_doc = (repo / "docs/TRAINING_PAUSE_RESUME.md").read_text(encoding="utf-8")
    assert "TRAIN_RENDERER_GPU.bat" in pause_doc
    assert "Do not power off" in pause_doc
    assert "resuming" in pause_doc

    print("training-control smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
