@echo off
setlocal
cd /d "%~dp0"
echo [SONICRAFT v7.0 RC] FAIL-CLOSED FINAL GATE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\rc_v70\FINAL_GATE_V70.ps1" -ProjectRoot "%CD%" %*
set EC=%ERRORLEVEL%
pause
exit /b %EC%
