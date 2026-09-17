@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" goto :usage

where python >nul 2>nul
if not errorlevel 1 (
  start "SONICRAFT Training Control" python training\training_control_panel.py --open
  python training\train_performance_planner.py %*
  exit /b %errorlevel%
)

start "SONICRAFT Training Control" py -3 training\training_control_panel.py --open
py -3 training\train_performance_planner.py %*
exit /b %errorlevel%

:usage
echo SONICRAFT symbolic Performance Planner training
echo.
echo Usage:
echo   TRAIN_PERFORMANCE_PLANNER.bat [train_performance_planner arguments]
echo.
echo Example:
echo   TRAIN_PERFORMANCE_PLANNER.bat --index datasets\processed\performance_planner_cleanroom_v1\index.jsonl --epochs 80 --out checkpoints\performance_planner_last.pt --best-out checkpoints\performance_planner_best.pt
echo.
echo The same PAUSE_TRAINING.bat / RESUME_TRAINING.bat / Training Control Panel are used.
exit /b 2
