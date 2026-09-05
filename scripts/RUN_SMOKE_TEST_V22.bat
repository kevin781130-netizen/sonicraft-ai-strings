@echo off
setlocal
cd /d "%~dp0\.."
python training\smoke_v22.py || exit /b 1
echo [PASS] v2.2 Platform Kill Gap smoke
endlocal
