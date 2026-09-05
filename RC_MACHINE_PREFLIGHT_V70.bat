@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\rc_v70\COLLECT_MACHINE_PREFLIGHT_V70.ps1" -ProjectRoot "%CD%"
pause
endlocal
