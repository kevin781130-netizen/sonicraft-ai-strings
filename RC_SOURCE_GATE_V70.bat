@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Use py -3 manually with scripts\rc_source_gate_v70.py.
  pause
  exit /b 2
)
python scripts\rc_source_gate_v70.py
set EC=%ERRORLEVEL%
pause
exit /b %EC%
