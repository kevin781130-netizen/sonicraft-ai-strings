@echo off
setlocal
cd /d "%~dp0"
call "%~dp0scripts\SELECT_TRAINING_PYTHON.bat"
if errorlevel 1 exit /b 2
"%SONICRAFT_TRAIN_PY%" training\training_control.py resume
exit /b %errorlevel%
