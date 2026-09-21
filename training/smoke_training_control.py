from __future__ import annotations

import json
import tempfile
from pathlib import Path

from accumulation import accumulation_window_size, is_optimizer_boundary
from gpu_training_preflight import _check_output, _inspect_index
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

        latent = root / "sample_latent.npz"
        latent.write_bytes(b"smoke")
        index = root / "index.jsonl"
        index.write_text(json.dumps({"file": str(latent)}) + "\n", encoding="utf-8")
        preflight_errors: list[str] = []
        preflight_warnings: list[str] = []
        preflight_facts: dict = {}
        _inspect_index(index, 8, preflight_errors, preflight_warnings, preflight_facts)
        _check_output(root / "outputs" / "last.pt", "out", preflight_errors, preflight_facts)
        assert preflight_errors == []
        assert preflight_facts["index"]["rows"] == 1
        assert preflight_facts["index"]["sample_missing_files"] == []
        assert preflight_facts["out"]["writable"] is True
        assert preflight_facts["index"]["full_validation"] is True

        # Tail accumulation must commit a final partial window instead of dropping gradients.
        assert accumulation_window_size(0, 3, 2) == 2
        assert accumulation_window_size(1, 3, 2) == 2
        assert accumulation_window_size(2, 3, 2) == 1
        assert not is_optimizer_boundary(0, 3, 2)
        assert is_optimizer_boundary(1, 3, 2)
        assert is_optimizer_boundary(2, 3, 2)

        # Full preflight validation must catch a missing latent beyond the reporting limit.
        full_index = root / "full_index.jsonl"
        full_index.write_text(
            "".join(json.dumps({"file": str(latent)}) + "\n" for _ in range(8))
            + json.dumps({"file": str(root / "missing_latent.npz")}) + "\n",
            encoding="utf-8",
        )
        full_errors: list[str] = []
        full_warnings: list[str] = []
        full_facts: dict = {}
        _inspect_index(full_index, 2, full_errors, full_warnings, full_facts)
        assert full_facts["index"]["rows"] == 9
        assert full_facts["index"]["checked_files"] == 9
        assert full_facts["index"]["missing_file_count"] == 1
        assert full_errors

    repo = Path(__file__).resolve().parents[1]
    for rel in (
        "training/accumulation.py",
        "training/training_control.py",
        "training/training_control_panel.py",
        "training/train_ballad_renderer_pausable.py",
        "training/train_performance_planner.py",
        "training/gpu_training_preflight.py",
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
    assert "gpu_training_preflight.py" in launcher
    assert "if errorlevel 1 goto :preflight_failed" in launcher
    assert "train_ballad_renderer_pausable.py" in launcher
    assert "training_control_panel.py --open" in launcher
    assert launcher.find("gpu_training_preflight.py") < launcher.find("training_control_panel.py --open")
    assert launcher.find("training_control_panel.py --open") < launcher.find("train_ballad_renderer_pausable.py")
    assert "--out Models\\ballad_renderer_hq_v20_last.pt" in launcher
    assert "--best-out Models\\ballad_renderer_hq_v20_best.pt" in launcher

    planner_launcher = (repo / "TRAIN_PERFORMANCE_PLANNER.bat").read_text(encoding="utf-8")
    assert "training_control_panel.py --open" in planner_launcher
    assert "train_performance_planner.py" in planner_launcher
    assert "PAUSE_TRAINING.bat" in planner_launcher

    pause_doc = (repo / "docs/TRAINING_PAUSE_RESUME.md").read_text(encoding="utf-8")
    assert "TRAIN_RENDERER_GPU.bat" in pause_doc
    assert "Do not power off" in pause_doc
    assert "resuming" in pause_doc

    planner_doc = (repo / "docs/PERFORMANCE_PLANNER.md").read_text(encoding="utf-8")
    assert "explicit written control wins" in planner_doc.lower()
    assert "TRAIN_PERFORMANCE_PLANNER.bat" in planner_doc

    print("training-control smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
