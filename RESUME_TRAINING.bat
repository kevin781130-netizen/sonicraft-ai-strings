@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
  python training\training_control.py resume
) else (
  py -3 training\training_control.py resume
)
if errorlevel 1 (
  echo.
  echo Resume failed. Open TRAINING_CONTROL_PANEL.bat to inspect the current state.
  pause
)
