@echo off
rem Called by training entrypoints; export one interpreter for the whole process.
set "SONICRAFT_TRAIN_PY="
if exist "%~dp0..\.venv\Scripts\python.exe" set "SONICRAFT_TRAIN_PY=%~dp0..\.venv\Scripts\python.exe"
if defined SONICRAFT_TRAIN_PY goto :verify
for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "SONICRAFT_TRAIN_PY=%%P"
if defined SONICRAFT_TRAIN_PY goto :verify
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "SONICRAFT_TRAIN_PY=%%P"
if not defined SONICRAFT_TRAIN_PY goto :missing
:verify
"%SONICRAFT_TRAIN_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto :missing
exit /b 0
:missing
echo [ERROR] A working Python 3.11+ training environment is required.
echo Run scripts\SETUP_TRAINING.bat and retry.
exit /b 2
