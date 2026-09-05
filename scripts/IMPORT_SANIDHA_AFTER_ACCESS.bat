@echo off
cd /d "%~dp0.."
if "%~1"=="" (echo Usage: IMPORT_SANIDHA_AFTER_ACCESS.bat C:\path\to\Sanidha & exit /b 2)
python training\scripts\import_sanidha.py "%~1"
pause
