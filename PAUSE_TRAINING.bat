@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
  python training\training_control.py pause
) else (
  py -3 training\training_control.py pause
)
echo.
echo Safe pause requested. The trainer will checkpoint at the next optimizer boundary and exit.
timeout /t 3 /nobreak >nul
