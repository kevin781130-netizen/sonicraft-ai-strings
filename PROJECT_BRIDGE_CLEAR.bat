@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag a SONICRAFT Q4 MIDI file onto this BAT.
  pause
  exit /b 2
)
set /p START=Start beat to clear: 
set /p END=End beat to clear: 
python runtime\project_bridge_v30.py clear "%~1" --start-beat %START% --end-beat %END%
if errorlevel 1 pause
endlocal
