@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if "%~1"=="" (set "MODEL_DIR=models\dnni") else (set "MODEL_DIR=%~1")
"%PY%" "runtime\dnni_tensor_shape_probe.py" "%MODEL_DIR%" --out "%MODEL_DIR%\dnni_tensor_shapes.json"
exit /b %ERRORLEVEL%
