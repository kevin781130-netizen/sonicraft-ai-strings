@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
python training\smoke_v06.py
endlocal
