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
set /p ASSIST=AI Assist ^(manual/assist/auto^): 
set /p STYLE=Style ^(neutral/adagio/allegro/con-fuoco/pop/ballade^): 
set /p LOOSE=Ensemble looseness 0.0-1.0 ^(example .18^): 
python runtime\project_bridge_v30.py apply "%~1" --start-beat %START% --end-beat %END% --assist %ASSIST% --style %STYLE% --smart-dynamics on --smart-articulation on --phrase-director on --looseness %LOOSE% --authority on
if errorlevel 1 pause
endlocal
