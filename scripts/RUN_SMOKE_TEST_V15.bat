@echo off
setlocal
cd /d "%~dp0.."
python training\smoke_v15.py
if errorlevel 1 exit /b %errorlevel%
echo.
echo v1.5 architecture/runtime smoke test PASS.
