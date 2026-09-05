@echo off
setlocal
if "%~1"=="" (
  echo Usage: ITERATE_STRINGS_v49.bat ^<judge_queue.json^> ^<render-folder^>
  echo The render folder should contain the expected WAV names, or A.wav B.wav C.wav D.wav.
  pause
  exit /b 2
)
set "ROOT=%~dp0"
if not exist "%ROOT%runtime\" if exist "%ROOT%..\Runtime\" set "ROOT=%~dp0..\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
"%PY%" "%ROOT%runtime\iterate_strings_v49.py" "%~1" "%~2"
if errorlevel 1 pause
