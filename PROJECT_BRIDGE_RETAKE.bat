@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag a SONICRAFT Q4 MIDI file onto this BAT.
  pause
  exit /b 2
)
set /p START=Start beat from project start ^(example 8^): 
set /p END=End beat ^(example 16^): 
set /p TARGET=Retake target ^(timbre/dynamics/vibrato/micro-pitch/timing/bow/all^): 
set /p AMOUNT=Retake amount 0.0-1.0 ^(example .7^): 
set /p SEED=Retake seed 0-255 ^(example 17^): 
python runtime\project_bridge_v30.py apply "%~1" --start-beat %START% --end-beat %END% --retake-target %TARGET% --retake-amount %AMOUNT% --seed %SEED% --authority on
if errorlevel 1 pause
endlocal
