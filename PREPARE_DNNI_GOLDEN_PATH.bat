@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if "%~1"=="" (
  set "MODEL_DIR=models\dnni"
) else (
  set "MODEL_DIR=%~1"
)

"%PY%" "runtime\dnni_dtype_map_probe.py" "%MODEL_DIR%" --out "%MODEL_DIR%\dnni_dtype_map.json"
if errorlevel 1 exit /b %ERRORLEVEL%

"%PY%" "runtime\dnni_shared_region_probe.py" "%MODEL_DIR%" --out "%MODEL_DIR%\dnni_shared_regions.json"
if errorlevel 1 exit /b %ERRORLEVEL%

"%PY%" "runtime\dnni_golden_path_probe.py" "%MODEL_DIR%" --dtype-map "%MODEL_DIR%\dnni_dtype_map.json" --out "%MODEL_DIR%\violin_a4_golden_path.json"
exit /b %ERRORLEVEL%
