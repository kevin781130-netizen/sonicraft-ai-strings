@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%runtime\" if exist "%ROOT%..\Runtime\" set "ROOT=%~dp0..\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
if "%~1"=="" (
  echo SONICRAFT v6.2 Acoustic Runtime Provenance Checkpoint
  echo.
  echo verify:
  echo   PERFORMANCE_CHECKPOINT_V62.bat verify CHECKPOINT.json --score SCORE.musicxml --store STORE.json [--policy POLICY.json] [--backend auto^|torch^|ort] [--model-dir MODELS]
  echo.
  echo replay:
  echo   PERFORMANCE_CHECKPOINT_V62.bat replay CHECKPOINT.json --score SCORE.musicxml --store STORE.json [runtime options]
  echo.
  echo provenance:
  echo   PERFORMANCE_CHECKPOINT_V62.bat provenance CHECKPOINT.json
  echo.
  echo restore:
  echo   PERFORMANCE_CHECKPOINT_V62.bat restore CHECKPOINT.json --store STORE.json --utility UTILITY.json --policy POLICY.json
  echo.
  echo release pin:
  echo   PERFORMANCE_CHECKPOINT_V62.bat release CHECKPOINT.json --store STORE.json
  exit /b 2
)
"%PY%" "%ROOT%runtime\performance_checkpoint_v62.py" %*
if errorlevel 1 pause
