@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
set ORT_SHA=2e2543fbe9fae542f921d47a72d21d5a4ef0b710
set ORT_DIR=build\_deps\onnxruntime
set OPS=build\ort_export\required_operators_and_types.config
set OPSABS=%CD%\%OPS%
if not exist "%OPS%" ( echo [ERROR] Run scripts\EXPORT_ORT_FRONTIER.bat first. & exit /b 2 )
if "%CUDA_PATH%"=="" ( echo [ERROR] CUDA_PATH missing. & exit /b 2 )
if "%CUDNN_HOME%"=="" ( echo [ERROR] CUDNN_HOME missing. & exit /b 2 )
if not exist "%ORT_DIR%\.git" git clone --filter=blob:none https://github.com/microsoft/onnxruntime.git "%ORT_DIR%" || exit /b 1
pushd "%ORT_DIR%"
git fetch origin %ORT_SHA% --depth 1 || exit /b 1
git checkout --detach %ORT_SHA% || exit /b 1
REM CUDA remains a modular high-performance option. Keep reduced operators and plugin EP;
REM CPU minimal build is the footprint reference because generic minimal-build + CUDA support
REM is not assumed safe without provider-specific validation.
call build.bat --config MinSizeRel --build_shared_lib --parallel --skip_tests --use_cuda ^
  --cuda_home "%CUDA_PATH%" --cudnn_home "%CUDNN_HOME%" ^
  --include_ops_by_config "%OPSABS%" --enable_reduced_operator_type_support ^
  --disable_ml_ops --disable_contrib_ops ^
  --cmake_extra_defines "CMAKE_CUDA_ARCHITECTURES=native" ^
  --cmake_extra_defines "onnxruntime_BUILD_CUDA_EP_AS_PLUGIN=ON"
if errorlevel 1 exit /b 1
popd
echo [PASS] Reduced ORT CUDA plugin build complete. Benchmark against CPU/PyTorch before promotion.
endlocal
