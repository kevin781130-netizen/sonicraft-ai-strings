@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No project venv activated; using current Python.
if "%~1"=="" (
  echo Usage: scripts\EXPORT_ORT_FRONTIER.bat ^<renderer.pt^> ^<strings_vae64_decoder.pt^>
  exit /b 2
)
if "%~2"=="" exit /b 2
REM Export dependencies are developer-only and are NOT part of the consumer runtime.
python -m pip install "onnx>=1.17" "onnxscript>=0.2" "onnxruntime>=1.23" || exit /b 1
python training\scripts\export_frontier_onnx.py --renderer "%~1" --decoder "%~2" --out-dir build\ort_export || exit /b 1
python -m onnxruntime.tools.convert_onnx_models_to_ort build\ort_export --optimization_style Fixed --enable_type_reduction || exit /b 1
echo.
echo [PASS] ONNX + ORT format exported. required_operators_and_types.config is ready for a reduced custom runtime build.
endlocal
