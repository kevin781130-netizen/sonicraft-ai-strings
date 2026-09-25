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

echo [CHECKPOINT PREFLIGHT]
python training\scripts\dnni_training_status.py
if errorlevel 1 goto :BAD_CHECKPOINT
echo.

if not exist "%ROOT%\capture_plan.jsonl" (
  echo [SETUP] Creating four-timbre capture plan...
  python training\scripts\run_logged.py --log "%LOGROOT%\capture_plan.log" -- python training\scripts\generate_dnni_capture_plan.py || goto :FAIL
)

if not exist "%RAW%" (
  echo [SETUP] Building render manifest from captured WAV files...
  python training\scripts\run_logged.py --log "%LOGROOT%\render_manifest.log" -- python training\scripts\build_dnni_render_manifest.py
  if errorlevel 1 (
    echo.
    echo [ERROR] Rendered WAV capture set is not complete yet.
    echo Follow datasets\dnni_four_timbres\capture_plan.jsonl and render the expected WAV files first.
    goto :FAIL
  )
)

echo [GPU / ENVIRONMENT CHECK]
python training\scripts\run_logged.py --log "%LOGROOT%\preflight.log" -- python training\scripts\dnni_5090_preflight.py || goto :FAIL
echo.

echo [1/5] VAE64 acoustic codec
set "CODEC_RESUME="
if exist "checkpoints\dnni4_vae64_research.pt" (
  set "CODEC_RESUME=--resume checkpoints\dnni4_vae64_research.pt"
  echo [AUTO RESUME] Found codec checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\01_codec.log" -- python training\train_codec.py --manifest "%RAW%" --arch vae64 --width 32 --epochs 100 --batch 4 --real-ratio 1.0 --modeled-ratio 0.0 --modeled-recon-weight 1.0 --physics-weight 0.0 --physics-metric-weight 0.0 --out checkpoints\dnni4_vae64_research.pt --decoder-out checkpoints\dnni4_vae64_decoder_research.pt !CODEC_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [2/5] Encode four-timbre VAE64 latents
if exist "%LATENTS%" (
  echo [SKIP] Latent index already exists: %LATENTS%
) else (
  python training\scripts\run_logged.py --log "%LOGROOT%\02_latents.log" -- python training\scripts\encode_vae64_latents.py --index "%RAW%" --codec checkpoints\dnni4_vae64_research.pt --out %ROOT%\latents || goto :FAIL
)
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [3/5] HQ four-timbre renderer
set "RENDER_RESUME="
if exist "checkpoints\dnni4_renderer_hq_research_last.pt" (
  set "RENDER_RESUME=--resume checkpoints\dnni4_renderer_hq_research_last.pt"
  echo [AUTO RESUME] Found HQ renderer checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\03_renderer.log" -- python training\scripts\run_dnni_research_entry.py renderer -- --index "%LATENTS%" --preset hq_strings_v18 --epochs 260 --batch 2 --accum 2 --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_renderer_hq_research_last.pt --best-out checkpoints\dnni4_renderer_hq_research_best.pt !RENDER_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [4/5] Frontier Core distillation
set "DISTILL_RESUME="
if exist "checkpoints\dnni4_frontier_research.pt" (
  set "DISTILL_RESUME=--resume checkpoints\dnni4_frontier_research.pt"
  echo [AUTO RESUME] Found distillation checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\04_distill.log" -- python training\scripts\run_dnni_research_entry.py distill -- --index "%LATENTS%" --teacher checkpoints\dnni4_renderer_hq_research_best.pt --student-preset frontier_core_dit --epochs 130 --batch 2 --accum 2 --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_frontier_research.pt !DISTILL_RESUME!
if errorlevel 1 goto :FAIL
if exist "%STOPFILE%" goto :PAUSED

echo.
echo [5/5] Shortcut distillation
set "SHORTCUT_RESUME="
if exist "checkpoints\dnni4_frontier_shortcut_research.pt" (
  set "SHORTCUT_RESUME=--resume checkpoints\dnni4_frontier_shortcut_research.pt"
  echo [AUTO RESUME] Found shortcut checkpoint.
)
python training\scripts\run_logged.py --log "%LOGROOT%\05_shortcut.log" -- python training\scripts\run_dnni_research_entry.py shortcut -- --index "%LATENTS%" --init checkpoints\dnni4_frontier_research.pt --preset frontier_core_dit --max-steps 8 --recommend-steps 2 --epochs 55 --batch 1 --accum 1 --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_frontier_shortcut_research.pt !SHORTCUT_RESUME!
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
echo Rename or move the bad checkpoint, then start TRAIN_DNNI_5090.bat again.
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
