@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r training\requirements.txt
echo Training environment ready.
pause
