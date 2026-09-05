@echo off
setlocal
cd /d "%~dp0\.."
python training\smoke_v23.py
if errorlevel 1 exit /b %errorlevel%
echo [PASS] v2.3 Native Production Pass smoke
