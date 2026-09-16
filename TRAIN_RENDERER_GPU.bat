@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" goto :usage

where python >nul 2>nul
if not errorlevel 1 (
  start "SONICRAFT Training Control" python training\training_control_panel.py --open
  python training\train_ballad_renderer_pausable.py %*
  exit /b %errorlevel%
)

start "SONICRAFT Training Control" py -3 training\training_control_panel.py --open
py -3 training\train_ballad_renderer_pausable.py %*
exit /b %errorlevel%

:usage
echo SONICRAFT safe GPU renderer training
echo.
echo Usage:
echo   TRAIN_RENDERER_GPU.bat [train_ballad_renderer arguments]
echo.
echo Example:
echo   TRAIN_RENDERER_GPU.bat --index datasets\processed\phrase_finetune\index.jsonl --preset hq_strings_v18 --epochs 100 --out Models\ballad_renderer_hq_v20_best.pt --best-out Models\ballad_renderer_hq_v20_best.pt
echo.
echo The launcher opens the local Training Control Panel automatically.
echo Use PAUSE_TRAINING.bat for a one-click safe pause and RESUME_TRAINING.bat to continue.
echo See docs\TRAINING_PAUSE_RESUME.md before the production run.
exit /b 2
