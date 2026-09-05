@echo off
setlocal
if "%~1"=="" (
  echo Drag a .musicxml .xml or .mxl score onto this BAT.
  pause
  exit /b 2
)
set "ROOT=%~dp0"
if not exist "%ROOT%runtime\" if exist "%ROOT%..\Runtime\" set "ROOT=%~dp0..\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
"%PY%" "%ROOT%runtime\compile_musicxml_strings_v49.py" "%~1"
if errorlevel 1 pause
