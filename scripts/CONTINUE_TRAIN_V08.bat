@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

REM Renderer index MUST contain DAC latents. Real physical-analysis rows do not, so they are
REM used to train/calibrate Experts and are never blindly mixed into HQ latent batches.
set BASE=datasets\processed\ballad_dac\index.jsonl
set REAL=datasets\processed\real_strings_v08\physics.jsonl
set EXPALL=datasets\processed\v08_experts\index.jsonl
set ETR0=datasets\processed\v08_experts\train_precal.jsonl
set EVA0=datasets\processed\v08_experts\val_precal.jsonl
set ETR=datasets\processed\v08_experts\train.jsonl
set EVA=datasets\processed\v08_experts\val.jsonl
set RTR0=datasets\processed\v08_renderer\train_precal.jsonl
set RVA0=datasets\processed\v08_renderer\val_precal.jsonl
set RTR=datasets\processed\v08_renderer\train.jsonl
set RVA=datasets\processed\v08_renderer\val.jsonl
set VIBCAL=checkpoints\vibrato_calibration_v08.json
set VIBARG=
set PERFARG=

REM If new public/custom real recordings were added, convert them to physical supervision first.
if not exist "%REAL%" (
  if exist datasets\manifests\real_strings_raw.jsonl call scripts\PREP_REAL_RECORDINGS_V08.bat
  if exist datasets\manifests\goodsounds_cora_2025.jsonl call scripts\PREP_REAL_RECORDINGS_V08.bat
)

if not exist "%BASE%" (
  echo [ERROR] Missing renderer DAC-latent index: %BASE%
  echo Run the codec/latent bootstrap first.
  exit /b 2
)
python training\scripts\check_release_sources.py --index "%BASE%" --registry training\dataset_registry.json || exit /b 1

REM Split the HQ renderer data independently so every renderer row is guaranteed to contain latent=.
python training\scripts\split_by_group.py --index "%BASE%" --train "%RTR0%" --val "%RVA0%" --val-percent 8 || exit /b 1

REM Experts can learn from both renderer controls and rights-cleared real recordings that have no DAC latent yet.
if exist "%REAL%" (
  python training\scripts\merge_indexes.py --input "%BASE%" --input "%REAL%" --out "%EXPALL%" || exit /b 1
) else (
  python training\scripts\merge_indexes.py --input "%BASE%" --out "%EXPALL%" || exit /b 1
  echo [INFO] No additional real-performance physics index yet; Expert training uses the current commercial-safe controls only.
)
python training\scripts\check_release_sources.py --index "%EXPALL%" --registry training\dataset_registry.json || exit /b 1
python training\scripts\split_by_group.py --index "%EXPALL%" --train "%ETR0%" --val "%EVA0%" --val-percent 8 || exit /b 1

REM Learn physical CC3 layer anchors from rights-cleared real performance statistics.
python training\fit_vibrato_calibration.py --index "%ETR0%" --out "%VIBCAL%" --min-events 12 || exit /b 1
python training\apply_vibrato_calibration.py --index "%ETR0%" --calibration "%VIBCAL%" --out-dir datasets\processed\v08_experts\train_npz --out-index "%ETR%" || exit /b 1
python training\apply_vibrato_calibration.py --index "%EVA0%" --calibration "%VIBCAL%" --out-dir datasets\processed\v08_experts\val_npz --out-index "%EVA%" || exit /b 1
python training\apply_vibrato_calibration.py --index "%RTR0%" --calibration "%VIBCAL%" --out-dir datasets\processed\v08_renderer\train_npz --out-index "%RTR%" || exit /b 1
python training\apply_vibrato_calibration.py --index "%RVA0%" --calibration "%VIBCAL%" --out-dir datasets\processed\v08_renderer\val_npz --out-index "%RVA%" || exit /b 1

python training\evaluate_controls.py --index "%ETR%" --out reports\control_coverage_v08.json || exit /b 1
python training\fit_timing_calibration.py --index "%ETR%" --out checkpoints\timing_calibration_v08.json --min-events 20 || exit /b 1

REM Per-output masks: straight notes may teach CC3 depth=0 without inventing rate/onset/jitter.
python training\train_vibrato_expert.py --index "%ETR%" --epochs 170 --batch 16 --out checkpoints\vibrato_expert_v08.pt
if errorlevel 3 (
  echo [INFO] Vibrato expert skipped: no rights-cleared vibrato depth supervision.
) else if errorlevel 1 (
  exit /b 1
) else (
  set VIBARG=--vibrato-expert checkpoints\vibrato_expert_v08_best.pt
)

python training\train_performance_experts.py --index "%ETR%" --epochs 150 --batch 16 --out checkpoints\performance_experts_v08.pt
if errorlevel 3 (
  echo [INFO] Transition/bow experts skipped: no trusted physical supervision yet.
) else if errorlevel 1 (
  exit /b 1
) else (
  set PERFARG=--performance-experts checkpoints\performance_experts_v08_best.pt
)

REM HQ teacher only receives true DAC-latent rows. Real Expert knowledge enters through the exact embedded submodules.
python training\train_ballad_renderer.py --index "%RTR%" --val-index "%RVA%" --preset hq --epochs 280 --batch 2 --accum 2 %VIBARG% %PERFARG% --expert-freeze-epochs 14 --out checkpoints\hq_v08_last.pt --best-out checkpoints\hq_v08_best.pt || exit /b 1
python training\distill_renderer.py --index "%RTR%" --teacher checkpoints\hq_v08_best.pt --epochs 130 --batch 2 --accum 2 --out checkpoints\compact_v08_distilled.pt || exit /b 1

echo.
echo [DONE] v0.8 real-recording Expert calibration + HQ teacher + compact distillation finished.
endlocal
