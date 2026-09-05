@echo off
setlocal
cd /d "%~dp0.."
set PY=python
if exist runtime\venv\Scripts\python.exe set PY=runtime\venv\Scripts\python.exe
%PY% training\shortcut_distill_renderer.py --index datasets\processed\ballad_vae64\index.jsonl --preset frontier_shared_dit --max-steps 8 --recommend-steps 2 --out checkpoints\ballad_renderer_frontier_shortcut.pt %*
if errorlevel 1 exit /b %errorlevel%
echo [PASS] v1.7 shortcut frontier checkpoint written.
