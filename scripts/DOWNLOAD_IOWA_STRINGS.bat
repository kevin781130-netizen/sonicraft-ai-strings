@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo [ERROR] Run scripts\SETUP_TRAINING.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python training\scripts\fetch_iowa_strings.py --out datasets\raw\IowaMIS
if errorlevel 1 goto :fail
python training\scripts\build_iowa_manifest.py --root datasets\raw\IowaMIS --out datasets\manifests\iowa_strings.jsonl
if errorlevel 1 goto :fail
echo.
echo Iowa 24/96 Violin-Viola-Cello dataset prepared.
pause
exit /b 0
:fail
echo.
echo [ERROR] Iowa dataset preparation failed.
pause
exit /b 1
