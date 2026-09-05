@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

set MARGS=
if exist datasets\manifests\iowa_strings.jsonl set MARGS=!MARGS! --manifest datasets\manifests\iowa_strings.jsonl
if exist datasets\manifests\tinysol_strings.jsonl set MARGS=!MARGS! --manifest datasets\manifests\tinysol_strings.jsonl
if exist datasets\manifests\goodsounds_cora_2025.jsonl set MARGS=!MARGS! --manifest datasets\manifests\goodsounds_cora_2025.jsonl
if "!MARGS!"=="" (
  echo [ERROR] No commercial-safe codec audio manifests found.
  echo Run DOWNLOAD_IOWA_STRINGS.bat and/or DOWNLOAD_TINYSOL.bat and/or DOWNLOAD_GOODSOUNDS_CORA_2025.bat first.
  exit /b 2
)
if not exist datasets\processed\ballad_isolated\index.jsonl (
  echo [ERROR] Missing datasets\processed\ballad_isolated\index.jsonl.
  echo Keep your existing copyright-clean isolated-audio/control bootstrap, then rerun this script.
  exit /b 2
)

echo [1/7] Train 48k / 64-d / 1600x strings-only VAE. Encoder+discriminator are training-only.
python training\train_codec.py !MARGS! --arch vae64 --width 24 --epochs 80 --batch 4 --out checkpoints\strings_vae64.pt --decoder-out checkpoints\strings_vae64_decoder.pt || exit /b 1

echo [2/7] Encode a NEW VAE64 latent corpus. Legacy DAC latents are preserved untouched.
python training\scripts\encode_vae64_latents.py --index datasets\processed\ballad_isolated\index.jsonl --codec checkpoints\strings_vae64.pt --out datasets\processed\ballad_vae64 || exit /b 1
python training\scripts\check_release_sources.py --index datasets\processed\ballad_vae64\index.jsonl --registry training\dataset_registry.json || exit /b 1

echo [3/7] Group-safe split.
python training\scripts\split_by_group.py --index datasets\processed\ballad_vae64\index.jsonl --train datasets\processed\ballad_vae64\train.jsonl --val datasets\processed\ballad_vae64\val.jsonl --val-percent 8 || exit /b 1

echo [4/7] Train 64-d HQ teacher. HQ remains optional; Standard ships the smaller frontier student.
python training\train_ballad_renderer.py --index datasets\processed\ballad_vae64\train.jsonl --val-index datasets\processed\ballad_vae64\val.jsonl --preset hq_dit --epochs 240 --batch 2 --accum 2 --out checkpoints\ballad_renderer_hq_v16_last.pt --best-out checkpoints\ballad_renderer_hq_v16_best.pt || exit /b 1

echo [5/7] Knowledge-distill to the 3.82M frontier renderer.
python training\distill_renderer.py --index datasets\processed\ballad_vae64\train.jsonl --teacher checkpoints\ballad_renderer_hq_v16_best.pt --student-preset frontier_dit --epochs 110 --batch 2 --accum 2 --out checkpoints\ballad_renderer_frontier_v16_distilled.pt || exit /b 1

echo [6/7] Reflow to a four-step target without adding runtime parameters.
python training\reflow_distill_renderer.py --index datasets\processed\ballad_vae64\train.jsonl --teacher checkpoints\ballad_renderer_frontier_v16_distilled.pt --student-preset frontier_dit --teacher-steps 24 --target-steps 4 --epochs 35 --batch 1 --out checkpoints\ballad_renderer_frontier_best.pt || exit /b 1

echo [7/7] Architecture/runtime regression.
python training\smoke_v16.py || exit /b 1

echo.
echo [DONE] v1.6 frontier training chain finished.
echo Next acoustic gates: codec ABX vs DAC, 24-step vs 4-step ABX, MIDI-lock, transitions, latency/VRAM, then ORT parity/size benchmark.
endlocal
