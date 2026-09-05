@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
set ORT_SHA=2e2543fbe9fae542f921d47a72d21d5a4ef0b710
set ORT_DIR=build\_deps\onnxruntime
set OPS=build\ort_export\required_operators_and_types.config
set OPSABS=%CD%\%OPS%
if not exist "%OPS%" (
  echo [ERROR] %OPS% missing. Run scripts\EXPORT_ORT_FRONTIER.bat first.
  exit /b 2
)
if not exist "%ORT_DIR%\.git" git clone --filter=blob:none https://github.com/microsoft/onnxruntime.git "%ORT_DIR%" || exit /b 1
pushd "%ORT_DIR%"
git fetch origin %ORT_SHA% --depth 1 || exit /b 1
git checkout --detach %ORT_SHA% || exit /b 1
REM CPU-first shipping target: smallest self-contained ORT runtime for no-dedicated-GPU machines.
call build.bat --config MinSizeRel --build_shared_lib --parallel --skip_tests ^
  --minimal_build --disable_ml_ops --disable_rtti --build_wheel ^
  --include_ops_by_config "%OPSABS%" --enable_reduced_operator_type_support
if errorlevel 1 exit /b 1
popd
echo [PASS] Reduced ORT CPU Python wheel build complete. Locate the wheel under build\Windows\MinSizeRel\MinSizeRel\dist and stage it with the ORT models before VERIFY_NATIVE_RUNTIME_V22.bat.
endlocal
