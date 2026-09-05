@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\rc_v70\VERIFY_AUTHENTICODE_V70.ps1" -ProjectRoot "%CD%"
set EC=%ERRORLEVEL%
pause
exit /b %EC%
