@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  echo Usage: %~nx0 WASAPI_STREAM_LATENCY_MS [HOST] [PORT]
  exit /b 2
)
set HOST=%~2
if "%HOST%"=="" set HOST=127.0.0.1
set PORT=%~3
if "%PORT%"=="" set PORT=49337
python training\scripts\benchmark_ultra_low_latency_v25.py --host %HOST% --port %PORT% --wasapi-stream-latency-ms %~1 --trials 20 --out build\ultra_low_latency_v25.json
