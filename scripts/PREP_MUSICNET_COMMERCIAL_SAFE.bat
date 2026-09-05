@echo off
cd /d "%~dp0.."
if "%~2"=="" (echo Usage: PREP_MUSICNET_COMMERCIAL_SAFE.bat metadata.csv C:\path\to\musicnet\train_data & exit /b 2)
python training\scripts\build_musicnet_safe_manifest.py "%~1" "%~2"
pause
