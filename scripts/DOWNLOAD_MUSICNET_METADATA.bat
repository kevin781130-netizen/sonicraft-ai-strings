@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
python training\scripts\fetch_musicnet.py --out datasets\raw\musicnet
endlocal
