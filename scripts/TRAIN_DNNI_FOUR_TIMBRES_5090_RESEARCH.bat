@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0.."
title SONICRAFT DNNI 4-Timbre RTX 5090 Training

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

set "ROOT=datasets\dnni_four_timbres"
set "RAW=%ROOT%\rendered\index.jsonl"
set "LATENTS=%ROOT%\latents\index.jsonl"
set "STOPFILE=%CD%\checkpoints\dnni4_stop_after_epoch.flag"
set "SONICRAFT_STOP_FILE=%STOPFILE%"
set "LOGROOT=logs\dnni5090"
set "PYTHONUNBUFFERED=1"

if not exist checkpoints mkdir checkpoints
if not exist "%LOGROOT%" mkdir "%LOGROOT%"

set "RECIPECMD=checkpoints\dnni4_training_recipe.cmd"
python training\scripts\dnni_training_config.py --write-cmd "%RECIPECMD%" || goto :FAIL
call "%RECIPECMD%" || goto :FAIL
echo [RECIPE FINGERPRINT] !SONICRAFT_RECIPE_FINGERPRINT!
echo [CUDA ALLOCATOR] !PYTORCH_CUDA_ALLOC_CONF!
if exist "%STOPFILE%" (
  echo [INFO] Clearing stale safe-stop request from previous run.
  del /q "%STOPFILE%" >nul 2>&1
)

echo ============================================================
echo SONICRAFT AI Strings - DNNI Four Timbres - RTX 5090
echo AUTO RESUME ENABLED
echo ============================================================
echo.
echo Safe stop: double-click STOP_DNNI_5090.bat ^(after current batch/step^)
echo Resume:    double-click TRAIN_DNNI_5090.bat again
echo Status:    double-click STATUS_DNNI_5090.bat
echo.

if not exist "%ROOT%\source\bundle_manifest.json" (
  echo [ERROR] Four DNNI source packages have not been imported yet.
  echo Run IMPORT_DNNI_5090.bat or choose Import / Verify in DNNI_5090_MANAGER.bat.
  goto :FAIL
)

if not exist "%ROOT%\capture_plan.jsonl" (
  echo [SETUP] Creating four-timbre capture plan...
  python training\scripts\run_logged.py --log "%LOGROOT%\capture_plan.log" -- python training\scripts\generate_dnni_capture_plan.py || goto :FAIL
)
if not exist "%ROOT%\batch_capture\batch_capture_map.json" (
  echo [SETUP] Creating four long capture MIDI files...
  python training\scripts\run_logged.py --log "%LOGROOT%\batch_capture.log" -- python training\scripts\generate_dnni_batch_capture_midi.py || goto :FAIL
)

if not exist "%RAW%" (
  set "HAVE_BATCH_BOUNCES=1"
  for %%T in (timbre_1 timbre_2 timbre_3 timbre_4) do (
    if not exist "%ROOT%\batch_bounces\%%T.wav" set "HAVE_BATCH_BOUNCES=0"
  )
  if "!HAVE_BATCH_BOUNCES!"=="1" (
    echo [SETUP] Found four long batch bounces. Slicing automatically...
    python training\scripts\run_logged.py --log "%LOGROOT%\batch_slice.log" -- python training\scripts\slice_dnni_batch_bounces.py || goto :FAIL
  )
  echo [SETUP] Building render manifest from captured WAV files...
  python training\scripts\run_logged.py --log "%LOGROOT%\render_manifest.log" -- python training\scripts\build_dnni_render_manifest.py
  if errorlevel 1 (
    echo.
    echo [ERROR] Rendered WAV capture set is not complete yet.
    echo Easiest path:
    echo   1. Run PREPARE_DNNI_CAPTURE.bat
    echo   2. Import the 4 generated MIDI files into Synthesizer V Studio 2
    echo   3. Bounce 4 long WAVs into datasets\dnni_four_timbres\batch_bounces
    echo   4. Run TRAIN_DNNI_5090.bat again
    goto :FAIL
  )
)

set "SONICRAFT_DATA_FINGERPRINT="
for /f "usebackq delims=" %%F in (`python training\scripts\dnni_pipeline_fingerprint.py --value-only`) do set "SONICRAFT_DATA_FINGERPRINT=%%F"
if not defined SONICRAFT_DATA_FINGERPRINT (
  echo [ERROR] Could not compute DNNI data fingerprint.
  goto :FAIL
)
echo [DATA FINGERPRINT] !SONICRAFT_DATA_FINGERPRINT!

echo [CHECKPOINT / LATENT PREFLIGHT]
python training\scripts\dnni_training_status.py
if errorlevel 1 goto :BAD_CHECKPOINT
echo.

echo [GPU / ENVIRONMENT CHECK]
python training\scripts\run_logged.py --log "%LOGROOT%\preflight.log" -- python training\scripts\dnni_5090_preflight.py || goto :FAIL
echo.

echo [1/5] VAE64 acoustic codec
set "SONICRAFT_RECIPE_FINGERPRINT=!DNNI_CODEC_RECIPE_FINGERPRINT!"
set "CODEC_RESUME="
if exist "checkpoints\dnni4_vae64_research.pt" (
  set "CODEC_RESUME=--resume checkpoints\dnni4_vae64_research.pt"
  echo [AUTO RESUME] Found codec checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\01_codec.log" -- python training\train_codec.py --manifest "%RAW%" --arch vae64 --width !DNNI_CODEC_WIDTH! --epochs !DNNI_CODEC_EPOCHS! --batch !DNNI_CODEC_BATCH! --real-ratio 1.0 --modeled-ratio 0.0 --modeled-recon-weight 1.0 --physics-weight 0.0 --physics-metric-weight 0.0 --out checkpoints\dnni4_vae64_research.pt --decoder-out checkpoints\dnni4_vae64_decoder_research.pt !CODEC_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [2/5] Encode four-timbre VAE64 latents
if exist "%LATENTS%" (
  echo [SKIP] Latent index already exists: %LATENTS%
) else (
  python training\scripts\run_logged.py --log "%LOGROOT%\02_latents.log" -- python training\scripts\encode_vae64_latents.py --index "%RAW%" --codec checkpoints\dnni4_vae64_research.pt --out %ROOT%\latents --source-fingerprint "!SONICRAFT_DATA_FINGERPRINT!" || goto :FAIL
)
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [3/5] HQ four-timbre renderer
set "SONICRAFT_RECIPE_FINGERPRINT=!DNNI_RENDER_RECIPE_FINGERPRINT!"
set "RENDER_RESUME="
if exist "checkpoints\dnni4_renderer_hq_research_last.pt" (
  set "RENDER_RESUME=--resume checkpoints\dnni4_renderer_hq_research_last.pt"
  echo [AUTO RESUME] Found HQ renderer checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\03_renderer.log" -- python training\scripts\run_dnni_research_entry.py renderer -- --index "%LATENTS%" --preset !DNNI_RENDER_PRESET! --epochs !DNNI_RENDER_EPOCHS! --batch !DNNI_RENDER_BATCH! --accum !DNNI_RENDER_ACCUM! --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_renderer_hq_research_last.pt --best-out checkpoints\dnni4_renderer_hq_research_best.pt !RENDER_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [4/5] Frontier Core distillation
set "SONICRAFT_RECIPE_FINGERPRINT=!DNNI_DISTILL_RECIPE_FINGERPRINT!"
set "DISTILL_RESUME="
if exist "checkpoints\dnni4_frontier_research.pt" (
  set "DISTILL_RESUME=--resume checkpoints\dnni4_frontier_research.pt"
  echo [AUTO RESUME] Found distillation checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\04_distill.log" -- python training\scripts\run_dnni_research_entry.py distill -- --index "%LATENTS%" --teacher checkpoints\dnni4_renderer_hq_research_best.pt --student-preset !DNNI_DISTILL_PRESET! --epochs !DNNI_DISTILL_EPOCHS! --batch !DNNI_DISTILL_BATCH! --accum !DNNI_DISTILL_ACCUM! --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_frontier_research.pt !DISTILL_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [5/5] Shortcut distillation
set "SONICRAFT_RECIPE_FINGERPRINT=!DNNI_SHORTCUT_RECIPE_FINGERPRINT!"
set "SHORTCUT_RESUME="
if exist "checkpoints\dnni4_frontier_shortcut_research.pt" (
  set "SHORTCUT_RESUME=--resume checkpoints\dnni4_frontier_shortcut_research.pt"
  echo [AUTO RESUME] Found shortcut checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\05_shortcut.log" -- python training\scripts\run_dnni_research_entry.py shortcut -- --index "%LATENTS%" --init checkpoints\dnni4_frontier_research.pt --preset !DNNI_SHORTCUT_PRESET! --max-steps !DNNI_SHORTCUT_MAX_STEPS! --recommend-steps !DNNI_SHORTCUT_RECOMMEND_STEPS! --epochs !DNNI_SHORTCUT_EPOCHS! --batch !DNNI_SHORTCUT_BATCH! --accum !DNNI_SHORTCUT_ACCUM! --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_frontier_shortcut_research.pt !SHORTCUT_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo ============================================================
echo [DONE] ALL TRAINING STAGES COMPLETE
echo Final checkpoint:
echo checkpoints\dnni4_frontier_shortcut_research.pt
echo Logs:
echo %LOGROOT%
echo ============================================================
if exist "%STOPFILE%" del /q "%STOPFILE%" >nul 2>&1
exit /b 0

:PAUSED
echo.
echo ============================================================
echo [SAFE STOP COMPLETE]
echo The current training state was saved successfully.
echo Double-click TRAIN_DNNI_5090.bat later to continue automatically.
echo ============================================================
exit /b 0

:BAD_CHECKPOINT
echo.
echo ============================================================
echo [INVALID/CORRUPT CHECKPOINT DETECTED]
echo Automatic resume has been blocked to protect your training state.
echo Run STATUS_DNNI_5090.bat for details.
echo Use DNNI_5090_MANAGER.bat - Archive / Reset training state if the data intentionally changed.
echo Otherwise inspect/rename the bad artifact, then start TRAIN_DNNI_5090.bat again.
echo ============================================================
exit /b 2

:FAIL
set "EC=%ERRORLEVEL%"
if "%EC%"=="0" set "EC=1"
echo.
echo ============================================================
echo [TRAINING STOPPED WITH ERROR] code=%EC%
echo Existing checkpoints are kept.
echo Fix the error, then double-click TRAIN_DNNI_5090.bat to resume.
echo ============================================================
exit /b %EC%
