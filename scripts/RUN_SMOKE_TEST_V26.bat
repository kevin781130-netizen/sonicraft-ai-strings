@echo off
setlocal
cd /d "%~dp0.."
python training\smoke_v26.py
if errorlevel 1 exit /b %errorlevel%
