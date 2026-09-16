from __future__ import annotations
"""One-command dependency-light validation for release-contract changes."""
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"

COMPILE_TARGETS = (
    "training/phrase_curriculum.py",
    "training/phrase_provenance.py",
    "training/phrase_release_provenance.py",
    "training/release_transition_gate.py",
    "training/transition_promotion.py",
    "training/train_ballad_renderer.py",
    "training/distill_renderer.py",
    "training/reflow_distill_renderer.py",
    "training/shortcut_distill_renderer.py",
    "training/smoke_release_schema8_end_to_end.py",
    "training/scripts/build_phrase_finetune_index.py",
    "training/scripts/build_transition_promotion.py",
    "training/scripts/evaluate_renderer_transitions.py",
    "training/scripts/seal_transition_promotion.py",
    "training/scripts/stamp_phrase_training_provenance.py",
    "training/scripts/build_release_model_manifest.py",
    "training/scripts/commercial_release_gate.py",
)

SMOKE_SCRIPTS = (
    "smoke_release_schema8.py",
    "smoke_phrase_provenance.py",
    "smoke_phrase_release_provenance.py",
    "smoke_release_schema8_end_to_end.py",
)


def main() -> None:
    for rel in COMPILE_TARGETS:
        py_compile.compile(str(ROOT / rel), doraise=True)
    print(f"compiled {len(COMPILE_TARGETS)} release-contract modules")

    for script in SMOKE_SCRIPTS:
        subprocess.run([sys.executable, script], cwd=TRAINING, check=True)

    print("release contract smoke: PASS")


if __name__ == "__main__":
    main()
