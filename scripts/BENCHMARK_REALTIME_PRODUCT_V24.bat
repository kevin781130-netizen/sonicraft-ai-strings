@echo off
setlocal
cd /d "%~dp0.."
python training\scripts\benchmark_realtime_preview_v24.py --out release\realtime_preview_benchmark_v24.json %*
endlocal
