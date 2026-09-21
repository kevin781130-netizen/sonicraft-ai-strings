@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" goto :usage
call "%~dp0scripts\SELECT_TRAINING_PYTHON.bat"
if errorlevel 1 exit /b 2
echo Running SONICRAFT GPU training preflight...
"%SONICRAFT_TRAIN_PY%" training\gpu_training_preflight.py %*
if errorlevel 1 goto :preflight_failed
start "SONICRAFT Training Control" "%SONICRAFT_TRAIN_PY%" training\training_control_panel.py --open
"%SONICRAFT_TRAIN_PY%" training\train_ballad_renderer_pausable.py %*
exit /b %errorlevel%

:preflight_failed
echo GPU training was NOT started because preflight failed.
echo Fix the reported issue and run the same command again.
exit /b 2

:usage
echo SONICRAFT safe GPU renderer training
echo.
echo Usage:
echo   TRAIN_RENDERER_GPU.bat [train_ballad_renderer arguments]
echo.
echo Example:
echo   TRAIN_RENDERER_GPU.bat --index datasets\processed\phrase_finetune\index.jsonl --preset hq_strings_v18 --epochs 100 --out Models\ballad_renderer_hq_v20_last.pt --best-out Models\ballad_renderer_hq_v20_best.pt
echo.
echo A read-only CUDA/data/output/pause-state preflight runs first.
echo The launcher opens the local Training Control Panel only after preflight passes.
echo Use PAUSE_TRAINING.bat for a one-click safe pause and RESUME_TRAINING.bat to continue.
echo See docs\TRAINING_PAUSE_RESUME.md before the production run.
exit /b 2
