@echo off
setlocal
cd /d "%~dp0.."
python training\smoke_v27.py
endlocal
