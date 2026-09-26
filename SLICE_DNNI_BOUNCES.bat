@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Slice 4 Long Bounces

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready. Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

if not exist datasets\dnni_four_timbres\batch_capture\batch_capture_map.json (
  echo [ERROR] Missing batch capture map.
  echo Run PREPARE_DNNI_CAPTURE.bat first.
  pause
  exit /b 2
)

for %%T in (timbre_1 timbre_2 timbre_3 timbre_4) do (
  if not exist "datasets\dnni_four_timbres\batch_bounces\%%T.wav" (
    echo [ERROR] Missing datasets\dnni_four_timbres\batch_bounces\%%T.wav
    pause
    exit /b 2
  )
)

echo [1/3] Slicing four long WAVs into capture clips...
python training\scripts\slice_dnni_batch_bounces.py || goto :FAIL

echo [2/3] Building research render manifest...
python training\scripts\build_dnni_render_manifest.py || goto :FAIL

echo [3/3] Verifying capture/data fingerprint...
python training\scripts\dnni_pipeline_fingerprint.py || goto :FAIL

echo.
echo ============================================================
echo [DONE] Four long bounces were converted to the training layout.
echo Next: run TRAIN_DNNI_5090.bat or choose Start / Resume in Manager.
echo ============================================================
pause
exit /b 0

:FAIL
echo.
echo [ERROR] Batch bounce processing failed. Existing source WAVs were not deleted.
pause
exit /b 1
