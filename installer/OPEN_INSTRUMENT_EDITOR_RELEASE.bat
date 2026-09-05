@echo off
setlocal
set "APP=%~dp0.."
set "PY=%APP%\Runtime\venv\Scripts\python.exe"
if not exist "%PY%" (
  where python.exe >nul 2>nul && set "PY=python.exe"
)
if not exist "%PY%" (
  where py.exe >nul 2>nul && set "PY=py.exe"
)
if "%PY%"=="py.exe" (
  start "SONICRAFT Instrument Editor" py.exe -3 "%APP%\Frontend\editor_server.py" --open
  exit /b 0
)
if not exist "%PY%" if "%PY%"=="%APP%\Runtime\venv\Scripts\python.exe" (
  echo SONICRAFT Instrument Editor needs the local AI Runtime/Python environment.
  echo Open Manager ^> AI RUNTIME ^> Install AI Runtime, then retry.
  pause
  exit /b 2
)
start "SONICRAFT Instrument Editor" "%PY%" "%APP%\Frontend\editor_server.py" --open
exit /b 0
