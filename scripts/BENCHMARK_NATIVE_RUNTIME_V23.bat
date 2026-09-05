@echo off
setlocal
cd /d "%~dp0\.."
python training\scripts\benchmark_renderer_service_v23.py --out release\native_runtime_benchmark_v23.json --seconds 2 --runs 8 --max-p95-rtf 1.0
