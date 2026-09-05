@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  echo Usage: %~nx0 path\to\teacher_checkpoint.pt [output_checkpoint.pt]
  exit /b 2
)
set "OUT=%~2"
if "%OUT%"=="" set "OUT=checkpoints\reflow_nano_dit.pt"
python training\reflow_distill_renderer.py --teacher "%~1" --out "%OUT%" --student-preset nano_dit --teacher-steps 24 --target-steps 4 --anchor 0.20
