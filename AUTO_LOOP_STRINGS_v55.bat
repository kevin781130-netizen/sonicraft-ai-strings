@echo off
setlocal
if "%~1"=="" (
  echo Drag a MusicXML/XML/MXL score onto this BAT.
  pause
  exit /b 2
)
set "ROOT=%~dp0"
if not exist "%ROOT%runtime\" if exist "%ROOT%..\Runtime\" set "ROOT=%~dp0..\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
"%PY%" "%ROOT%runtime\auto_loop_strings_v55.py" "%~1"
if errorlevel 1 pause
