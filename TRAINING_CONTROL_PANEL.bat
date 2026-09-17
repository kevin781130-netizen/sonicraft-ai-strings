@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
  python training\training_control_panel.py --open
) else (
  py -3 training\training_control_panel.py --open
)
if errorlevel 1 (
  echo.
  echo Failed to start SONICRAFT Training Control.
  pause
)
