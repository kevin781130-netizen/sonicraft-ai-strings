@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag a Standard MIDI file onto this BAT, or pass its path as argument 1.
  pause
  exit /b 2
)
python runtime\compile_midi_performance_v30.py "%~1"
if errorlevel 1 pause
endlocal
