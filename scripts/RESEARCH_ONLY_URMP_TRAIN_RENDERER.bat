@echo off
setlocal
cd /d "%~dp0.."
echo ============================================================
echo RESEARCH ONLY - URMP OUTPUT MUST NOT ENTER COMMERCIAL WEIGHTS
ECHO ============================================================
echo.
call .venv\Scripts\activate.bat
python training\scripts\encode_latents.py --codec checkpoints\codec_s.pt --index datasets\processed\urmp48\index.jsonl
python training\train_renderer.py --index datasets\processed\urmp48\index.jsonl --out checkpoints\RESEARCH_ONLY_renderer_urmp.pt --epochs 120 --batch 4
pause
