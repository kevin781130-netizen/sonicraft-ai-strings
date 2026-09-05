@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

set RAW=datasets\manifests\real_strings_raw.jsonl
set AUD=datasets\manifests\real_strings_audited_v08.jsonl
set ANA=datasets\processed\real_strings_v08\analyzed.jsonl
set PHY=datasets\processed\real_strings_v08\physics.jsonl

if not exist "%RAW%" (
  call scripts\BUILD_REAL_STRINGS_MANIFEST_V08.bat
)
if not exist "%RAW%" (
  echo [INFO] No Expert-ready commercial real recordings yet.
  exit /b 3
)
python training\scripts\audit_real_recordings.py --manifest "%RAW%" --out "%AUD%" || exit /b 1
python training\scripts\analyze_real_performance.py --manifest "%AUD%" --out-dir datasets\processed\real_strings_v08\analysis_npz --out-index "%ANA%" || exit /b 1
python training\derive_performance_physics.py --index "%ANA%" --out-dir datasets\processed\real_strings_v08\physics_npz --out-index "%PHY%" || exit /b 1

echo [DONE] Rights-cleared real recordings analyzed into vibrato/transition/bow supervision: %PHY%
endlocal
