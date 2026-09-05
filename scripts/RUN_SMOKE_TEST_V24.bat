@echo off
setlocal
cd /d "%~dp0.."
python training\smoke_v24.py
if errorlevel 1 exit /b 1
echo [PASS] v2.4 Realtime Product Shell smoke
endlocal
