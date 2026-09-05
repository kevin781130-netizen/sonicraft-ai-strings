@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo [ERROR] Run scripts\SETUP_TRAINING.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo WARNING: QuartSet is RESEARCH ONLY in this project until commercial rights are verified.
python training\scripts\fetch_quartset_research.py --out datasets\research\QuartSet
pause
