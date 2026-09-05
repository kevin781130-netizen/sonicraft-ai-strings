@echo off
setlocal
cd /d "%~dp0.."
python training\smoke_v25.py
if errorlevel 1 exit /b %errorlevel%
echo [PASS] v2.5 Ultra-Low-Latency Engine smoke
