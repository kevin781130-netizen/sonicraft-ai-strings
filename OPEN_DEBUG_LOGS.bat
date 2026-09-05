@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
start "" explorer.exe "%ROOT%logs"
