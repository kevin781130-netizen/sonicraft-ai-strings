@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0BUILD_VST3.bat"
if errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\install.ps1"
endlocal
