@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%runtime\" if exist "%ROOT%..\Runtime\" set "ROOT=%~dp0..\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
if "%~1"=="" (
  echo SONICRAFT v6.0 Unified Evidence Store
  echo.
  echo Usage:
  echo   EVIDENCE_STORE_V60.bat status   --store STORE.json
  echo   EVIDENCE_STORE_V60.bat verify   --store STORE.json --utility UTILITY.json
  echo   EVIDENCE_STORE_V60.bat compact  --store STORE.json --retain 16
  echo   EVIDENCE_STORE_V60.bat export   --store STORE.json --out BACKUP.json
  echo   EVIDENCE_STORE_V60.bat rollback --store STORE.json --utility UTILITY.json [--commit ID]
  exit /b 2
)
"%PY%" "%ROOT%runtime\evidence_store_v60.py" %*
if errorlevel 1 pause
