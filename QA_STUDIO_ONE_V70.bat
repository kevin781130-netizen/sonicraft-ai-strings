@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\rc_v70\RUN_HOST_QA_V70.ps1" -ProjectRoot "%CD%" -Host StudioOne
set EC=%ERRORLEVEL%
pause
exit /b %EC%
