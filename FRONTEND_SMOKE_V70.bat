@echo off
setlocal
cd /d "%~dp0"
call "%~dp0FRONTEND_SMOKE_V64.bat"
if errorlevel 1 exit /b 1
call "%~dp0FRONTEND_LAYOUT_GATE_V70.bat"
if errorlevel 1 exit /b 1
exit /b 0
