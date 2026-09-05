@echo off
setlocal
cd /d "%~dp0\.."
set IDX=%~1
if "%IDX%"=="" set IDX=datasets\processed\ballad_dac\train.jsonl
call .venv\Scripts\activate.bat 2>nul
python training\train_vibrato_expert.py --index "%IDX%" --epochs 120 --batch 16 --out checkpoints\vibrato_expert_v06.pt
endlocal
